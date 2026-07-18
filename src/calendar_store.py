"""
Calendario persistente: acumula eventos con fecha futura.
Los eventos se detectan de cualquier fuente y se guardan hasta que su fecha pasa.
"""

import json
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional

CHILE_TZ = ZoneInfo("America/Santiago")
CALENDAR_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "eventos.json")


def load_calendar() -> List[Dict]:
    """Carga el calendario persistente."""
    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_calendar(eventos: List[Dict]):
    """Guarda el calendario persistente."""
    os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(eventos, f, indent=2, ensure_ascii=False)


def add_event(
    fecha: str,
    descripcion: str,
    tipo: str = "evento",
    hijo: str = "ambos",
    fuente: str = "manual",
    hora: Optional[str] = None,
    lugar: Optional[str] = None,
) -> bool:
    """
    Agrega un evento al calendario si no existe ya uno similar.
    
    Args:
        fecha: "YYYY-MM-DD"
        descripcion: texto del evento
        tipo: evaluacion, reunion, sin_clases, evento, entrega, extraprogramatica
        hijo: "franco", "blanca", "ambos"
        fuente: "scinfo", "email", "whatsapp", "calendario_web", "manual"
        hora: "HH:MM" opcional
        lugar: texto opcional
    
    Returns:
        True si se agregó (nuevo), False si ya existía
    """
    calendario = load_calendar()
    
    # Verificar si ya existe un evento similar (misma fecha + descripción similar)
    for ev in calendario:
        if ev["fecha"] == fecha and _similar(ev["descripcion"], descripcion):
            return False
    
    evento = {
        "fecha": fecha,
        "descripcion": descripcion,
        "tipo": tipo,
        "hijo": hijo,
        "fuente": fuente,
        "detectado": datetime.now(CHILE_TZ).strftime("%Y-%m-%d"),
    }
    if hora:
        evento["hora"] = hora
    if lugar:
        evento["lugar"] = lugar
    
    calendario.append(evento)
    save_calendar(calendario)
    return True


def get_upcoming_events(days: int = 14) -> List[Dict]:
    """Obtiene eventos de los próximos N días."""
    calendario = load_calendar()
    today = datetime.now(CHILE_TZ).date()
    cutoff = today + timedelta(days=days)
    
    upcoming = []
    for ev in calendario:
        try:
            ev_date = datetime.strptime(ev["fecha"], "%Y-%m-%d").date()
            if today <= ev_date <= cutoff:
                upcoming.append(ev)
        except (ValueError, KeyError):
            continue
    
    return sorted(upcoming, key=lambda x: x["fecha"])


