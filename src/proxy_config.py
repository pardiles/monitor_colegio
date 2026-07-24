"""
Configuración de proxy residencial — Bright Data ISP (Static Chile).

Soporta pool de múltiples IPs:
  PROXY_POOL=zone1:pass1,zone2:pass2,zone3:pass3
  (o 1 sola: PROXY_USER + PROXY_PASS)

Cada usuario tiene asignado un proxy_ip_index (0, 1, 2...).
1 IP por cada 10 usuarios. Asignación en el registro (Lambda).

Configurar en .env:
  PROXY_HOST=brd.superproxy.io
  PROXY_PORT=33335
  # Opción 1: una sola IP (hoy)
  PROXY_USER=brd-customer-hl_439f135d-zone-monitor_colegio_cl
  PROXY_PASS=u997kloltv8s
  # Opción 2: pool de IPs (futuro)
  # PROXY_POOL=brd-customer-xxx-zone-ip1:pass1,brd-customer-xxx-zone-ip2:pass2

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


def _get_pool():
    """Obtener pool de proxies. Retorna lista de {user, password}."""
    pool_str = os.environ.get("PROXY_POOL", "")
    if pool_str:
        # Formato: user1:pass1,user2:pass2,...
        entries = []
        for entry in pool_str.split(","):
            parts = entry.strip().split(":", 1)
            if len(parts) == 2:
                entries.append({"user": parts[0], "password": parts[1]})
        if entries:
            return entries

    # Fallback: una sola IP
    user = os.environ.get("PROXY_USER", "")
    password = os.environ.get("PROXY_PASS", "")
    if user and password:
        return [{"user": user, "password": password}]

    return []


def get_proxy_config(ip_index: int = 0):
    """Obtener configuración de proxy para un índice específico.
    
    Args:
        ip_index: índice del proxy en el pool (0, 1, 2...).
                  Si el índice excede el pool, hace round-robin.
    
    Returns None si no hay proxy configurado.
    """
    host = os.environ.get("PROXY_HOST", "")
    port = os.environ.get("PROXY_PORT", "")

    if not host or not port:
        return None

    pool = _get_pool()
    if not pool:
        return None

    # Round-robin si el índice excede el pool
    entry = pool[ip_index % len(pool)]

    return {
        "host": host,
        "port": int(port),
        "user": entry["user"],
        "password": entry["password"],
        "ip_index": ip_index,
        "pool_size": len(pool),
    }


def get_proxy_for_user(user_cfg: dict = None):
    """Obtener proxy para un usuario específico según su ip_index asignado.
    
    Lee proxy_ip_index de la config del usuario. Si no tiene, usa 0.
    """
    ip_index = 0
    if user_cfg:
        ip_index = user_cfg.get("proxy_ip_index", 0)
    return get_proxy_config(ip_index)


def get_playwright_proxy(user_cfg: dict = None):
    """Obtener proxy formateado para Playwright browser context.

    Uso:
        from src.proxy_config import get_playwright_proxy
        proxy = get_playwright_proxy(user_cfg)
        context = browser.new_context(proxy=proxy) if proxy else browser.new_context()
    """
    cfg = get_proxy_for_user(user_cfg)
    if not cfg:
        return None

    return {
        "server": f"http://{cfg['host']}:{cfg['port']}",
        "username": cfg["user"],
        "password": cfg["password"],
    }


def get_requests_proxy(user_cfg: dict = None):
    """Obtener proxy formateado para requests library.

    Uso:
        from src.proxy_config import get_requests_proxy
        proxies = get_requests_proxy(user_cfg)
        response = requests.get(url, proxies=proxies)
    """
    cfg = get_proxy_for_user(user_cfg)
    if not cfg:
        return None

    proxy_url = f"http://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def get_docker_proxy_env(ip_index: int = 0):
    """Obtener variables de entorno para Docker (WAHA).

    Para configurar WAHA con proxy:
      docker run -e HTTP_PROXY=... -e HTTPS_PROXY=... -e NO_PROXY=localhost,127.0.0.1

    Uso:
        from src.proxy_config import get_docker_proxy_env
        env = get_docker_proxy_env(ip_index=0)
    """
    cfg = get_proxy_config(ip_index)
    if not cfg:
        return None

    proxy_url = f"http://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
    return {
        "HTTP_PROXY": proxy_url,
        "HTTPS_PROXY": proxy_url,
        "NO_PROXY": "localhost,127.0.0.1",
    }


def assign_ip_index(current_users: list) -> int:
    """Asignar un ip_index a un nuevo usuario.
    
    Estrategia: asignar al índice con menos usuarios (balanceo).
    
    Args:
        current_users: lista de configs de usuarios existentes
        
    Returns:
        ip_index para el nuevo usuario
    """
    pool = _get_pool()
    if not pool:
        return 0

    # Contar usuarios por ip_index
    counts = [0] * len(pool)
    for u in current_users:
        idx = u.get("proxy_ip_index", 0)
        if idx < len(counts):
            counts[idx] += 1

    # Asignar al que tenga menos (máximo 10 por IP)
    for i, count in enumerate(counts):
        if count < 10:
            return i

    # Todas llenas → asignar al primero (overflow)
    return 0
