"""
Admin Service — Dashboard y acciones administrativas.
Puerto: 8087

Endpoints:
  GET  /dashboard              — Resumen del sistema (usuarios, servicios, último run)
  GET  /users                  — Listar usuarios con estado
  GET  /users/{user_id}        — Detalle de un usuario
  POST /users/{user_id}/rescrape — Forzar re-scraping
  POST /users/{user_id}/resend   — Re-enviar último resumen
  POST /users/{user_id}/pause    — Pausar usuario
  POST /users/{user_id}/activate — Activar usuario
  GET  /logs                   — Últimas líneas de log
  GET  /services               — Estado de todos los servicios
  GET  /health                 — Health check

Dependencias:
  - storage (8084): datos de usuarios
  - orchestrator (8083): forzar ciclos
  - wa-handler (8080): estado WA
"""

import os
import json
import subprocess
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")
PORT = int(os.environ.get("ADMIN_PORT", "8087"))
STORAGE_URL = os.environ.get("STORAGE_URL", "http://localhost:8084")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8083")
WA_HANDLER_URL = os.environ.get("WA_HANDLER_URL", "http://localhost:8080")
SCRAPER_URL = os.environ.get("SCRAPER_URL", "http://localhost:8081")
SUMMARIZER_URL = os.environ.get("SUMMARIZER_URL", "http://localhost:8082")
RAG_URL = os.environ.get("RAG_URL", "http://localhost:8086")
LOG_FILE = os.environ.get("LOG_FILE", "/var/log/monitor-colegio.log")


def _check_service(name, url):
    try:
        r = requests.get(f"{url}/health", timeout=2)
        if r.status_code == 200:
            return {"status": "up", **r.json()}
        return {"status": "error", "code": r.status_code}
    except Exception:
        return {"status": "down"}


def get_dashboard():
    """Resumen general del sistema."""
    # Usuarios
    try:
        r = requests.get(f"{STORAGE_URL}/users", timeout=5)
        users = r.json().get("users", []) if r.status_code == 200 else []
    except Exception:
        users = []

    # Servicios
    services = {}
    for name, url in [
        ("storage", STORAGE_URL), ("scraper", SCRAPER_URL),
        ("summarizer", SUMMARIZER_URL), ("orchestrator", ORCHESTRATOR_URL),
        ("wa-handler", WA_HANDLER_URL), ("rag", RAG_URL),
    ]:
        services[name] = _check_service(name, url)

    # WA sessions
    wa_sessions = []
    try:
        r = requests.get(f"{WA_HANDLER_URL}/api/sessions", timeout=3)
        if r.status_code == 200:
            wa_sessions = r.json().get("sessions", [])
    except Exception:
        pass

    # Disk
    disk = "unknown"
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            disk = lines[1]
    except Exception:
        pass

    return {
        "time": datetime.now(CHILE_TZ).isoformat(),
        "users": {"count": len(users), "list": users},
        "services": services,
        "wa_sessions": wa_sessions,
        "disk": disk,
    }


def get_logs(n=50):
    """Últimas n líneas del log."""
    try:
        result = subprocess.run(["tail", "-n", str(n), LOG_FILE], capture_output=True, text=True, timeout=5)
        return result.stdout.split("\n")
    except Exception:
        return ["Log file not available"]