def cleanup_past_events():
    """Elimina eventos cuya fecha ya pasó (más de 1 día)."""
    calendario = load_calendar()
    yesterday = (datetime.now(CHILE_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    filtered = [ev for ev in calendario if ev["fecha"] >= yesterday]
    if len(filtered) < len(calendario):
        save_calendar(filtered)


def extract_events_from_scinfo(scinfo_content: str) -> List[Dict]:
    """Extrae eventos con fecha del contenido del SC Info."""
    events = []
    
    # Patrones de fecha comunes en SC Info
    # "13 al 15 de julio", "17 de julio", "22 de julio", etc.
    date_patterns = [
        # "DD de MES" 
        r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        # "DD/MM/YYYY"
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
    ]
    
    months = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    year = datetime.now(CHILE_TZ).year
    lines = scinfo_content.split('\n')
    
    for i, line in enumerate(lines):
        # Buscar fechas con contexto
        for match in re.finditer(r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)', line, re.IGNORECASE):
            day = int(match.group(1))
            month = months.get(match.group(2).lower(), 0)
            if month and 1 <= day <= 31:
                fecha = f"{year}-{month:02d}-{day:02d}"
                # Contexto: la línea completa + siguiente
                context = line.strip()
                if i + 1 < len(lines):
                    context += " " + lines[i + 1].strip()
                
                # Determinar tipo
                tipo = "evento"
                if any(kw in context.lower() for kw in ['sin clases', 'no disponible', 'feriado', 'interferiado']):
                    tipo = "sin_clases"
                elif any(kw in context.lower() for kw in ['entrevista', 'reunión', 'reunion']):
                    tipo = "reunion"
                elif any(kw in context.lower() for kw in ['prueba', 'evaluación', 'evaluacion', 'control']):
                    tipo = "evaluacion"
                
                events.append({
                    "fecha": fecha,
                    "descripcion": context[:150],
                    "tipo": tipo,
                    "hijo": "ambos",
                    "fuente": "scinfo",
                })
    
    return events


def extract_events_from_emails(emails: List[Dict]) -> List[Dict]:
    """Extrae eventos con fecha de los emails usando Claude para parsear."""
    events = []
    year = datetime.now(CHILE_TZ).year
    
    # Primero intento con Claude (más preciso)
    try:
        events = _extract_events_with_ai(emails)
        if events:
            return events
    except Exception as e:
        print(f"   ⚠️ AI extraction failed: {e}, falling back to regex")
    
    # Fallback: regex básico
    months = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    for email in emails:
        text = email.get("body", "") + " " + email.get("asunto", "")
        
        for match in re.finditer(r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)', text, re.IGNORECASE):
            day = int(match.group(1))
            month = months.get(match.group(2).lower(), 0)
            if month and 1 <= day <= 31:
                fecha = f"{year}-{month:02d}-{day:02d}"
                if fecha >= datetime.now(CHILE_TZ).strftime("%Y-%m-%d"):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].strip()
                    
                    hijo = "ambos"
                    if "franco" in email.get("asunto", "").lower() or "5°" in text[start:end]:
                        hijo = "franco"
                    elif "blanca" in email.get("asunto", "").lower() or "1°" in text[start:end]:
                        hijo = "blanca"
                    
                    events.append({
                        "fecha": fecha,
                        "descripcion": context[:150],
                        "tipo": "evento",
                        "hijo": hijo,
                        "fuente": "email",
                    })
    
    return events


def _extract_events_with_ai(emails: List[Dict]) -> List[Dict]:
    """Usa Claude para extraer eventos futuros de los emails."""
    import anthropic
    
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []
    
    # Preparar texto de emails (solo los que parecen tener eventos)
    relevant_emails = []
    event_keywords = ['entrevista', 'reunión', 'reunion', 'prueba', 'evaluación',
                      'salida', 'actividad', 'feriado', 'sin clases', 'jornada',
                      'taller', 'citación', 'presentación', 'plazo', 'fecha']
    
    for email in emails:
        text = (email.get("asunto", "") + " " + email.get("body", "")[:500]).lower()
        if any(kw in text for kw in event_keywords):
            relevant_emails.append(email)
    
    if not relevant_emails:
        return []
    
    # Armar prompt
    emails_text = ""
    for e in relevant_emails[:10]:
        emails_text += f"\n---\nAsunto: {e.get('asunto', '')}\nFecha email: {e.get('fecha', '')}\nContenido: {e.get('body', '')[:600]}\n"
    
    today = datetime.now(CHILE_TZ).strftime("%Y-%m-%d")
    
    prompt = f"""Analiza estos emails del colegio y extrae TODOS los eventos futuros (fecha >= {today}).
Para cada evento devuelve un JSON con: fecha (YYYY-MM-DD), descripcion (corta), hora (HH:MM o null), lugar (o null), hijo (franco/blanca/ambos), tipo (reunion/evaluacion/sin_clases/evento/entrega).

Emails:
{emails_text}

Responde SOLO con un array JSON. Si no hay eventos futuros, responde [].
Ejemplo: [{{"fecha":"2026-07-22","descripcion":"Entrevista apoderados Franco 5°A","hora":"10:30","lugar":"Oficina Miss Valentina","hijo":"franco","tipo":"reunion"}}]"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    
    result_text = response.content[0].text.strip()
    
    # Extraer JSON del response
    json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
    if json_match:
        events_raw = json.loads(json_match.group())
        events = []
        for ev in events_raw:
            events.append({
                "fecha": ev.get("fecha", ""),
                "descripcion": ev.get("descripcion", "")[:150],
                "tipo": ev.get("tipo", "evento"),
                "hijo": ev.get("hijo", "ambos"),
                "fuente": "email",
                "hora": ev.get("hora"),
                "lugar": ev.get("lugar"),
            })
        return events
    
    return []


def update_calendar_from_sources(data: Dict) -> int:
    """
    Actualiza el calendario persistente con datos de todas las fuentes.
    Usa Claude para analizar TODAS las fuentes y extraer eventos futuros.
    Returns: número de eventos nuevos agregados.
    """
    new_count = 0
    
    # Recopilar todo el texto de todas las fuentes
    all_texts = []
    
    # Emails
    if "emails" in data and data["emails"]:
        for e in data["emails"]:
            all_texts.append({
                "fuente": "email",
                "asunto": e.get("asunto", ""),
                "contenido": e.get("body", "")[:600],
            })
    
    # SC Info
    if "scinfo" in data and data["scinfo"].get("contenido"):
        all_texts.append({
            "fuente": "scinfo",
            "asunto": "SC Info " + data["scinfo"].get("fecha", ""),
            "contenido": data["scinfo"]["contenido"][:2000],
        })
    
    # Comunicaciones SchoolNet
    if "comunicaciones" in data:
        coms = data["comunicaciones"].get("comunicaciones", [])
        for c in coms[:5]:
            all_texts.append({
                "fuente": "schoolnet",
                "asunto": c.get("asunto", ""),
                "contenido": c.get("asunto", ""),
            })
    
    # Cuaderno Rojo
    if "cuadernorojo_comunicados" in data:
        for c in data["cuadernorojo_comunicados"][:5]:
            all_texts.append({
                "fuente": "cuadernorojo",
                "asunto": c.get("asunto", ""),
                "contenido": c.get("contenido", "")[:400],
            })
    
    # WhatsApp grupos
    for key, value in data.items():
        if key.startswith("whatsapp_") and isinstance(value, list):
            # Tomar últimos mensajes relevantes
            for msg in value[-20:]:
                body = msg.get("body", "")
                if len(body) > 20:  # Solo mensajes con contenido
                    all_texts.append({
                        "fuente": f"whatsapp ({key})",
                        "asunto": f"Mensaje de {msg.get('from', '')}",
                        "contenido": body[:300],
                    })
    
    # Extraer eventos con Claude de todas las fuentes
    if all_texts:
        try:
            events = _extract_events_with_ai_all(all_texts)
            for ev in events:
                if add_event(**ev):
                    new_count += 1
                    print(f"   📅 Nuevo evento: {ev['fecha']} - {ev['descripcion'][:50]}")
        except Exception as e:
            print(f"   ⚠️ Error extrayendo eventos con AI: {e}")
            # Fallback: regex en emails
            if "emails" in data and data["emails"]:
                events = extract_events_from_emails(data["emails"])
                for ev in events:
                    if add_event(**ev):
                        new_count += 1
    
    # Desde calendario web del colegio (API directa, no necesita AI)
    if "calendario" in data:
        for ev in data["calendario"]:
            fecha = ev.get("start", "")[:10]
            desc = ev.get("title", "") + " - " + ev.get("description", "")
            if fecha and desc:
                if add_event(fecha=fecha, descripcion=desc[:150], tipo="evento",
                           hijo="ambos", fuente="calendario_web"):
                    new_count += 1

    # Desde pagos (vencimientos)
    if "pagos" in data and isinstance(data["pagos"], dict):
        fechas_pago = data["pagos"].get("fechas", []) or data["pagos"].get("proximos_vencimientos", [])
        for pago in fechas_pago:
            fecha = pago.get("fecha", "")[:10] if isinstance(pago, dict) else ""
            monto = pago.get("monto", "") if isinstance(pago, dict) else ""
            if fecha and fecha >= datetime.now(CHILE_TZ).strftime("%Y-%m-%d"):
                desc = f"💰 Vencimiento pago colegio - ${monto}" if monto else "💰 Vencimiento pago colegio"
                if add_event(fecha=fecha, descripcion=desc, tipo="evento", hijo="ambos", fuente="schoolnet_pagos"):
                    new_count += 1
    
    # Limpiar eventos pasados
    cleanup_past_events()
    
    return new_count


def _extract_events_with_ai_all(texts: List[Dict]) -> List[Dict]:
    """Usa Claude para extraer eventos futuros de TODAS las fuentes."""
    import anthropic
    
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return []
    
    # Armar texto consolidado
    content = ""
    for t in texts[:30]:  # Max 30 items para no exceder contexto
        content += f"\n[{t['fuente']}] {t['asunto']}\n{t['contenido']}\n---\n"
    
    if not content.strip():
        return []
    
    today = datetime.now(CHILE_TZ).strftime("%Y-%m-%d")
    
    prompt = f"""Analiza estas comunicaciones del colegio y extrae TODOS los eventos futuros (fecha >= {today}).

IMPORTANTE - EXTRAER ESPECIALMENTE:
- Reuniones/entrevistas de apoderados con fecha y hora exacta
- Pruebas y evaluaciones
- Días sin clases
- Plazos de inscripción
- Salidas anticipadas
- Actividades especiales

Comunicaciones:
{content}

Para cada evento devuelve un JSON con:
- fecha: YYYY-MM-DD (año actual es {datetime.now(CHILE_TZ).year}. Si dice "jueves 23 de julio" = {datetime.now(CHILE_TZ).year}-07-23)
- descripcion: texto corto descriptivo (incluir con quién es la reunión si se menciona)
- hora: HH:MM (o null si no se indica). Si dice "11:10 hrs" → "11:10"
- lugar: texto (o null). Ej: "oficina de Miss Isabel"
- hijo: "franco"/"blanca"/"ambos" (si el asunto o body menciona un nombre específico, usar ese)
- tipo: "reunion"/"evaluacion"/"sin_clases"/"evento"/"entrega"/"extraprogramatica"
- fuente: la fuente del texto original (email, scinfo, etc.)

Responde SOLO con un array JSON. Si no hay eventos futuros, responde [].
No incluir eventos cuya fecha ya pasó (< {today})."""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    
    result_text = response.content[0].text.strip()
    
    # Extraer JSON
    json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
    if json_match:
        events_raw = json.loads(json_match.group())
        events = []
        for ev in events_raw:
            if ev.get("fecha"):
                events.append({
                    "fecha": ev["fecha"],
                    "descripcion": ev.get("descripcion", "")[:150],
                    "tipo": ev.get("tipo", "evento"),
                    "hijo": ev.get("hijo", "ambos"),
                    "fuente": "ai_extraction",
                    "hora": ev.get("hora"),
                    "lugar": ev.get("lugar"),
                })
        return events
    
    return []


def _similar(text1: str, text2: str) -> bool:
    """Verifica si dos textos son similares (para evitar duplicados)."""
    # Simplificación: si comparten más del 60% de palabras
    words1 = set(text1.lower().split()[:10])
    words2 = set(text2.lower().split()[:10])
    if not words1 or not words2:
        return False
    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap > 0.6
