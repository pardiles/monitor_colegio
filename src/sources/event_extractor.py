"""
Extractor de eventos y datos generales desde mensajes de WhatsApp y emails.
Usa AI (Claude Haiku) para detectar información relevante que no viene de fuentes formales.

Busca:
- Cumpleaños de compañeros mencionados en grupos
- Paseos, salidas grupales, juntas fuera del colegio
- Partidos y eventos deportivos
- Cambios de horario informales
- Actividades sociales (rifas, colectas, regalos profesores)
- Transporte (furgón, cambios de ruta)
- Cualquier dato con FECHA que un apoderado consideraría útil

Los eventos extraídos se agregan al calendario persistente.
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")


def extract_events_from_messages(messages: List[Dict], hijo: str = "", 
                                  api_key: str = "", max_messages: int = 50) -> List[Dict]:
    """
    Extrae eventos y datos relevantes de mensajes de WhatsApp usando AI.
    
    Args:
        messages: Lista de mensajes [{from, body, date, time}, ...]
        hijo: Nombre del hijo (para contexto)
        api_key: Anthropic API key
        max_messages: Máximo de mensajes a procesar
        
    Returns:
        Lista de eventos extraídos [{fecha, hora, descripcion, tipo, hijo, fuente}, ...]
    """
    if not messages or not api_key:
        return []

    # Filtrar mensajes recientes y con contenido relevante (>10 chars)
    recent = [m for m in messages[-max_messages:] if len(m.get("body", "")) > 10]
    if not recent:
        return []

    # Construir texto de mensajes para el prompt
    msgs_text = "\n".join([
        f"[{m.get('date', '')} {m.get('time', '')}] {m.get('from', '')}: {m.get('body', '')[:200]}"
        for m in recent
    ])

    today = datetime.now(CHILE_TZ).strftime("%Y-%m-%d")
    
    prompt = f"""Analiza estos mensajes de un grupo de WhatsApp de apoderados de colegio.
Extrae SOLO información que tenga una FECHA (explícita o implícita) y sea relevante para un apoderado.

Busca:
- Cumpleaños (ej: "el cumple de Juanito es el sábado")
- Paseos/salidas (ej: "paseo al parque viernes 15:00")
- Partidos deportivos (ej: "partido el sábado a las 10")
- Juntas de apoderados informales (ej: "asado el 25 en mi casa")
- Cambios de horario (ej: "mañana salen a las 13:00")
- Colectas/regalos (ej: "juntamos plata para la profe, plazo viernes")
- Furgón/transporte (ej: "el furgón no pasa mañana")
- Cualquier evento con fecha que un papá/mamá debería saber

Fecha de hoy: {today}
Hijo relevante: {hijo or 'no especificado'}

Mensajes:
{msgs_text[:4000]}

Responde SOLO en formato JSON array. Si no hay eventos, responde [].
Cada evento: {{"fecha": "YYYY-MM-DD", "hora": "HH:MM o null", "descripcion": "texto corto", "tipo": "cumpleaños|paseo|partido|junta|horario|colecta|transporte|otro", "confianza": "alta|media|baja"}}

JSON:"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        
        # Parsear JSON (puede venir con ```json wrapper)
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        events = json.loads(text)
        if not isinstance(events, list):
            return []
            
        # Agregar metadata
        for ev in events:
            ev["hijo"] = hijo
            ev["fuente"] = "whatsapp_grupo"
            ev["extraido_el"] = today
            
        return [e for e in events if e.get("fecha") and e.get("confianza") != "baja"]
        
    except Exception as e:
        print(f"   ⚠️ Event extractor error: {e}")
        return []


