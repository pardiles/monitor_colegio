"""
Storage por usuario.

Estructura:
  data/{user_id}/
  ├── bot_context.json       ← snapshot completo para el bot
  ├── calendario.json        ← eventos persistentes
  ├── instrucciones.json     ← inputs manuales del apoderado
  ├── whatsapp_messages.json ← mensajes de sus grupos
  ├── meta.json              ← timestamps última actualización por fuente
  └── history/               ← historial semanal (futuro)

Compatibilidad: lee de la nueva estructura primero, fallback a la vieja.
La migración es progresiva — cada corrida escribe en la nueva ubicación.
"""

import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")
DATA_DIR = "data"


def _user_dir(user_id: str) -> str:
    """Obtener/crear directorio de un usuario."""
    d = os.path.join(DATA_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def save_bot_context(user_id: str, context: dict):
    """Guardar bot_context en la carpeta del usuario.
    También mantiene el archivo legacy para compatibilidad con wa_handler.
    """
    user_dir = _user_dir(user_id)
    # Nueva ubicación
    with open(os.path.join(user_dir, "bot_context.json"), "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False)
    # Legacy (wa_handler.js todavía lee de data/bot_context_{user_id}.json)
    legacy_path = os.path.join(DATA_DIR, f"bot_context_{user_id}.json")
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False)


def load_bot_context(user_id: str) -> dict:
    """Cargar bot_context. Intenta nueva ubicación primero."""
    new_path = os.path.join(_user_dir(user_id), "bot_context.json")
    if os.path.exists(new_path):
        with open(new_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback legacy
    legacy_path = os.path.join(DATA_DIR, f"bot_context_{user_id}.json")
    if os.path.exists(legacy_path):
        with open(legacy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_calendario(user_id: str, eventos: list):
    """Guardar calendario persistente del usuario."""
    user_dir = _user_dir(user_id)
    with open(os.path.join(user_dir, "calendario.json"), "w", encoding="utf-8") as f:
        json.dump(eventos, f, indent=2, ensure_ascii=False)
    # Legacy
    legacy_path = os.path.join(DATA_DIR, f"calendario_{user_id}.json")
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(eventos, f, indent=2, ensure_ascii=False)


def load_calendario(user_id: str) -> list:
    """Cargar calendario persistente."""
    new_path = os.path.join(_user_dir(user_id), "calendario.json")
    if os.path.exists(new_path):
        with open(new_path, "r", encoding="utf-8") as f:
            return json.load(f)
    legacy_path = os.path.join(DATA_DIR, f"calendario_{user_id}.json")
    if os.path.exists(legacy_path):
        with open(legacy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_instrucciones(user_id: str, instrucciones: list):
    """Guardar instrucciones de los padres."""
    user_dir = _user_dir(user_id)
    with open(os.path.join(user_dir, "instrucciones.json"), "w", encoding="utf-8") as f:
        json.dump(instrucciones, f, indent=2, ensure_ascii=False)


def load_instrucciones(user_id: str) -> list:
    """Cargar instrucciones. Intenta varias ubicaciones."""
    new_path = os.path.join(_user_dir(user_id), "instrucciones.json")
    if os.path.exists(new_path):
        with open(new_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Legacy: monitor_inputs_{user_id}.json
    legacy_path = os.path.join(DATA_DIR, f"monitor_inputs_{user_id}.json")
    if os.path.exists(legacy_path):
        with open(legacy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Legacy compartido: monitor_inputs.json
    shared_path = os.path.join(DATA_DIR, "monitor_inputs.json")
    if os.path.exists(shared_path):
        with open(shared_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def update_meta(user_id: str, source: str):
    """Marcar que una fuente fue actualizada para este usuario."""
    user_dir = _user_dir(user_id)
    meta_path = os.path.join(user_dir, "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass
    meta[source] = datetime.now(CHILE_TZ).isoformat()
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def get_last_update(user_id: str, source: str) -> str:
    """Obtener timestamp de última actualización de una fuente."""
    meta_path = os.path.join(_user_dir(user_id), "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get(source, "")
        except Exception:
            pass
    return ""
