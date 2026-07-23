"""
Configuración de proxy residencial — Webshare ISP (Static).

Webshare Static Residential:
  - Chile disponible (316K+ IPs)
  - IP fija permanente (no rota)
  - $0.30/IP/mes ($6/mes por 20 IPs)
  - 10 IPs gratis para trial
  - HTTP + SOCKS5
  - Bandwidth ilimitado

Configurar en .env:
  PROXY_HOST=p.webshare.io
  PROXY_PORT=80
  PROXY_USER=XXXXX
  PROXY_PASS=XXXXX

La misma IP se usa para:
  - WAHA (WhatsApp) — sesión permanente 24/7
  - SchoolNet (Playwright login)
  - Extraprogramáticas (Cloudflare bypass)

1 IP fija por cada 10 usuarios (plan de escalamiento).
"""

import os


def get_proxy_config():
    """Obtener configuración de proxy desde .env.
    Returns None si no está configurado.
    """
    host = os.environ.get("PROXY_HOST", "")
    port = os.environ.get("PROXY_PORT", "")
    user = os.environ.get("PROXY_USER", "")
    password = os.environ.get("PROXY_PASS", "")

    if not host or not port:
        return None

    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
    }


def get_playwright_proxy():
    """Obtener proxy formateado para Playwright browser context.

    Webshare format (simple auth):
      server: http://p.webshare.io:80
      username: XXXXX
      password: XXXXX

    Uso:
        from src.proxy_config import get_playwright_proxy
        proxy = get_playwright_proxy()
        context = browser.new_context(proxy=proxy) if proxy else browser.new_context()
    """
    cfg = get_proxy_config()
    if not cfg:
        return None

    return {
        "server": f"http://{cfg['host']}:{cfg['port']}",
        "username": cfg["user"],
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

    proxy_url = f"http://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def get_docker_proxy_env():
    """Obtener variables de entorno para Docker (WAHA).

    Para configurar WAHA con proxy, agregar al docker run:
      -e HTTP_PROXY=http://user:pass@host:port
      -e HTTPS_PROXY=http://user:pass@host:port

    Uso:
        from src.proxy_config import get_docker_proxy_env
        env = get_docker_proxy_env()
        # docker run -e HTTP_PROXY={env['HTTP_PROXY']} ...
    """
    cfg = get_proxy_config()
    if not cfg:
        return None

    proxy_url = f"http://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
    return {
        "HTTP_PROXY": proxy_url,
        "HTTPS_PROXY": proxy_url,
    }
