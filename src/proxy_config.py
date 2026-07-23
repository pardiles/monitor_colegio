"""
Configuración de proxy residencial — Bright Data.

Bright Data Residential Proxies:
  - Chile disponible (pay-as-you-go $8/GB)
  - Rotating con sticky session (misma IP por 30 min)
  - ~250KB por usuario por ciclo = centavos/mes

Configurar en .env:
  PROXY_HOST=brd.superproxy.io
  PROXY_PORT=33335
  PROXY_USER=brd-customer-XXXXX-zone-residential
  PROXY_PASS=XXXXX
  PROXY_COUNTRY=cl

El proxy se usa en:
  - Playwright (SchoolNet login, extracurriculares) → proxy en browser context
  - Requests (si se necesita) → proxies dict

Solo scraping a sitios con Cloudflare/anti-bot necesita proxy.
APIs legítimas (calendario JSON, Gmail API, WAHA) NO lo necesitan.
"""

import os
import hashlib
import time


def get_proxy_config():
    """Obtener configuración de proxy desde .env.
    Returns None si no está configurado.
    """
    host = os.environ.get("PROXY_HOST", "")
    port = os.environ.get("PROXY_PORT", "")
    user = os.environ.get("PROXY_USER", "")
    password = os.environ.get("PROXY_PASS", "")
    country = os.environ.get("PROXY_COUNTRY", "cl")

    if not host or not port:
        return None

    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "country": country,
    }


def get_playwright_proxy():
    """Obtener proxy formateado para Playwright browser context.

    Bright Data format:
      username: brd-customer-XXXXX-zone-residential-country-cl-session-XXX
      password: XXXXX
      server: http://brd.superproxy.io:33335

    Uso:
        from src.proxy_config import get_playwright_proxy
        proxy = get_playwright_proxy()
        context = browser.new_context(proxy=proxy) if proxy else browser.new_context()
    """
    cfg = get_proxy_config()
    if not cfg:
        return None

    # Sticky session: misma IP por 30 min (suficiente para cualquier scrape)
    session_id = hashlib.md5(f"{int(time.time() // 1800)}".encode()).hexdigest()[:8]

    username = cfg["user"]
    if cfg["country"] and f"-country-{cfg['country']}" not in username:
        username = f"{username}-country-{cfg['country']}"
    username = f"{username}-session-{session_id}"

    return {
        "server": f"http://{cfg['host']}:{cfg['port']}",
        "username": username,
        "password": cfg["password"],
    }


def get_requests_proxy():
    """Obtener proxy formateado para requests library.

    Uso:
        from src.proxy_config import get_requests_proxy
        proxies = get_requests_proxy()
        response = requests.get(url, proxies=proxies)
    """
    cfg = get_proxy_config()
    if not cfg:
        return None

    session_id = hashlib.md5(f"{int(time.time() // 1800)}".encode()).hexdigest()[:8]

    username = cfg["user"]
    if cfg["country"] and f"-country-{cfg['country']}" not in username:
        username = f"{username}-country-{cfg['country']}"
    username = f"{username}-session-{session_id}"

    proxy_url = f"http://{username}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }
