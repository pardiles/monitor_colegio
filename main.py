"""
Monitor Colegio - Script principal.
Orquesta la ingesta de datos y generación de resumen.

Uso:
    python main.py morning   # Briefing matutino
    python main.py evening   # Resumen nocturno
    python main.py ingest    # Solo ingesta (sin enviar)
    python main.py test      # Genera resumen pero no envía
"""

import os
import sys
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

CHILE_TZ = ZoneInfo("America/Santiago")

from src.sources.calendario import fetch_evaluaciones
from src.sources.schoolnet import SchoolNetClient
from src.sources.gmail_source import GmailClient
from src.sources.noticias_web import fetch_noticias
from src.sources.extracurriculares import fetch_extracurriculares
from src.sources.scinfo import fetch_scinfo_latest
from src.processor.summarizer import Summarizer
from src.calendar_store import update_calendar_from_sources, get_upcoming_events
# from src.messenger.whatsapp import WhatsAppSender  # Replaced by Baileys


def _load_horarios():
    """Cargar horarios desde archivo JSON local."""
    horarios_file = os.path.join("data", "horarios.json")
    if os.path.exists(horarios_file):
        with open(horarios_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_whatsapp():
    """Cargar mensajes de WhatsApp desde archivo JSON."""
    wa_file = os.path.join("data", "whatsapp_messages.json")
    monitor_file = os.path.join("data", "monitor_inputs.json")
    result = {"whatsapp_5A_franco": [], "whatsapp_1C_blanca": [], "whatsapp_sharks_franco": [], "instrucciones_padres": []}
    
    if os.path.exists(wa_file):
        with open(wa_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            result["whatsapp_5A_franco"] = data.get("5A_franco", [])
            result["whatsapp_1C_blanca"] = data.get("1C_blanca", [])
            result["whatsapp_sharks_franco"] = data.get("5to_sharks_franco", [])
    
    if os.path.exists(monitor_file):
        with open(monitor_file, "r", encoding="utf-8") as f:
            result["instrucciones_padres"] = json.load(f)
    
    return result


def ingest_all() -> dict:
    """Recopila datos de todas las fuentes."""
    data = {}
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"INGESTA - {today}")
    print(f"{'='*50}")

    # Determinar si es primera ejecución o diaria
    state_file = os.path.join("data", ".last_run")
    if os.path.exists(state_file):
        days_back = 1  # Producción: solo ayer
    else:
        days_back = 7  # Primera vez: última semana
    print(f"   Modo: {'primera vez (7 días)' if days_back == 7 else 'diario (1 día)'}")

    # 1. Calendario evaluaciones (siempre 14 días adelante)
    print("\n📅 Calendario evaluaciones...")
    try:
        categorias = [
            os.getenv("CHILD_1_CATEGORY", "5"),
            os.getenv("CHILD_2_CATEGORY", "1"),
        ]
        data["calendario"] = fetch_evaluaciones(categorias)
        print(f"   ✅ {len(data['calendario'])} eventos")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        data["calendario"] = []

    # 2. SchoolNet
    print("\n🏫 SchoolNet...")
    try:
        sn = SchoolNetClient(
            os.getenv("SCHOOLNET_USERNAME"),
            os.getenv("SCHOOLNET_PASSWORD"),
        )
        if sn.login():
            print("   ✅ Login OK")
            data["comunicaciones"] = sn.get_comunicaciones()
            print(f"   ✅ Comunicaciones: {len(data['comunicaciones'].get('comunicaciones', []))}")
            
            data["calificaciones_franco"] = sn.get_calificaciones(0)
            data["calificaciones_blanca"] = sn.get_calificaciones(1)
            print("   ✅ Calificaciones")

            data["asistencia"] = sn.get_asistencia(0)
            print("   ✅ Asistencia")

            data["pagos"] = sn.get_pagos()
            print(f"   ✅ Pagos: {len(data['pagos'].get('fechas', []))}")

            # Compañeros (para cumpleaños)
            data["companeros_franco"] = sn.get_companeros(0)
            data["companeros_blanca"] = sn.get_companeros(1)
            print("   ✅ Compañeros (cumpleaños)")

            # Extracurriculares
            try:
                sso_url = sn.get_extracurriculares_url()
                if sso_url:
                    data["extracurriculares"] = [
                        vars(e) for e in fetch_extracurriculares(sso_url)
                    ]
                    print(f"   ✅ Extracurriculares: {len(data['extracurriculares'])}")
            except Exception as e:
                print(f"   ⚠️ Extracurriculares: {e}")
        else:
            print("   ❌ Login falló")
    except Exception as e:
        print(f"   ❌ Error SchoolNet: {e}")

    # 3. Gmail
    print("\n📧 Gmail...")
    try:
        gmail = GmailClient(
            os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json"),
            os.getenv("GMAIL_TOKEN_FILE", "token.json"),
        )
        gmail.authenticate()
        # Emails siempre 7 días (los avisos llegan con anticipación)
        data["emails"] = gmail.get_school_emails(days=7)
        print(f"   ✅ {len(data['emails'])} correos")
    except Exception as e:
        print(f"   ❌ Error Gmail: {e}")
        data["emails"] = []

    # 4. Noticias web
    print("\n📰 Noticias web...")
    try:
        data["noticias"] = fetch_noticias(max_noticias=5)
        print(f"   ✅ {len(data['noticias'])} noticias")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        data["noticias"] = []

    # 5. SC Info (newsletter semanal)
    print("\n📋 SC Info...")
    try:
        data["scinfo"] = fetch_scinfo_latest()
        if data["scinfo"]["contenido"]:
            print(f"   ✅ SC Info {data['scinfo']['fecha']} ({len(data['scinfo']['contenido'])} chars)")
        else:
            print("   ⚠️ Sin contenido")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        data["scinfo"] = {}

    # 6. Actualizar calendario persistente con datos de todas las fuentes
    print("\n📅 Calendario persistente...")
    try:
        new_events = update_calendar_from_sources(data)
        upcoming = get_upcoming_events(days=14)
        data["calendario_persistente"] = upcoming
        print(f"   ✅ {new_events} eventos nuevos, {len(upcoming)} próximos 14 días")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        data["calendario_persistente"] = []

    return data


def generate_and_send(mode: str, data: dict, is_weekly: bool = False):
    """Genera resumen con Claude y envía por WhatsApp."""
    
    print(f"\n{'='*50}")
    print(f"RESUMEN ({mode}{' - SEMANAL' if is_weekly else ''})")
    print(f"{'='*50}")

    # Generar resumen
    print("\n🤖 Generando resumen con Claude...")
    summarizer = Summarizer(os.getenv("ANTHROPIC_API_KEY"))
    
    if mode == "morning":
        message = summarizer.generate_morning_briefing(data, is_weekly=is_weekly)
    else:
        message = summarizer.generate_evening_summary(data, is_weekly=is_weekly)

    print(f"\n{'─'*50}")
    print(message)
    print(f"{'─'*50}")
    print(f"\n📏 Largo: {len(message)} chars")

    # Guardar mensaje para envío por WhatsApp
    os.makedirs("data", exist_ok=True)
    msg_file = os.path.join("data", "mensaje_enviar.json")
    with open(msg_file, "w", encoding="utf-8") as f:
        json.dump({"mensaje": message, "mode": mode}, f, ensure_ascii=False)

    # Enviar por WhatsApp via Node.js
    print("\n📱 Enviando por WhatsApp...")
    import subprocess
    result = subprocess.run(
        ["node", "send_whatsapp.js"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"   ⚠️ Error: {result.stderr}")

    return message


def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py [morning|evening|ingest|test]")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "ingest":
        data = ingest_all()
        # Guardar en archivo local
        output_file = f"data/ingesta_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        os.makedirs("data", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Datos guardados en {output_file}")

    elif mode in ("morning", "evening"):
        data = ingest_all()
        # Agregar horarios y WhatsApp
        data["horarios"] = _load_horarios()
        data.update(_load_whatsapp())
        
        # Determinar si es resumen semanal (domingo PM)
        today = datetime.now(CHILE_TZ)
        is_weekly = (today.weekday() == 6 and mode == "evening")  # Domingo PM
        
        if is_weekly:
            # Domingo PM: resumen completo de la semana que viene
            print("\n📅 RESUMEN SEMANAL (domingo PM)")
            generate_and_send(mode, data, is_weekly=True)
        else:
            # Otros días: solo enviar si hay algo relevante para HOY/MAÑANA
            generate_and_send(mode, data, is_weekly=False)

    elif mode == "test":
        data = ingest_all()
        # Agregar horarios manuales
        data["horarios"] = _load_horarios()
        # Agregar WhatsApp si existe
        data.update(_load_whatsapp())
        # Solo genera, no envía
        summarizer = Summarizer(os.getenv("ANTHROPIC_API_KEY"))
        
        if len(sys.argv) > 2 and sys.argv[2] == "evening":
            message = summarizer.generate_evening_summary(data)
        else:
            message = summarizer.generate_morning_briefing(data)
        print(f"\n{'─'*50}")
        print(message)
        print(f"{'─'*50}")

    else:
        print(f"Modo '{mode}' no reconocido. Usa: morning, evening, ingest, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
