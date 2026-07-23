"""
Summarizer Service — Genera resúmenes con LLM.
Puerto: 8082

Endpoints:
  POST /generate           — Generar resumen (morning/evening/weekly)
  POST /answer             — Responder pregunta del bot con contexto
  GET  /health             — Health check

Dependencias:
  - storage (8084): leer bot_context del usuario
  - rag (8086): buscar chunks relevantes para preguntas
"""

import os
import sys
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.environ.get("PROJECT_DIR", "/opt/monitor-colegio"))

PORT = int(os.environ.get("SUMMARIZER_PORT", "8082"))
STORAGE_URL = os.environ.get("STORAGE_URL", "http://localhost:8084")
RAG_URL = os.environ.get("RAG_URL", "http://localhost:8086")
AI_ENGINE = os.environ.get("AI_ENGINE", "haiku")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def generate_summary(user_id, mode, data=None, is_weekly=False):
    """Generar resumen para un usuario."""
    from src.processor.summarizer import Summarizer

    # Leer config del usuario
    try:
        r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
        user_cfg = r.json().get("data", {}) if r.status_code == 200 else {}
    except Exception:
        user_cfg = {}

    # Si no viene data, leer bot_context desde storage
    if not data:
        try:
            r = requests.get(f"{STORAGE_URL}/context/{user_id}", timeout=5)
            data = r.json().get("data", {}) if r.status_code == 200 else {}
        except Exception:
            data = {}

    engine = AI_ENGINE
    api_key = GEMINI_API_KEY if engine == "gemini" else ANTHROPIC_API_KEY

    summarizer = Summarizer(api_key, user_cfg=user_cfg, engine=engine)

    if mode == "morning":
        message = summarizer.generate_morning_briefing(data, is_weekly=is_weekly)
    else:
        message = summarizer.generate_evening_summary(data, is_weekly=is_weekly)

    return {"ok": True, "message": message, "engine": engine, "chars": len(message)}


def answer_question(user_id, question):
    """Responder pregunta del bot usando RAG + LLM."""
    # 1. Buscar chunks relevantes via RAG
    context_chunks = []
    try:
        r = requests.post(f"{RAG_URL}/query", json={"user_id": user_id, "question": question}, timeout=5)
        if r.status_code == 200:
            context_chunks = r.json().get("chunks", [])
    except Exception:
        pass

    # 2. Si no hay RAG, fallback a bot_context truncado
    if not context_chunks:
        try:
            r = requests.get(f"{STORAGE_URL}/context/{user_id}", timeout=5)
            if r.status_code == 200:
                ctx = r.json().get("data", {})
                context_chunks = [json.dumps(ctx, ensure_ascii=False)[:6000]]
        except Exception:
            context_chunks = ["Sin contexto disponible"]

    # 3. Leer config usuario
    try:
        r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
        user_cfg = r.json().get("data", {}) if r.status_code == 200 else {}
    except Exception:
        user_cfg = {}

    # 4. Construir prompt y llamar LLM
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/Santiago")).strftime("%Y-%m-%d")
    hijos = ", ".join([f"{h['nombre']} ({h.get('curso','')})" for h in user_cfg.get("hijos", [])])

    context = "\n\n".join(context_chunks)
    system_prompt = f"""Eres un asistente de WhatsApp que responde preguntas de un apoderado sobre el colegio.
Responde breve (1-4 líneas), amigable, español chileno.
Si no tienes la info, di "No tengo esa info, confirma con el colegio 📞".
NUNCA inventes información.

Fecha: {today}
Hijos: {hijos}

Contexto:
{context}"""

    # Call LLM
    import anthropic
    if ANTHROPIC_API_KEY:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            system=system_prompt,
            messages=[{"role": "user", "content": question}],
        )
        answer = response.content[0].text
        return {"ok": True, "answer": answer, "chunks_used": len(context_chunks)}

    return {"ok": False, "error": "No API key configured"}


class SummarizerHandler(BaseHTTPRequestHandler):
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
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if urlparse(self.path).path.strip("/") == "health":
            self._respond(200, {"ok": True, "service": "summarizer", "port": PORT, "engine": AI_ENGINE})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        body = self._read_body()

        # POST /generate
        if parts == ["generate"]:
            user_id = body.get("user_id", "")
            mode = body.get("mode", "morning")
            is_weekly = body.get("is_weekly", False)
            data = body.get("data")
            if not user_id:
                self._respond(400, {"error": "user_id requerido"})
                return
            try:
                result = generate_summary(user_id, mode, data=data, is_weekly=is_weekly)
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"error": str(e)})

        # POST /answer
        elif parts == ["answer"]:
            user_id = body.get("user_id", "")
            question = body.get("question", "")
            if not user_id or not question:
                self._respond(400, {"error": "user_id y question requeridos"})
                return
            try:
                result = answer_question(user_id, question)
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"error": str(e)})

        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), SummarizerHandler)
    print(f"Summarizer service listening on :{PORT}")
    print(f"  Engine: {AI_ENGINE}")
    print(f"  Storage: {STORAGE_URL}")
    print(f"  RAG: {RAG_URL}")
    server.serve_forever()