def extract_events_from_emails(emails: List[Dict], api_key: str = "") -> List[Dict]:
    """
    Extrae eventos y datos relevantes de emails del colegio usando AI.
    
    Args:
        emails: Lista de emails [{de, asunto, body/resumen, fecha}, ...]
        api_key: Anthropic API key
        
    Returns:
        Lista de eventos extraídos
    """
    if not emails or not api_key:
        return []

    # Construir texto de emails
    emails_text = "\n---\n".join([
        f"De: {e.get('de', '')}\nAsunto: {e.get('asunto', '')}\nFecha: {e.get('fecha', '')}\nContenido: {(e.get('body', '') or e.get('resumen', ''))[:300]}"
        for e in emails[:10]
    ])

    today = datetime.now(CHILE_TZ).strftime("%Y-%m-%d")

    prompt = f"""Analiza estos emails de un colegio y extrae TODOS los eventos/fechas relevantes para un apoderado.

Busca:
- Reuniones de apoderados (fecha, hora, lugar)
- Evaluaciones/pruebas (fecha, asignatura)
- Salidas anticipadas o cambios de horario
- Eventos del colegio (ferias, actos, celebraciones)
- Plazos de entrega (autorizaciones, documentos)
- Pagos/cobranzas con fecha de vencimiento
- Actividades especiales (día del alumno, jornadas, retiros)

Fecha de hoy: {today}

Emails:
{emails_text[:4000]}

Responde SOLO en formato JSON array. Si no hay eventos, responde [].
Cada evento: {{"fecha": "YYYY-MM-DD", "hora": "HH:MM o null", "descripcion": "texto corto", "tipo": "reunion|evaluacion|horario|evento|plazo|pago|actividad|otro", "lugar": "si se menciona o null"}}

JSON:"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        events = json.loads(text)
        if not isinstance(events, list):
            return []
            
        for ev in events:
            ev["fuente"] = "email"
            ev["extraido_el"] = today
            
        return events
        
    except Exception as e:
        print(f"   ⚠️ Email event extractor error: {e}")
        return []


def process_and_store_events(wa_messages: Dict[str, List], emails: List[Dict],
                              hijos: List[Dict], api_key: str, user_id: str):
    """
    Procesa mensajes WA + emails, extrae eventos, y los guarda en el calendario persistente.
    
    Args:
        wa_messages: Dict {grupo_label: [messages]}
        emails: Lista de emails
        hijos: Lista de hijos del usuario [{nombre, curso}, ...]
        api_key: Anthropic API key
        user_id: ID del usuario
    """
    from src.calendar_store import add_events_to_calendar
    
    all_events = []
    
    # Extraer de cada grupo WA
    for grupo, msgs in wa_messages.items():
        if not msgs:
            continue
        # Determinar a qué hijo corresponde el grupo
        hijo = ""
        for h in hijos:
            nombre_lower = h.get("nombre", "").lower()
            if nombre_lower in grupo.lower():
                hijo = h["nombre"]
                break
        
        events = extract_events_from_messages(msgs, hijo=hijo, api_key=api_key)
        if events:
            for e in events:
                e["fuente_detalle"] = f"WA grupo {grupo}"
            all_events.extend(events)
            print(f"   📅 {len(events)} eventos extraídos de WA grupo '{grupo}'")
    
    # Extraer de emails
    if emails:
        email_events = extract_events_from_emails(emails, api_key=api_key)
        if email_events:
            all_events.extend(email_events)
            print(f"   📅 {len(email_events)} eventos extraídos de emails")
    
    # Guardar en calendario persistente
    if all_events:
        try:
            added = add_events_to_calendar(all_events, user_id=user_id)
            print(f"   ✅ {added} eventos nuevos agregados al calendario")
        except Exception as e:
            print(f"   ⚠️ Error guardando eventos: {e}")
            # Fallback: guardar en archivo JSON
            events_file = os.path.join("data", f"extracted_events_{user_id}.json")
            existing = []
            if os.path.exists(events_file):
                with open(events_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.extend(all_events)
            # Dedup por fecha+descripcion
            seen = set()
            deduped = []
            for ev in existing:
                key = f"{ev.get('fecha', '')}-{ev.get('descripcion', '')[:30]}"
                if key not in seen:
                    seen.add(key)
                    deduped.append(ev)
            with open(events_file, "w", encoding="utf-8") as f:
                json.dump(deduped[-100:], f, indent=2, ensure_ascii=False)
    
    return all_events