class AdminHandler(BaseHTTPRequestHandler):
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
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        query = parse_qs(parsed.query)

        if parts == ["health"]:
            self._respond(200, {"ok": True, "service": "admin", "port": PORT})

        elif parts == ["dashboard"]:
            self._respond(200, get_dashboard())

        elif parts == ["users"]:
            try:
                r = requests.get(f"{STORAGE_URL}/users", timeout=5)
                self._respond(200, r.json() if r.status_code == 200 else {"users": []})
            except Exception as e:
                self._respond(500, {"error": str(e)})

        elif len(parts) == 2 and parts[0] == "users":
            user_id = parts[1]
            try:
                r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
                data = r.json() if r.status_code == 200 else {"error": "Not found"}
                # Add WA status
                try:
                    wr = requests.get(f"{WA_HANDLER_URL}/api/session/status?session={user_id}", timeout=3)
                    data["wa_session"] = wr.json() if wr.status_code == 200 else {}
                except Exception:
                    pass
                # Add RAG stats
                try:
                    rr = requests.get(f"{RAG_URL}/stats/{user_id}", timeout=3)
                    data["rag_stats"] = rr.json() if rr.status_code == 200 else {}
                except Exception:
                    pass
                self._respond(200, data)
            except Exception as e:
                self._respond(500, {"error": str(e)})

        elif parts == ["services"]:
            services = {}
            for name, url in [
                ("storage", STORAGE_URL), ("scraper", SCRAPER_URL),
                ("summarizer", SUMMARIZER_URL), ("orchestrator", ORCHESTRATOR_URL),
                ("wa-handler", WA_HANDLER_URL), ("rag", RAG_URL),
            ]:
                services[name] = _check_service(name, url)
            self._respond(200, {"services": services})

        elif parts == ["logs"]:
            n = int(query.get("n", [50])[0])
            self._respond(200, {"lines": get_logs(n)})

        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")

        # POST /users/{user_id}/rescrape
        if len(parts) == 3 and parts[0] == "users" and parts[2] == "rescrape":
            user_id = parts[1]
            try:
                r = requests.post(f"{ORCHESTRATOR_URL}/run/{user_id}", json={"mode": "morning"}, timeout=180)
                self._respond(200, r.json() if r.status_code == 200 else {"error": r.text})
            except Exception as e:
                self._respond(500, {"error": str(e)})

        # POST /users/{user_id}/resend
        elif len(parts) == 3 and parts[0] == "users" and parts[2] == "resend":
            user_id = parts[1]
            # Re-send last message from data/mensaje_enviar_{user_id}.json
            msg_file = os.path.join(os.environ.get("DATA_DIR", "/opt/monitor-colegio/data"), f"mensaje_enviar_{user_id}.json")
            if os.path.exists(msg_file):
                try:
                    with open(msg_file) as f:
                        msg_data = json.load(f)
                    # Trigger send via node
                    result = subprocess.run(
                        ["node", "/opt/monitor-colegio/send_whatsapp.js", user_id],
                        capture_output=True, text=True, timeout=10
                    )
                    self._respond(200, {"ok": True, "output": result.stdout})
                except Exception as e:
                    self._respond(500, {"error": str(e)})
            else:
                self._respond(404, {"error": "No message file found"})

        # POST /users/{user_id}/pause
        elif len(parts) == 3 and parts[0] == "users" and parts[2] == "pause":
            user_id = parts[1]
            try:
                r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
                if r.status_code == 200:
                    cfg = r.json().get("data", {})
                    cfg["status"] = "paused"
                    requests.put(f"{STORAGE_URL}/users/{user_id}", json=cfg, timeout=5)
                self._respond(200, {"ok": True, "status": "paused"})
            except Exception as e:
                self._respond(500, {"error": str(e)})

        # POST /users/{user_id}/activate
        elif len(parts) == 3 and parts[0] == "users" and parts[2] == "activate":
            user_id = parts[1]
            try:
                r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
                if r.status_code == 200:
                    cfg = r.json().get("data", {})
                    cfg["status"] = "active"
                    requests.put(f"{STORAGE_URL}/users/{user_id}", json=cfg, timeout=5)
                self._respond(200, {"ok": True, "status": "active"})
            except Exception as e:
                self._respond(500, {"error": str(e)})

        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), AdminHandler)
    print(f"Admin service listening on :{PORT}")
    print(f"  Dashboard: http://localhost:{PORT}/dashboard")
    print(f"  Services:  http://localhost:{PORT}/services")
    print(f"  Users:     http://localhost:{PORT}/users")
    server.serve_forever()
