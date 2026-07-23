"""
Procesador de PDFs recibidos por WhatsApp.
Lee los PDFs descargados por wa_handler (en data/attachments/) y extrae su contenido
para incluirlo en el bot_context y el RAG.

Los PDFs del colegio suelen ser:
- Circulares / comunicados
- Calendario de pruebas
- Horarios
- Informes de notas
- Autorizaciones
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

from src.utils.pdf_reader import read_pdf_from_file

CHILE_TZ = ZoneInfo("America/Santiago")
ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "attachments")
PROCESSED_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "wa_pdfs_processed.json")


def _load_processed() -> Dict:
    """Carga registro de PDFs ya procesados."""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_processed(processed: Dict):
    """Guarda registro de PDFs procesados."""
    os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)


def process_wa_pdfs(user_id: str, max_pdfs: int = 10, max_chars_per_pdf: int = 4000) -> List[Dict]:
    """
    Procesa PDFs descargados de WhatsApp para un usuario.
    
    Args:
        user_id: ID del usuario
        max_pdfs: Máximo de PDFs a procesar por ciclo
        max_chars_per_pdf: Máximo de caracteres a extraer por PDF
        
    Returns:
        Lista de dicts con: filename, contenido, fecha_recibido, grupo
    """
    if not os.path.exists(ATTACHMENTS_DIR):
        return []

    processed = _load_processed()
    user_processed = processed.get(user_id, {})
    results = []

    # Buscar PDFs del usuario (formato: {userId}_{grupo}_{timestamp}_{filename}.pdf)
    pattern = re.compile(rf"^{re.escape(user_id)}_(.+?)_(\d+)_(.+\.pdf)$", re.IGNORECASE)

    pdf_files = []
    for fname in os.listdir(ATTACHMENTS_DIR):
        match = pattern.match(fname)
        if match:
            pdf_files.append({
                "path": os.path.join(ATTACHMENTS_DIR, fname),
                "filename": fname,
                "grupo": match.group(1),
                "timestamp": match.group(2),
                "original_name": match.group(3),
            })

    # Ordenar por timestamp descendente (más recientes primero)
    pdf_files.sort(key=lambda x: x["timestamp"], reverse=True)

    for pdf_info in pdf_files[:max_pdfs]:
        fname = pdf_info["filename"]

        # Saltar si ya fue procesado
        if fname in user_processed:
            # Agregar al resultado igual (para incluir en bot_context)
            results.append(user_processed[fname])
            continue

        # Extraer texto del PDF
        text = read_pdf_from_file(pdf_info["path"], max_chars=max_chars_per_pdf)
        if not text:
            continue

        # Formatear timestamp
        try:
            ts = int(pdf_info["timestamp"])
            fecha = datetime.fromtimestamp(ts, tz=CHILE_TZ).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            fecha = datetime.now(CHILE_TZ).strftime("%Y-%m-%d")

        entry = {
            "filename": pdf_info["original_name"],
            "contenido": text,
            "fecha_recibido": fecha,
            "grupo": pdf_info["grupo"],
        }

        results.append(entry)
        user_processed[fname] = entry

    # Guardar registro actualizado
    processed[user_id] = user_processed
    _save_processed(processed)

    return results


def get_pdf_summary_for_context(user_id: str, max_total_chars: int = 8000) -> List[Dict]:
    """
    Obtiene resúmenes de PDFs de WA para incluir en bot_context.
    Limita el contenido total para no saturar el contexto.
    
    Args:
        user_id: ID del usuario
        max_total_chars: Máximo total de caracteres sumados
        
    Returns:
        Lista de dicts con: filename, contenido (truncado), fecha_recibido, grupo
    """
    pdfs = process_wa_pdfs(user_id)
    if not pdfs:
        return []

    # Limitar contenido total
    total_chars = 0
    result = []
    for pdf in pdfs:
        remaining = max_total_chars - total_chars
        if remaining <= 200:
            break
        entry = {
            "filename": pdf["filename"],
            "contenido": pdf["contenido"][:remaining],
            "fecha_recibido": pdf["fecha_recibido"],
            "grupo": pdf["grupo"],
        }
        total_chars += len(entry["contenido"])
        result.append(entry)

    return result
