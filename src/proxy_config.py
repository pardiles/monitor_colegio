"""
Configuración de proxy residencial (IPRoyal).

Cuando se contrate IPRoyal, configurar en .env:
  PROXY_HOST=geo.iproyal.com
  PROXY_PORT=12321
  PROXY_USER=tu_usuario
  PROXY_PASS=tu_password
  PROXY_COUNTRY=cl

El proxy se usa en:
  - Playwright (SchoolNet, extracurriculares) → proxy en browser context
  - Requests (APIs, gmail) → NO necesita proxy (son APIs legítimas)

Solo scraping a sitios con Cloudflare necesita proxy residencial.
APIs (calendario JSON, Gmail API, WAHA) NO lo necesitan.
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
    
    Soporta 2 modos:
    - Static residential: IP fija permanente
    - Rotating residential (sticky): IP fija por 30 min (más barato, Chile disponible)
    
    Para IPRoyal rotating con sticky session, el username incluye parámetros:
      usuario_country-cl_session-XXXX_lifetime-30m
    
    Uso:
        from src.proxy_config import get_playwright_proxy
        proxy = get_playwright_proxy()
        context = browser.new_context(proxy=proxy) if proxy else browser.new_context()
    """
    cfg = get_proxy_config()
    if not cfg:
        return None

    username = cfg["user"]
    # Si tiene country, agregarlo al username (formato IPRoyal rotating)
    if cfg["country"] and "_country-" not in username:
        username = f"{username}_country-{cfg['country']}"
    # Agregar sticky session si no está ya (mantiene IP por 30 min)
    if "_session-" not in username:
        import hashlib, time
        # Session ID basado en la hora (cambia cada 30 min)
        session_id = hashlib.md5(f"{int(time.time() // 1800)}".encode()).hexdigest()[:8]
        username = f"{username}_session-{session_id}_lifetime-30m"

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

    username = cfg["user"]
    if cfg["country"] and "_country-" not in username:
        username = f"{username}_country-{cfg['country']}"
    if "_session-" not in username:
        import hashlib, time
        session_id = hashlib.md5(f"{int(time.time() // 1800)}".encode()).hexdigest()[:8]
        username = f"{username}_session-{session_id}_lifetime-30m"

    proxy_url = f"http://{username}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }
