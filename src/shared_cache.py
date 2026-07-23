"""
Cache compartido por colegio.

Fuentes que son IGUALES para todos los usuarios del mismo colegio:
- Calendario evaluaciones (API pública)
- Casino/menú del día (PDF mensual)
- SC Info (newsletter semanal)
- Noticias web del colegio
- Compañeros por curso (para cumpleaños)

Estas fuentes se scrappean UNA VEZ por colegio por ciclo (AM/PM)
y se reutilizan para todos los usuarios de ese colegio.

Estructura:
  data/shared/{colegio_id}/
  ├── evaluaciones.json       ← calendario pruebas
  ├── casino.json             ← menú completo del mes
  ├── casino_hoy.json         ← menú de hoy/mañana
  ├── scinfo.json             ← SC Info semanal
  ├── noticias.json           ← noticias web
  ├── companeros_{curso}.json ← lista compañeros (para cumpleaños)
  └── _meta.json              ← timestamps de última actualización
"""

import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")
SHARED_DIR = os.path.join("data", "shared")


def _get_colegio_id(user_cfg: dict) -> str:
    """Obtener un ID de colegio normalizado desde la config del usuario."""
    colegio = user_cfg.get("colegio", {})
    if colegio:
        # Usar nombre normalizado como ID
        nombre = colegio.get("nombre", "")
        if nombre:
            return nombre.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return ""


def _get_cache_dir(colegio_id: str) -> str:
    """Obtener directorio de cache para un colegio."""
    cache_dir = os.path.join(SHARED_DIR, colegio_id)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _load_meta(colegio_id: str) -> dict:
    """Cargar metadata de última actualización."""
    meta_file = os.path.join(_get_cache_dir(colegio_id), "_meta.json")
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_meta(colegio_id: str, meta: dict):
    """Guardar metadata de última actualización."""
    meta_file = os.path.join(_get_cache_dir(colegio_id), "_meta.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def _is_fresh(colegio_id: str, source: str, max_age_hours: float = 12) -> bool:
    """Verificar si un cache es fresco (no expirado)."""
    meta = _load_meta(colegio_id)
    last_update = meta.get(source, "")
    if not last_update:
        return False
    try:
        last_dt = datetime.fromisoformat(last_update)
        now = datetime.now(CHILE_TZ)
        # Si last_dt no tiene timezone, asumimos Chile
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=CHILE_TZ)
        age_hours = (now - last_dt).total_seconds() / 3600
        return age_hours < max_age_hours
    except Exception:
        return False


def _mark_updated(colegio_id: str, source: str):
    """Marcar una fuente como actualizada ahora."""
    meta = _load_meta(colegio_id)
    meta[source] = datetime.now(CHILE_TZ).isoformat()
    _save_meta(colegio_id, meta)


def get_cached(colegio_id: str, source: str, max_age_hours: float = 12):
    """Obtener datos cacheados si son frescos. Retorna None si expiró."""
    if not colegio_id:
        return None
    if not _is_fresh(colegio_id, source, max_age_hours):
        return None
    cache_file = os.path.join(_get_cache_dir(colegio_id), f"{source}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def set_cached(colegio_id: str, source: str, data):
    """Guardar datos en cache y marcar como actualizado."""
    if not colegio_id:
        return
    cache_file = os.path.join(_get_cache_dir(colegio_id), f"{source}.json")
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _mark_updated(colegio_id, source)


# --- Funciones de conveniencia por fuente ---

def get_evaluaciones(colegio_id: str):
    """Calendario evaluaciones — 1x/día (12h cache)."""
    return get_cached(colegio_id, "evaluaciones", max_age_hours=12)


def set_evaluaciones(colegio_id: str, data):
    set_cached(colegio_id, "evaluaciones", data)


def get_casino(colegio_id: str):
    """Casino menú — 1x/día AM (12h cache)."""
    return get_cached(colegio_id, "casino", max_age_hours=12)


def set_casino(colegio_id: str, data):
    set_cached(colegio_id, "casino", data)


def get_casino_hoy(colegio_id: str):
    """Casino menú de hoy — 1x/día AM (12h cache)."""
    return get_cached(colegio_id, "casino_hoy", max_age_hours=12)


def set_casino_hoy(colegio_id: str, data):
    set_cached(colegio_id, "casino_hoy", data)


def get_scinfo(colegio_id: str):
    """SC Info — 1x/semana (7 días cache)."""
    return get_cached(colegio_id, "scinfo", max_age_hours=168)


def set_scinfo(colegio_id: str, data):
    set_cached(colegio_id, "scinfo", data)


def get_noticias(colegio_id: str):
    """Noticias web — 1x/día (12h cache)."""
    return get_cached(colegio_id, "noticias", max_age_hours=12)


def set_noticias(colegio_id: str, data):
    set_cached(colegio_id, "noticias", data)


def get_companeros(colegio_id: str, curso: str):
    """Compañeros por curso — 1x/mes (720h cache)."""
    return get_cached(colegio_id, f"companeros_{curso}", max_age_hours=720)


def set_companeros(colegio_id: str, curso: str, data):
    set_cached(colegio_id, f"companeros_{curso}", data)
