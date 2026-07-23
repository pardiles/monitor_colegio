"""
Orchestrator Service — Coordinación y scheduling.
Puerto: 8083

Endpoints:
  POST /run/{user_id}         — Ejecutar ciclo completo para un usuario (scrape + resumen + envío)
  POST /run-all               — Ejecutar ciclo para todos los usuarios
  POST /run-all/{mode}        — Ejecutar ciclo AM/PM para todos
  GET  /status                — Estado del sistema (sesiones WA, último run, etc.)
  GET  /health                — Health check

Dependencias:
  - storage (8084): listar usuarios, leer configs
  - scraper (8081): ejecutar scraping
  - summarizer (8082): generar resúmenes
  - wa-handler (8080): enviar mensajes via outbox
"""

import os
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")
PORT = int(os.environ.get("ORCHESTRATOR_PORT", "8083"))
STORAGE_URL = os.environ.get("STORAGE_URL", "http://localhost:8084")
SCRAPER_URL = os.environ.get("SCRAPER_URL", "http://localhost:8081")
SUMMARIZER_URL = os.environ.get("SUMMARIZER_URL", "http://localhost:8082")
WA_HANDLER_URL = os.environ.get("WA_HANDLER_URL", "http://localhost:8080")


def run_cycle(user_id, mode="morning", force=False):
    """Ejecutar ciclo completo: scrape → resumen → envío."""
    log = []
    now = datetime.now(CHILE_TZ)

    # 1. Scrape
    log.append(f"[{now.strftime('%H:%M:%S')}] Scraping {user_id}...")
    try:
        r = requests.post(f"{SCRAPER_URL}/scrape/{user_id}", timeout=120)
        scrape_result = r.json() if r.status_code == 200 else {"error": r.text}
        log.append(f"  Scrape: {list(scrape_result.get('sources', {}).keys())}")
    except Exception as e:
        log.append(f"  Scrape ERROR: {e}")
        scrape_result = {}

    # 2. Generate summary
    log.append(f"[{now.strftime('%H:%M:%S')}] Generating summary...")
    is_weekly = (now.weekday() == 6 and mode == "evening")
    try:
        r = requests.post(f"{SUMMARIZER_URL}/generate", json={
            "user_id": user_id, "mode": mode, "is_weekly": is_weekly
        }, timeout=30)
        summary_result = r.json() if r.status_code == 200 else {"error": r.text}
        message = summary_result.get("message", "")
        log.append(f"  Summary: {len(message)} chars ({summary_result.get('engine', '?')})")
    except Exception as e:
        log.append(f"  Summary ERROR: {e}")
        return {"ok": False, "log": log, "error": str(e)}

    if not message:
        log.append("  No message generated, skipping send")
        return {"ok": True, "log": log, "skipped": True}

    # 3. Send via outbox
    log.append(f"[{now.strftime('%H:%M:%S')}] Sending...")
    try:
        # Get user's grupo_monitor
        r = requests.get(f"{STORAGE_URL}/users/{user_id}", timeout=5)
        user_cfg = r.json().get("data", {}) if r.status_code == 200 else {}
        grupo = user_cfg.get("whatsapp", {}).get("grupo_monitor")
        if not grupo:
            targets = [n + "@s.whatsapp.net" for n in user_cfg.get("whatsapp", {}).get("destinatarios_monitor", [])]
        else:
            targets = [grupo]

        if targets:
            # Write outbox file directly (wa_handler picks it up)
            import time
            outbox_dir = os.path.join(os.environ.get("DATA_DIR", "/opt/monitor-colegio/data"), "outbox")
            os.makedirs(outbox_dir, exist_ok=True)
            outbox_file = os.path.join(outbox_dir, f"{user_id}_{int(time.time()*1000)}.json")
            outbox_data = {
                "user_id": user_id,
                "targets": targets,
                "message": message.replace("**", "*"),
                "created_at": datetime.now(CHILE_TZ).isoformat(),
                "status": "pending",
            }
            with open(outbox_file, "w", encoding="utf-8") as f:
                json.dump(outbox_data, f, indent=2, ensure_ascii=False)
            os.chmod(outbox_file, 0o666)
            log.append(f"  Sent to outbox: {targets}")
        else:
            log.append("  No targets configured, skipping")
    except Exception as e:
        log.append(f"  Send ERROR: {e}")

    return {"ok": True, "log": log}


class OrchestratorHandler(BaseHTTPRequestHandler):
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
            self._respond(200, {"ok": True, "service": "orchestrator", "port": PORT})
        elif parts == ["status"]:
            # Check all services
            services = {}
            for name, url in [("storage", STORAGE_URL), ("scraper", SCRAPER_URL),
                              ("summarizer", SUMMARIZER_URL), ("wa-handler", WA_HANDLER_URL)]:
                try:
                    r = requests.get(f"{url}/health", timeout=2)
                    services[name] = r.json() if r.status_code == 200 else {"status": "error"}
                except Exception:
                    services[name] = {"status": "down"}
            self._respond(200, {"services": services, "time": datetime.now(CHILE_TZ).isoformat()})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        body = self._read_body()

        # POST /run/{user_id}
        if len(parts) == 2 and parts[0] == "run":
            user_id = parts[1]
            mode = body.get("mode", "morning")
            result = run_cycle(user_id, mode=mode)
            self._respond(200, result)

        # POST /run-all or /run-all/{mode}
        elif parts[0] == "run-all":
            mode = parts[1] if len(parts) > 1 else body.get("mode", "morning")
            # Get all users
            try:
                r = requests.get(f"{STORAGE_URL}/users", timeout=5)
                users = r.json().get("users", []) if r.status_code == 200 else []
            except Exception:
                users = []
            results = {}
            for u in users:
                uid = u["id"]
                results[uid] = run_cycle(uid, mode=mode)
            self._respond(200, {"mode": mode, "users_processed": len(results), "results": results})

        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), OrchestratorHandler)
    print(f"Orchestrator service listening on :{PORT}")
    print(f"  Storage: {STORAGE_URL}")
    print(f"  Scraper: {SCRAPER_URL}")
    print(f"  Summarizer: {SUMMARIZER_URL}")
    server.serve_forever()
