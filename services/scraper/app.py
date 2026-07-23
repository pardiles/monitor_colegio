"""
Scraper Service — Extrae datos de fuentes del colegio.
Puerto: 8081

Endpoints:
  POST /scrape/{user_id}              — Scraping completo de un usuario
  POST /scrape/{user_id}/fast         — Scraping rápido (solo detectar hijos)
  POST /scrape/shared/{colegio_id}    — Scraping de fuentes compartidas (calendario, casino, scinfo)
  GET  /sources                       — Listar fuentes disponibles
  GET  /health                        — Health check

Dependencias:
  - storage (8084): para leer config usuario y guardar resultados
"""

import os
import sys
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
from zoneinfo import ZoneInfo

# Agregar path del proyecto para importar módulos
sys.path.insert(0, os.environ.get("PROJECT_DIR", "/opt/monitor-colegio"))

CHILE_TZ = ZoneInfo("America/Santiago")
PORT = int(os.environ.get("SCRAPER_PORT", "8081"))
STORAGE_URL = os.environ.get("STORAGE_URL", "http://localhost:8084")

AVAILABLE_SOURCES = [
    {"id": "schoolnet", "name": "SchoolNet (Colegium)", "type": "per_user", "frequency": "2x/day"},
    {"id": "calendario", "name": "Calendario evaluaciones", "type": "shared", "frequency": "1x/day"},
    {"id": "casino", "name": "Casino/Menú", "type": "shared", "frequency": "1x/day"},
    {"id": "scinfo", "name": "SC Info", "type": "shared", "frequency": "1x/week"},
    {"id": "gmail", "name": "Gmail", "type": "per_user", "frequency": "2x/day"},
    {"id": "web_colegio", "name": "Web del colegio", "type": "shared", "frequency": "1x/day"},
    {"id": "extraprogramaticas", "name": "Extraprogramáticas", "type": "per_user", "frequency": "1x/semester"},
]


