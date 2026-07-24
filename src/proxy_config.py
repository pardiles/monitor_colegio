"""
Configuración de proxy residencial — Bright Data ISP (Static Chile).

Bright Data ISP Proxies:
  - Chile IP fija permanente
  - $1.80/IP/mes (plan 10 IPs = $18/mes)
  - Bandwidth ilimitado incluido
  - Misma IP para WAHA + SchoolNet + Extraprogramáticas

Configurar en .env:
  PROXY_HOST=brd.superproxy.io
  PROXY_PORT=33335
  PROXY_USER=brd-customer-hl_439f135d-zone-monitor_colegio_cl
  PROXY_PASS=u997kloltv8s

La misma IP se usa para:
  - WAHA (WhatsApp) — sesión permanente 24/7
  - SchoolNet (Playwright login)
  - Extraprogramáticas (Cloudflare bypass)

1 IP fija por cada 10 usuarios (plan de escalamiento).
"""

import os

# Cargar .env si existe (para ejecución standalone sin main.py)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.environ.get("PROJECT_DIR", "/opt/monitor-colegio"), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        load_dotenv()
except ImportError:
    pass


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

    Bright Data ISP format:
      server: http://brd.superproxy.io:33335
      username: brd-customer-XXXXX-zone-XXXXX
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
