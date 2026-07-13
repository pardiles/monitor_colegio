"""
Fuente: Calendario de evaluaciones del colegio.
API JSON pública - no requiere login.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict


CALENDAR_URL = "https://colegiodelsagradocorazon.cl/evaluation/calendar.json"


def fetch_evaluaciones(
    categorias: List[str] = ["5", "1"],
    dias_adelante: int = 14,
) -> List[Dict]:
    """
    Obtiene evaluaciones y eventos del calendario del colegio.
    
    Args:
        categorias: Lista de cursos a consultar (ej: ["5", "1"])
        dias_adelante: Cuántos días hacia adelante consultar
    
    Returns:
        Lista de eventos con estructura:
        {
            "id": int,
            "title": str,
            "description": str,
            "start": "YYYY-MM-DD",
            "end": "YYYY-MM-DD",
            "start_date": str,
            "allDay": bool,
            "category": str,
            "color": str,
            "url": str
        }
    """
    today = datetime.now()
    start = today - timedelta(days=1)
    end = today + timedelta(days=dias_adelante)

    params = {
        "category[]": categorias,
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
    }

    response = requests.get(CALENDAR_URL, params=params, timeout=15)
    response.raise_for_status()

    eventos = response.json()
    return eventos