def _storage_get(path):
    try:
        r = requests.get(f"{STORAGE_URL}/{path}", timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _storage_put(path, data):
    try:
        requests.put(f"{STORAGE_URL}/{path}", json=data, timeout=5)
    except Exception:
        pass


def scrape_user(user_id, fast=False):
    """Ejecutar scraping para un usuario. Retorna datos obtenidos."""
    # Leer config del usuario desde storage
    resp = _storage_get(f"users/{user_id}")
    if not resp or not resp.get("ok"):
        return {"error": f"User {user_id} not found"}

    user_cfg = resp["data"]
    results = {"user_id": user_id, "timestamp": datetime.now(CHILE_TZ).isoformat(), "sources": {}}

    # Importar scrapers
    try:
        from src.sources.schoolnet import SchoolNetClient
        from src.sources.calendario import fetch_evaluaciones
        from src.sources.gmail_source import GmailClient
    except ImportError as e:
        return {"error": f"Import error: {e}"}

    colegio = user_cfg.get("colegio", {})

    # SchoolNet
    sn_user = colegio.get("schoolnet_user", "")
    sn_pass = colegio.get("schoolnet_pass", "")
    if sn_user and sn_pass:
        try:
            sn = SchoolNetClient(sn_user, sn_pass)
            if sn.login():
                results["sources"]["schoolnet"] = {"status": "ok"}

                if fast:
                    # Solo detectar hijos
                    hijos_raw = sn.get_asistencia(0)
                    results["sources"]["schoolnet"]["hijos_detected"] = True
                else:
                    # Scraping completo
                    results["sources"]["schoolnet"]["comunicaciones"] = sn.get_comunicaciones()
                    results["sources"]["schoolnet"]["pagos"] = sn.get_pagos()
                    hijos = user_cfg.get("hijos", [])
                    for i, hijo in enumerate(hijos):
                        nombre = hijo["nombre"].lower()
                        try:
                            results["sources"]["schoolnet"][f"calificaciones_{nombre}"] = sn.get_calificaciones(i)
                        except Exception:
                            pass
                        try:
                            results["sources"]["schoolnet"][f"asistencia_{nombre}"] = sn.get_asistencia(i)
                        except Exception:
                            pass
            else:
                results["sources"]["schoolnet"] = {"status": "login_failed"}
        except Exception as e:
            results["sources"]["schoolnet"] = {"status": "error", "error": str(e)}

    # Calendario (compartido — check cache first)
    if colegio.get("calendario_url") and not fast:
        colegio_id = colegio.get("nombre", "").lower().replace(" ", "_")
        cache_check = _storage_get(f"cache/{colegio_id}/evaluaciones/fresh?max_hours=12")
        if cache_check and cache_check.get("fresh"):
            cached = _storage_get(f"cache/{colegio_id}/evaluaciones")
            if cached and cached.get("ok"):
                results["sources"]["calendario"] = {"status": "cache", "data": cached["data"]}
        else:
            try:
                categorias = []
                for h in user_cfg.get("hijos", []):
                    import re
                    m = re.match(r'^(\d+)', h.get("curso", ""))
                    if m:
                        categorias.append(m.group(1))
                if categorias:
                    data = fetch_evaluaciones(categorias)
                    results["sources"]["calendario"] = {"status": "ok", "data": data}
                    _storage_put(f"cache/{colegio_id}/evaluaciones", data)
            except Exception as e:
                results["sources"]["calendario"] = {"status": "error", "error": str(e)}

    # Gmail
    if not fast:
        try:
            from src.sources.gmail_source import GmailClient
            gmail_cfg = user_cfg.get("gmail", {})
            token_file = ""
            creds_file = ""
            # Check S3 token
            import os as _os
            s3_token = _os.path.join("config", "tokens", f"{user_id}_gmail_token.json")
            if _os.path.exists(s3_token):
                token_file = s3_token
            elif isinstance(gmail_cfg, dict):
                token_file = gmail_cfg.get("token_file", "")
                creds_file = gmail_cfg.get("credentials_file", "")
            if token_file and _os.path.exists(token_file):
                gmail = GmailClient(creds_file, token_file)
                gmail.authenticate()
                emails = gmail.get_school_emails(days=7)
                results["sources"]["gmail"] = {"status": "ok", "count": len(emails), "data": emails}
            else:
                results["sources"]["gmail"] = {"status": "no_token"}
        except Exception as e:
            results["sources"]["gmail"] = {"status": "error", "error": str(e)}

    # Casino (compartido — check cache)
    if colegio.get("casino_url") and not fast:
        colegio_id = colegio.get("nombre", "").lower().replace(" ", "_")
        cache_check = _storage_get(f"cache/{colegio_id}/casino/fresh?max_hours=12")
        if cache_check and cache_check.get("fresh"):
            cached = _storage_get(f"cache/{colegio_id}/casino")
            if cached and cached.get("ok"):
                results["sources"]["casino"] = {"status": "cache", "data": cached["data"]}
        else:
            try:
                from src.sources.casino import fetch_casino_menu, fetch_casino_menu_today
                casino_data = fetch_casino_menu(colegio["casino_url"])
                menu_hoy = fetch_casino_menu_today(colegio["casino_url"])
                results["sources"]["casino"] = {"status": "ok", "data": casino_data}
                if menu_hoy:
                    results["sources"]["casino_hoy"] = menu_hoy
                _storage_put(f"cache/{colegio_id}/casino", casino_data)
                if menu_hoy:
                    _storage_put(f"cache/{colegio_id}/casino_hoy", menu_hoy)
            except Exception as e:
                results["sources"]["casino"] = {"status": "error", "error": str(e)}

    # SC Info (compartido — check cache, 7 días)
    if colegio.get("scinfo_url") and not fast:
        colegio_id = colegio.get("nombre", "").lower().replace(" ", "_")
        cache_check = _storage_get(f"cache/{colegio_id}/scinfo/fresh?max_hours=168")
        if cache_check and cache_check.get("fresh"):
            cached = _storage_get(f"cache/{colegio_id}/scinfo")
            if cached and cached.get("ok"):
                results["sources"]["scinfo"] = {"status": "cache", "data": cached["data"]}
        else:
            try:
                from src.sources.scinfo import fetch_scinfo_latest
                scinfo_data = fetch_scinfo_latest()
                results["sources"]["scinfo"] = {"status": "ok", "data": scinfo_data}
                _storage_put(f"cache/{colegio_id}/scinfo", scinfo_data)
            except Exception as e:
                results["sources"]["scinfo"] = {"status": "error", "error": str(e)}

    # Web del colegio (noticias, talleres — compartido)
    if not fast:
        web_urls = {}
        if colegio.get("noticias_url"):
            web_urls["noticias"] = colegio["noticias_url"]
        if colegio.get("talleres_url"):
            web_urls["talleres"] = colegio["talleres_url"]
        if colegio.get("extraprogramaticas_url"):
            web_urls["talleres"] = colegio["extraprogramaticas_url"]
        if colegio.get("deportiva_url"):
            web_urls["deportiva"] = colegio["deportiva_url"]

        if web_urls or colegio.get("web_url"):
            try:
                from src.sources.web_colegio import WebColegioScraper
                scraper = WebColegioScraper(colegio.get("web_url", ""), web_urls)
                web_data = scraper.scrape_all()
                if web_data:
                    results["sources"]["web_colegio"] = {"status": "ok", "data": web_data}
            except Exception as e:
                results["sources"]["web_colegio"] = {"status": "error", "error": str(e)}

    # Guardar resultados en storage
    _storage_put(f"meta/{user_id}/scraper", {})

    return results


class ScraperHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
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
            self._respond(200, {"ok": True, "service": "scraper", "port": PORT})
        elif parts == ["sources"]:
            self._respond(200, {"sources": AVAILABLE_SOURCES})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")

        # POST /scrape/{user_id}
        if len(parts) == 2 and parts[0] == "scrape":
            user_id = parts[1]
            result = scrape_user(user_id, fast=False)
            self._respond(200, result)

        # POST /scrape/{user_id}/fast
        elif len(parts) == 3 and parts[0] == "scrape" and parts[2] == "fast":
            user_id = parts[1]
            result = scrape_user(user_id, fast=True)
            self._respond(200, result)

        else:
            self._respond(404, {"error": "Not found"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), ScraperHandler)
    print(f"Scraper service listening on :{PORT}")
    print(f"  Storage: {STORAGE_URL}")
    print(f"  Sources: {len(AVAILABLE_SOURCES)}")
    server.serve_forever()
