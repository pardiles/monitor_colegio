"""
Onboarding Service — Registro y vinculación de usuarios nuevos.
Puerto: 8085

Endpoints:
  POST /register             — Registrar/actualizar usuario
  POST /vincular/{user_id}   — Iniciar vinculación WA (crear sesión WAHA)
  GET  /status/{user_id}     — Estado de vinculación (WA + Gmail)
  POST /welcome/{user_id}    — Disparar primer resumen de bienvenida
  POST /authorize            — Agregar email a lista autorizada
  GET  /authorized           — Listar emails autorizados
  GET  /health               — Health check

Dependencias:
  - storage (8084): guardar config usuario
  - wa-handler (8080): crear sesión, obtener QR
  - scraper (8081): scrape inicial (fast)
  - orchestrator (8083): disparar ciclo de bienvenida
"""

import os
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")
PORT = int(os.environ.get("ONBOARDING_PORT", "8085"))
STORAGE_URL = os.environ.get("STORAGE_URL", "http://localhost:8084")
WA_HANDLER_URL = os.environ.get("WA_HANDLER_URL", "http://localhost:8080")
SCRAPER_URL = os.environ.get("SCRAPER_URL", "http://localhost:8081")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8083")
ADMIN_EMAILS = ["pardiles@gmail.com"]


def register_user(body):
    """Registrar o actualizar un usuario."""
    nombre = body.get("nombre", "").strip()
    user_id = body.get("user_id", "") or nombre.lower().replace(" ", "_")
    if not user_id:
        return {"ok": False, "error": "user_id requerido"}

    # Leer config existente
    existing = {}
    try:
        r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
        if r.status_code == 200 and r.json().get("ok"):
            existing = r.json()["data"]
    except Exception:
        pass

    # Merge
    config = {**existing, "id": user_id}
    for field in ["nombre", "telefono", "hijos", "extraprogramaticas", "regimen",
                  "whatsapp", "whatsapp_groups", "colegio", "colegios", "step"]:
        if body.get(field):
            config[field] = body[field]

    # Guardar
    try:
        requests.put(f"{STORAGE_URL}/users/{user_id}", json=config, timeout=5)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "user_id": user_id}


def vincular_whatsapp(user_id):
    """Iniciar sesión WAHA para vincular WhatsApp."""
    session_name = user_id.replace(" ", "_")
    try:
        r = requests.post(f"{WA_HANDLER_URL}/api/session/start",
                         json={"session": session_name}, timeout=10)
        result = r.json() if r.status_code == 200 else {"error": r.text}
        return {"ok": True, "session": session_name, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_status(user_id):
    """Obtener estado de vinculación WA + Gmail."""
    session_name = user_id.replace(" ", "_")
    result = {"user_id": user_id, "wa_status": "unknown", "gmail_linked": False}

    # WA status
    try:
        r = requests.get(f"{WA_HANDLER_URL}/api/session/status?session={session_name}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            result["wa_status"] = data.get("status", "unknown")
    except Exception:
        pass

    # Gmail status (check if token exists in storage)
    # This would check S3 via storage — simplified for now
    result["gmail_linked"] = False  # TODO: check token in S3

    return result


def trigger_welcome(user_id):
    """Disparar primer resumen de bienvenida."""
    try:
        r = requests.post(f"{ORCHESTRATOR_URL}/run/{user_id}",
                         json={"mode": "evening"}, timeout=180)
        return r.json() if r.status_code == 200 else {"error": r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class OnboardingHandler(BaseHTTPRequestHandler):
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
        parts = urlparse(self.path).path.strip("/").split("/")
        if parts == ["health"]:
            self._respond(200, {"ok": True, "service": "onboarding", "port": PORT})
        elif len(parts) == 2 and parts[0] == "status":
            result = get_status(parts[1])
            self._respond(200, result)
        elif parts == ["authorized"]:
            # TODO: leer lista de S3 via storage
            self._respond(200, {"emails": [], "message": "TODO"})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        body = self._read_body()

        if parts == ["register"]:
            result = register_user(body)
            self._respond(200, result)
        elif len(parts) == 2 and parts[0] == "vincular":
            result = vincular_whatsapp(parts[1])
            self._respond(200, result)
        elif len(parts) == 2 and parts[0] == "welcome":
            result = trigger_welcome(parts[1])
            self._respond(200, result)
        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), OnboardingHandler)
    print(f"Onboarding service listening on :{PORT}")
    server.serve_forever()
