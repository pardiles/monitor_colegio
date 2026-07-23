"""
Storage Service — API de datos centralizada.
Puerto: 8084

Endpoints:
  GET/PUT  /users/{user_id}           — Config del usuario
  GET/PUT  /context/{user_id}         — Bot context completo
  GET/PUT  /calendario/{user_id}      — Calendario persistente
  GET/PUT  /instrucciones/{user_id}   — Instrucciones de padres
  GET/PUT  /cache/{colegio_id}/{source} — Cache compartido por colegio
  GET      /cache/{colegio_id}/{source}/fresh?max_hours=12 — Check si cache es fresco
  GET      /meta/{user_id}            — Timestamps última actualización
  PUT      /meta/{user_id}/{source}   — Marcar fuente como actualizada
  GET      /users                     — Listar todos los usuarios
  DELETE   /users/{user_id}           — Eliminar usuario y sus datos
"""

import os
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CHILE_TZ = ZoneInfo("America/Santiago")
DATA_DIR = os.environ.get("DATA_DIR", "/opt/monitor-colegio/data")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/opt/monitor-colegio/config")
PORT = int(os.environ.get("STORAGE_PORT", "8084"))


def _read_json(path, fallback=None):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return fallback


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _user_dir(user_id):
    d = os.path.join(DATA_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def _cache_dir(colegio_id):
    d = os.path.join(DATA_DIR, "shared", colegio_id)
    os.makedirs(d, exist_ok=True)
    return d


def _is_fresh(colegio_id, source, max_hours):
    meta = _read_json(os.path.join(_cache_dir(colegio_id), "_meta.json"), {})
    last = meta.get(source, "")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=CHILE_TZ)
        age = (datetime.now(CHILE_TZ) - last_dt).total_seconds() / 3600
        return age < max_hours
    except Exception:
        return False


class StorageHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silenciar logs de request

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
        self.send_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        query = parse_qs(parsed.query)

        # GET /users — listar todos
        if parts == ["users"]:
            users = []
            users_dir = os.path.join(CONFIG_DIR, "users")
            if os.path.isdir(users_dir):
                for f in os.listdir(users_dir):
                    if f.endswith(".json") and f != "admin.json":
                        u = _read_json(os.path.join(users_dir, f))
                        if u and u.get("id"):
                            users.append({"id": u["id"], "nombre": u.get("nombre", ""), "step": u.get("step", 0)})
            self._respond(200, {"users": users, "count": len(users)})

        # GET /users/{user_id}
        elif len(parts) == 2 and parts[0] == "users":
            user_id = parts[1]
            path = os.path.join(CONFIG_DIR, "users", f"{user_id}.json")
            data = _read_json(path)
            if data:
                self._respond(200, {"ok": True, "data": data})
            else:
                self._respond(404, {"ok": False, "error": "User not found"})

        # GET /context/{user_id}
        elif len(parts) == 2 and parts[0] == "context":
            user_id = parts[1]
            # Try new path first, then legacy
            data = _read_json(os.path.join(_user_dir(user_id), "bot_context.json"))
            if not data:
                data = _read_json(os.path.join(DATA_DIR, f"bot_context_{user_id}.json"))
            if data:
                self._respond(200, {"ok": True, "data": data})
            else:
                self._respond(404, {"ok": False, "error": "Context not found"})

        # GET /calendario/{user_id}
        elif len(parts) == 2 and parts[0] == "calendario":
            user_id = parts[1]
            data = _read_json(os.path.join(_user_dir(user_id), "calendario.json"))
            if not data:
                data = _read_json(os.path.join(DATA_DIR, f"calendario_{user_id}.json"))
            self._respond(200, {"ok": True, "data": data or []})

        # GET /instrucciones/{user_id}
        elif len(parts) == 2 and parts[0] == "instrucciones":
            user_id = parts[1]
            data = _read_json(os.path.join(_user_dir(user_id), "instrucciones.json"))
            if not data:
                data = _read_json(os.path.join(DATA_DIR, f"monitor_inputs_{user_id}.json"))
            self._respond(200, {"ok": True, "data": data or []})

        # GET /cache/{colegio_id}/{source}
        elif len(parts) == 3 and parts[0] == "cache":
            colegio_id, source = parts[1], parts[2]
            data = _read_json(os.path.join(_cache_dir(colegio_id), f"{source}.json"))
            if data:
                self._respond(200, {"ok": True, "data": data})
            else:
                self._respond(404, {"ok": False, "error": "Cache miss"})

        # GET /cache/{colegio_id}/{source}/fresh?max_hours=12
        elif len(parts) == 4 and parts[0] == "cache" and parts[3] == "fresh":
            colegio_id, source = parts[1], parts[2]
            max_hours = float(query.get("max_hours", [12])[0])
            fresh = _is_fresh(colegio_id, source, max_hours)
            self._respond(200, {"fresh": fresh})

        # GET /meta/{user_id}
        elif len(parts) == 2 and parts[0] == "meta":
            user_id = parts[1]
            data = _read_json(os.path.join(_user_dir(user_id), "meta.json"), {})
            self._respond(200, {"ok": True, "data": data})

        # GET /health
        elif parts == ["health"]:
            self._respond(200, {"ok": True, "service": "storage", "port": PORT})

        else:
            self._respond(404, {"error": "Not found"})

    def do_PUT(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        body = self._read_body()

        # PUT /users/{user_id}
        if len(parts) == 2 and parts[0] == "users":
            user_id = parts[1]
            path = os.path.join(CONFIG_DIR, "users", f"{user_id}.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            _write_json(path, body)
            self._respond(200, {"ok": True})

        # PUT /context/{user_id}
        elif len(parts) == 2 and parts[0] == "context":
            user_id = parts[1]
            _write_json(os.path.join(_user_dir(user_id), "bot_context.json"), body)
            # Legacy path too
            _write_json(os.path.join(DATA_DIR, f"bot_context_{user_id}.json"), body)
            self._respond(200, {"ok": True})

        # PUT /calendario/{user_id}
        elif len(parts) == 2 and parts[0] == "calendario":
            user_id = parts[1]
            _write_json(os.path.join(_user_dir(user_id), "calendario.json"), body)
            _write_json(os.path.join(DATA_DIR, f"calendario_{user_id}.json"), body)
            self._respond(200, {"ok": True})

        # PUT /instrucciones/{user_id}
        elif len(parts) == 2 and parts[0] == "instrucciones":
            user_id = parts[1]
            _write_json(os.path.join(_user_dir(user_id), "instrucciones.json"), body)
            self._respond(200, {"ok": True})

        # PUT /cache/{colegio_id}/{source}
        elif len(parts) == 3 and parts[0] == "cache":
            colegio_id, source = parts[1], parts[2]
            cache_path = os.path.join(_cache_dir(colegio_id), f"{source}.json")
            _write_json(cache_path, body)
            # Update meta
            meta_path = os.path.join(_cache_dir(colegio_id), "_meta.json")
            meta = _read_json(meta_path, {})
            meta[source] = datetime.now(CHILE_TZ).isoformat()
            _write_json(meta_path, meta)
            self._respond(200, {"ok": True})

        # PUT /meta/{user_id}/{source}
        elif len(parts) == 3 and parts[0] == "meta":
            user_id, source = parts[1], parts[2]
            meta_path = os.path.join(_user_dir(user_id), "meta.json")
            meta = _read_json(meta_path, {})
            meta[source] = datetime.now(CHILE_TZ).isoformat()
            _write_json(meta_path, meta)
            self._respond(200, {"ok": True})

        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        self.do_PUT()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")

        # DELETE /users/{user_id}
        if len(parts) == 2 and parts[0] == "users":
            user_id = parts[1]
            import shutil
            # Remove user config
            cfg_path = os.path.join(CONFIG_DIR, "users", f"{user_id}.json")
            if os.path.exists(cfg_path):
                os.remove(cfg_path)
            # Remove user data dir
            user_dir = os.path.join(DATA_DIR, user_id)
            if os.path.isdir(user_dir):
                shutil.rmtree(user_dir)
            # Remove legacy files
            for f in [f"bot_context_{user_id}.json", f"calendario_{user_id}.json", f"monitor_inputs_{user_id}.json"]:
                p = os.path.join(DATA_DIR, f)
                if os.path.exists(p):
                    os.remove(p)
            self._respond(200, {"ok": True, "message": f"User {user_id} deleted"})
        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), StorageHandler)
    print(f"Storage service listening on :{PORT}")
    print(f"  DATA_DIR: {DATA_DIR}")
    print(f"  CONFIG_DIR: {CONFIG_DIR}")
    server.serve_forever()
