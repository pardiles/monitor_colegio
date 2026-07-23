"""
RAG Service — Embeddings + Similarity Search.
Puerto: 8086

Endpoints:
  POST /index/{user_id}      — Indexar/actualizar chunks de un usuario
  POST /query                — Buscar chunks relevantes para una pregunta
  GET  /stats/{user_id}      — Estadísticas de chunks indexados
  DELETE /index/{user_id}    — Eliminar índice de un usuario
  GET  /health               — Health check

Dependencias:
  - storage (8084): leer bot_context para chunking

Implementación:
  Fase 1 (actual): ChromaDB local (en memoria, persistido a disco)
  Fase 2 (futuro): pgvector en Aurora Serverless
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import requests

PORT = int(os.environ.get("RAG_PORT", "8086"))
STORAGE_URL = os.environ.get("STORAGE_URL", "http://localhost:8084")
CHROMA_DIR = os.environ.get("CHROMA_DIR", "/opt/monitor-colegio/data/chromadb")

# ChromaDB (lazy init)
_chroma_client = None
_collections = {}


def _get_chroma():
    """Inicializar ChromaDB (lazy)."""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            os.makedirs(CHROMA_DIR, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        except ImportError:
            # ChromaDB no instalado — fallback a búsqueda simple
            _chroma_client = "unavailable"
    return _chroma_client


def _get_collection(user_id):
    """Obtener o crear colección de un usuario."""
    if user_id not in _collections:
        client = _get_chroma()
        if client == "unavailable":
            return None
        _collections[user_id] = client.get_or_create_collection(
            name=f"user_{user_id}",
            metadata={"hnsw:space": "cosine"}
        )
    return _collections[user_id]


def _chunk_context(bot_context):
    """Dividir bot_context en chunks indexables."""
    chunks = []

    # Calendario: 1 evento = 1 chunk
    for evento in bot_context.get("calendario_persistente", []):
        text = f"Evento {evento.get('fecha', '')}: {evento.get('titulo', '')} ({evento.get('hijo', 'todos')})"
        if evento.get("hora"):
            text += f" a las {evento['hora']}"
        chunks.append({"id": f"cal_{evento.get('fecha','')}_{len(chunks)}", "text": text, "source": "calendario"})

    # Comunicaciones
    comms = bot_context.get("comunicaciones", {})
    if isinstance(comms, dict):
        for comm in comms.get("comunicaciones", [])[:20]:
            text = f"Comunicación: {comm.get('asunto', '')} — {comm.get('contenido', '')[:300]}"
            chunks.append({"id": f"comm_{len(chunks)}", "text": text, "source": "comunicaciones"})

    # Emails
    for email in bot_context.get("emails_recientes", [])[:10]:
        text = f"Email {email.get('fecha', '')}: {email.get('asunto', '')} — {email.get('resumen', '')}"
        chunks.append({"id": f"email_{len(chunks)}", "text": text, "source": "emails"})

    # Notas por hijo
    for key, val in bot_context.items():
        if key.startswith("calificaciones_") and isinstance(val, dict):
            hijo = key.replace("calificaciones_", "")
            text = f"Notas {hijo}: {json.dumps(val, ensure_ascii=False)[:500]}"
            chunks.append({"id": f"notas_{hijo}", "text": text, "source": "notas"})

    # Extraprogramáticas
    for extra in bot_context.get("extraprogramaticas", []):
        text = f"Extraprogramática: {extra.get('nombre', '')} — {extra.get('dia', '')} {extra.get('horario', '')} ({extra.get('hijo', '')})"
        chunks.append({"id": f"extra_{len(chunks)}", "text": text, "source": "extraprogramaticas"})

    # Casino
    casino = bot_context.get("casino_hoy") or bot_context.get("casino_menu", "")
    if casino:
        text = f"Casino/Menú: {casino[:300]}" if isinstance(casino, str) else f"Casino: {json.dumps(casino)[:300]}"
        chunks.append({"id": "casino", "text": text, "source": "casino"})

    # Horarios
    horarios = bot_context.get("horarios", {})
    if horarios:
        text = f"Horarios: {json.dumps(horarios, ensure_ascii=False)[:500]}"
        chunks.append({"id": "horarios", "text": text, "source": "horarios"})

    # SC Info
    scinfo = bot_context.get("scinfo", {})
    if scinfo:
        text = f"SC Info {scinfo.get('fecha', '')}: {scinfo.get('contenido', '')[:500]}"
        chunks.append({"id": "scinfo", "text": text, "source": "scinfo"})

    # WhatsApp reciente
    for grupo, msgs in bot_context.get("whatsapp_reciente", {}).items():
        if msgs:
            text = f"WA grupo {grupo}: " + " | ".join([f"{m.get('from','')}: {m.get('body','')}" for m in msgs[:5]])
            chunks.append({"id": f"wa_{grupo}", "text": text[:500], "source": "whatsapp"})

    return chunks


def index_user(user_id):
    """Indexar chunks del bot_context de un usuario."""
    # Leer bot_context desde storage
    try:
        r = requests.get(f"{STORAGE_URL}/context/{user_id}", timeout=5)
        if r.status_code != 200:
            return {"ok": False, "error": "Context not found"}
        bot_context = r.json().get("data", {})
    except Exception as e:
        return {"ok": False, "error": str(e)}

    chunks = _chunk_context(bot_context)
    if not chunks:
        return {"ok": True, "chunks": 0, "message": "No chunks to index"}

    collection = _get_collection(user_id)
    if collection is None:
        # ChromaDB not available — store chunks as JSON fallback
        chunks_path = os.path.join(CHROMA_DIR, f"{user_id}_chunks.json")
        os.makedirs(os.path.dirname(chunks_path), exist_ok=True)
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        return {"ok": True, "chunks": len(chunks), "backend": "json_fallback"}

    # Upsert to ChromaDB
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"]} for c in chunks],
    )
    return {"ok": True, "chunks": len(chunks), "backend": "chromadb"}


def query_chunks(user_id, question, n_results=5):
    """Buscar chunks relevantes para una pregunta."""
    collection = _get_collection(user_id)

    if collection is None:
        # Fallback: buscar en JSON
        chunks_path = os.path.join(CHROMA_DIR, f"{user_id}_chunks.json")
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as f:
                all_chunks = json.load(f)
            # Simple keyword matching
            q_lower = question.lower()
            scored = []
            for c in all_chunks:
                score = sum(1 for word in q_lower.split() if word in c["text"].lower())
                if score > 0:
                    scored.append((score, c))
            scored.sort(key=lambda x: -x[0])
            return [c["text"] for _, c in scored[:n_results]]
        return []

    # ChromaDB query
    try:
        results = collection.query(query_texts=[question], n_results=n_results)
        return results.get("documents", [[]])[0]
    except Exception:
        return []


class RAGHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if parts == ["health"]:
            chroma = _get_chroma()
            backend = "chromadb" if chroma != "unavailable" else "json_fallback"
            self._respond(200, {"ok": True, "service": "rag", "port": PORT, "backend": backend})
        elif len(parts) == 2 and parts[0] == "stats":
            user_id = parts[1]
            collection = _get_collection(user_id)
            if collection:
                count = collection.count()
                self._respond(200, {"ok": True, "user_id": user_id, "chunks": count})
            else:
                chunks_path = os.path.join(CHROMA_DIR, f"{user_id}_chunks.json")
                if os.path.exists(chunks_path):
                    with open(chunks_path) as f:
                        count = len(json.load(f))
                    self._respond(200, {"ok": True, "user_id": user_id, "chunks": count, "backend": "json"})
                else:
                    self._respond(200, {"ok": True, "user_id": user_id, "chunks": 0})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        body = self._read_body()

        # POST /index/{user_id}
        if len(parts) == 2 and parts[0] == "index":
            result = index_user(parts[1])
            self._respond(200, result)

        # POST /query
        elif parts == ["query"]:
            user_id = body.get("user_id", "")
            question = body.get("question", "")
            n = body.get("n_results", 5)
            if not user_id or not question:
                self._respond(400, {"error": "user_id y question requeridos"})
                return
            chunks = query_chunks(user_id, question, n_results=n)
            self._respond(200, {"ok": True, "chunks": chunks, "count": len(chunks)})

        else:
            self._respond(404, {"error": "Not found"})

    def do_DELETE(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "index":
            user_id = parts[1]
            client = _get_chroma()
            if client and client != "unavailable":
                try:
                    client.delete_collection(f"user_{user_id}")
                except Exception:
                    pass
            self._respond(200, {"ok": True, "message": f"Index deleted for {user_id}"})
        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    os.makedirs(CHROMA_DIR, exist_ok=True)
    server = HTTPServer(("0.0.0.0", PORT), RAGHandler)
    chroma = _get_chroma()
    backend = "chromadb" if chroma != "unavailable" else "json_fallback (install chromadb for better results)"
    print(f"RAG service listening on :{PORT}")
    print(f"  Backend: {backend}")
    print(f"  ChromaDB dir: {CHROMA_DIR}")
    server.serve_forever()
