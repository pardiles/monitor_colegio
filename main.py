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
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

CHILE_TZ = ZoneInfo("America/Santiago")
DIAS_ES = {0:'Lunes',1:'Martes',2:'Miércoles',3:'Jueves',4:'Viernes',5:'Sábado',6:'Domingo'}

from src.sources.calendario import fetch_evaluaciones
from src.sources.schoolnet import SchoolNetClient
from src.sources.gmail_source import GmailClient
from src.sources.noticias_web import fetch_noticias
from src.sources.extracurriculares import fetch_extracurriculares
from src.sources.scinfo import fetch_scinfo_latest
from src.sources.cuadernorojo import fetch_cuadernorojo
from src.sources.wa_pdf_processor import get_pdf_summary_for_context
from src.sources.oxford import fetch_oxford_all
from src.processor.summarizer import Summarizer
from src.calendar_store import update_calendar_from_sources, get_upcoming_events
from src.shared_cache import (
    _get_colegio_id, get_evaluaciones, set_evaluaciones,
    get_casino, set_casino, get_casino_hoy, set_casino_hoy,
    get_scinfo, set_scinfo, get_noticias, set_noticias,
    get_companeros, set_companeros,
)
from src.user_storage import save_bot_context, load_instrucciones, update_meta
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
    attachments_dir = os.path.join("data", "attachments")
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

    # Leer contenido de PDFs adjuntos de WhatsApp
    if os.path.exists(attachments_dir):
        from src.utils.pdf_reader import read_pdf_from_file
        wa_pdfs = []
        for filename in os.listdir(attachments_dir):
            if filename.lower().endswith(".pdf"):
                filepath = os.path.join(attachments_dir, filename)
                text = read_pdf_from_file(filepath, max_chars=2000)
                if text:
                    # Extraer grupo y timestamp del nombre: label_ts_filename.pdf
                    parts = filename.split("_", 2)
                    grupo = parts[0] if len(parts) > 0 else "desconocido"
                    wa_pdfs.append({
                        "grupo": grupo,
                        "filename": parts[2] if len(parts) > 2 else filename,
                        "contenido": text,
                    })
        if wa_pdfs:
            result["whatsapp_pdfs"] = wa_pdfs
    
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
        days_back = 30  # Primera vez: último mes
    print(f"   Modo: {'primera vez (30 días)' if days_back == 30 else 'diario (1 día)'}")

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
        # Primera vez: 30 días. Después: 3 días
        gmail_days = days_back if days_back > 3 else 3
        data["emails"] = gmail.get_school_emails(days=gmail_days)
        print(f"   ✅ {len(data['emails'])} correos ({gmail_days} días)")
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


def ingest_oscar() -> dict:
    """Recopila datos de las fuentes de Oscar (Oxford School + Acuarela Montessori)."""
    data = {}
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"INGESTA OSCAR - {today}")
    print(f"{'='*50}")

    # Cargar config de Oscar
    oscar_cfg = None
    # Primero intentar archivo individual
    oscar_file = os.path.join("config", "users", "oscar_ardiles.json")
    if os.path.exists(oscar_file):
        with open(oscar_file, "r", encoding="utf-8") as f:
            oscar_cfg = json.load(f)
    # Fallback: legacy users.json
    if not oscar_cfg:
        users_file = os.path.join("config", "users.json")
        if not os.path.exists(users_file):
            print("   ❌ No se encontró config de Oscar")
            return data
        with open(users_file, "r", encoding="utf-8") as f:
            users = json.load(f)
        oscar_cfg = next((u for u in users if u["id"] == "oscar_ardiles"), None)
    if not oscar_cfg:
        print("   ❌ No se encontró config de Oscar")
        return data

    # 1. Oxford School (Esperanza) - RSS + PDFs
    print("\n🏫 Oxford School (Esperanza)...")
    try:
        esperanza = next((h for h in oscar_cfg["hijos"] if h["nombre"] == "Esperanza"), {})
        oxford_data = fetch_oxford_all(curso=esperanza.get("curso", ""))
        data["oxford_noticias"] = oxford_data["noticias"]
        data["oxford_pdfs"] = oxford_data["pdfs"]
    except Exception as e:
        print(f"   ❌ Error Oxford: {e}")
        data["oxford_noticias"] = []

    # 2. Cuaderno Rojo / Acuarela Montessori (Simón)
    print("\n📕 Cuaderno Rojo - Acuarela Montessori (Simón)...")
    try:
        acuarela_cfg = next(
            (c for c in oscar_cfg.get("colegios", []) if "Acuarela" in c["nombre"]),
            None
        )
        if acuarela_cfg and acuarela_cfg.get("plataforma_notas"):
            pn = acuarela_cfg["plataforma_notas"]
            cr_result = fetch_cuadernorojo(pn["user"], pn["pass"], max_comunicados=5)
            if cr_result["login_ok"]:
                data["cuadernorojo_comunicados"] = cr_result["comunicados"]
                print(f"   ✅ {len(cr_result['comunicados'])} comunicados")
            else:
                print("   ❌ Login Cuaderno Rojo falló")
                data["cuadernorojo_comunicados"] = []
        else:
            print("   ⚠️ Sin credenciales Cuaderno Rojo")
    except Exception as e:
        print(f"   ❌ Error Cuaderno Rojo: {e}")
        data["cuadernorojo_comunicados"] = []

    # 3. Gmail de Oscar (ambos colegios)
    print("\n📧 Gmail Oscar...")
    try:
        gmail_cfg = oscar_cfg.get("gmail", {})
        creds_file = gmail_cfg.get("credentials_file", "")
        if creds_file and os.path.exists(creds_file):
            for account in gmail_cfg.get("accounts", []):
                token_file = account.get("token_file", "")
                if token_file and os.path.exists(token_file):
                    gmail = GmailClient(creds_file, token_file)
                    gmail.authenticate()
                    # Filtrar por dominios del colegio
                    from src.sources.gmail_source import SCHOOL_DOMAINS
                    original_domains = SCHOOL_DOMAINS[:]
                    SCHOOL_DOMAINS.clear()
                    SCHOOL_DOMAINS.extend(account.get("school_domains", []))

                    emails = gmail.get_school_emails(days=7)
                    hijo = account.get("hijo", "")
                    key = f"emails_{hijo.lower()}"
                    data[key] = emails
                    print(f"   ✅ {len(emails)} emails ({hijo})")

                    SCHOOL_DOMAINS.clear()
                    SCHOOL_DOMAINS.extend(original_domains)
        else:
            print("   ⚠️ Sin credenciales Gmail")
    except Exception as e:
        print(f"   ❌ Error Gmail: {e}")

    return data


def generate_and_send(mode: str, data: dict, is_weekly: bool = False,
                     user_id: str = "pablo", user_cfg: dict = None, force_send: bool = False):
    """Genera resumen con Claude y envía por WhatsApp."""
    
    # Skip en días sin relevancia (viernes PM, sábado, domingo AM)
    # Solo enviar si hay eventos para hoy/mañana o novedades
    today = datetime.now(CHILE_TZ)
    weekday = today.weekday()  # 0=lun, 4=vie, 5=sab, 6=dom
    
    skip_if_empty = (
        (weekday == 4 and mode == "evening") or   # viernes PM
        (weekday == 5) or                          # sábado (AM y PM)
        (weekday == 6 and mode == "morning")       # domingo AM
    )
    
    if skip_if_empty and not is_weekly and not force_send:
        calendario = data.get("calendario_persistente", [])
        # Verificar si hay eventos para hoy o mañana
        today_str = today.strftime("%Y-%m-%d")
        tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        has_events = any(e["fecha"] in (today_str, tomorrow) for e in calendario)
        # Verificar si hay novedades (emails, WA, comunicaciones nuevas)
        has_news = bool(data.get("emails")) or any(k.startswith("whatsapp_") and data[k] for k in data)
        
        if not has_events and not has_news:
            print(f"\n⏭️ Sin eventos ni novedades para hoy/mañana ({DIAS_ES[weekday]} {mode}). No se envía resumen.")
            return None

    print(f"\n{'='*50}")
    print(f"RESUMEN ({mode}{' - SEMANAL' if is_weekly else ''}) - {user_id}")
    print(f"{'='*50}")

    # Generar resumen
    engine = os.getenv("AI_ENGINE", "haiku")  # "haiku" o "gemini"
    api_key = os.getenv("GEMINI_API_KEY") if engine == "gemini" else os.getenv("ANTHROPIC_API_KEY")
    print(f"\n🤖 Generando resumen con {engine}...")
    summarizer = Summarizer(api_key, user_cfg=user_cfg, engine=engine)
    
    # Agregar user_id al data para que RAG pueda hacer queries
    data["_user_id"] = user_id
    
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
    msg_file = os.path.join("data", f"mensaje_enviar_{user_id}.json")
    with open(msg_file, "w", encoding="utf-8") as f:
        json.dump({"mensaje": message, "mode": mode, "user_id": user_id}, f, ensure_ascii=False)

    # Enviar por WhatsApp via outbox → wa_handler.js (WAHA)
    print("\n📱 Enviando por WhatsApp...")
    import subprocess
    send_script = "send_whatsapp.js"  # Escribe outbox, wa_handler lo envía via WAHA
    result = subprocess.run(
        ["node", send_script, user_id],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"   ⚠️ Error: {result.stderr}")

    return message


MAX_USERS_PER_INSTANCE = 8


def _load_users() -> list:
    """Cargar lista de usuarios.
    Fuente primaria: config/users/*.json (archivos individuales de S3)
    Fallback: config/users.json (legacy, para campos que no estén en S3)
    """
    users = []
    seen_ids = set()
    users_by_id = {}

    # 0. Sync desde S3 (descargar configs actualizados por la landing)
    try:
        import subprocess
        subprocess.run(
            ["aws", "s3", "sync", "s3://monitor-colegio-config-669294688330/config/users/", "config/users/", "--region", "us-east-2"],
            capture_output=True, timeout=30
        )
    except Exception:
        pass

    # 1. Legacy: config/users.json (tiene config completa con colegio, schoolnet, etc.)
    users_file = os.path.join("config", "users.json")
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                legacy_users = json.load(f)
            for user in legacy_users:
                if user.get("id"):
                    users.append(user)
                    seen_ids.add(user["id"])
                    users_by_id[user["id"]] = user
        except Exception as e:
            print(f"   ⚠️ Error leyendo users.json: {e}")

    # 2. Archivos individuales (S3) — merge sobre la config legacy (no reemplazar)
    users_dir = os.path.join("config", "users")
    if os.path.isdir(users_dir):
        for filename in os.listdir(users_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(users_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        s3_user = json.load(f)
                    uid = s3_user.get("id")
                    if not uid:
                        continue
                    if uid in users_by_id:
                        # Merge: S3 data overwrites only non-empty fields
                        for key, val in s3_user.items():
                            if val and key != "id":  # Don't override with empty values
                                users_by_id[uid][key] = val
                    else:
                        # New user from S3 (not in legacy)
                        users.append(s3_user)
                        seen_ids.add(uid)
                        users_by_id[uid] = s3_user
                except Exception as e:
                    print(f"   ⚠️ Error leyendo {filename}: {e}")

    return users


def _check_capacity(users: list):
    """Verificar que no se exceda la capacidad de la instancia."""
    if len(users) > MAX_USERS_PER_INSTANCE:
        print(f"\n🚨🚨🚨 ALERTA: {len(users)} usuarios excede el máximo de {MAX_USERS_PER_INSTANCE} por instancia!")
        print(f"   Crear una nueva instancia EC2 para los usuarios adicionales.")
        print(f"   Usuarios actuales: {[u['id'] for u in users]}")
        # Solo log, NO enviar a WhatsApp (no alarmar a los usuarios)


def ingest_for_user(user_cfg: dict) -> dict:
    """Ejecutar ingesta para un usuario según su config."""
    user_id = user_cfg["id"]
    data = {}
    connection_errors = []  # Alertas de fuentes que fallaron

    # Si tiene colegio con SchoolNet (Sagrado Corazón u otro Colegium)
    colegio = user_cfg.get("colegio", {})
    if not colegio:
        # Multi-colegio (como Oscar)
        colegios = user_cfg.get("colegios", [])
        for col in colegios:
            if col.get("plataforma_notas"):
                pn = col["plataforma_notas"]
                if "cuadernorojo" in pn.get("url", "").lower():
                    try:
                        cr_result = fetch_cuadernorojo(pn["user"], pn["pass"], max_comunicados=5)
                        if cr_result["login_ok"]:
                            data["cuadernorojo_comunicados"] = cr_result["comunicados"]
                    except Exception as e:
                        print(f"   ⚠️ Cuaderno Rojo: {e}")
            if col.get("web_url") and "oxford" in col.get("nombre", "").lower():
                try:
                    hijo = next((h for h in user_cfg.get("hijos", []) if h.get("colegio") == col["nombre"]), {})
                    oxford_data = fetch_oxford_all(curso=hijo.get("curso", ""))
                    data["oxford_noticias"] = oxford_data["noticias"]
                except Exception as e:
                    print(f"   ⚠️ Oxford: {e}")
    else:
        # Colegio único con SchoolNet
        sn_user = colegio.get("schoolnet_user", "")
        sn_pass = colegio.get("schoolnet_pass", "")
        if sn_user and sn_pass:
            try:
                sn = SchoolNetClient(sn_user, sn_pass)
                if sn.login():
                    # Extraprogramáticas PRIMERO (SSO caduca rápido)
                    # Solo scrappear si NO hay datos en config (cambian 1x/semestre)
                    user_extras = user_cfg.get("extraprogramaticas", [])
                    if not user_extras:
                        try:
                            from src.sources.extracurriculares import fetch_extracurriculares_browser
                            extras_raw = fetch_extracurriculares_browser(sn_user, sn_pass)
                            if extras_raw:
                                data["extraprogramaticas_schoolnet"] = [vars(e) if hasattr(e, '__dict__') else e for e in extras_raw]
                                print(f"   ✅ Extraprogramáticas scrapeadas: {len(extras_raw)}")
                        except Exception as e:
                            print(f"   ⚠️ Extraprogramáticas: {e}")
                    else:
                        print(f"   ✅ Extraprogramáticas desde config: {len(user_extras)}")

                    # Comunicaciones (compartido entre hijos)
                    data["comunicaciones"] = sn.get_comunicaciones()
                    print("   ✅ Comunicaciones")

                    # Pagos (compartido)
                    data["pagos"] = sn.get_pagos()
                    print("   ✅ Pagos")

                    # Avisos de cobranza (vencimientos futuros)
                    try:
                        data["avisos_cobranza"] = sn.get_avisos_cobranza()
                        print(f"   ✅ Avisos cobranza: {len(data['avisos_cobranza'])}")
                    except Exception as e:
                        print(f"   ⚠️ Avisos cobranza: {e}")

                    # Por cada hijo: calificaciones, asistencia, conducta, salud, compañeros
                    hijos = user_cfg.get("hijos", [])
                    for i, hijo in enumerate(hijos):
                        nombre = hijo["nombre"].lower()
                        try:
                            data[f"calificaciones_{nombre}"] = sn.get_calificaciones(i, periodo=1)
                            # Intentar 2do semestre también
                            sem2 = sn.get_calificaciones(i, periodo=2)
                            if isinstance(sem2, dict) and sem2.get("nombre"):
                                data[f"calificaciones_{nombre}_sem2"] = sem2
                        except Exception:
                            pass
                        try:
                            data[f"asistencia_{nombre}"] = sn.get_asistencia(i)
                        except Exception:
                            pass
                        try:
                            data[f"conducta_{nombre}"] = sn.get_conducta(i)
                        except Exception:
                            pass
                        try:
                            data[f"salud_{nombre}"] = sn.get_salud(i)
                        except Exception:
                            pass
                        try:
                            # Compañeros: cache compartido por curso (solo cambia 1x/mes)
                            curso = hijo.get("curso", "").replace(" ", "").lower()
                            colegio_id = _get_colegio_id(user_cfg)
                            cached_comp = get_companeros(colegio_id, curso) if colegio_id and curso else None
                            if cached_comp is not None:
                                data[f"companeros_{nombre}"] = cached_comp
                            else:
                                comp = sn.get_companeros(i)
                                data[f"companeros_{nombre}"] = comp
                                if colegio_id and curso and comp:
                                    set_companeros(colegio_id, curso, comp)
                        except Exception:
                            pass
                    print(f"   ✅ Datos por hijo ({len(hijos)} hijos)")

                else:
                    print("   ❌ SchoolNet login falló")
                    connection_errors.append("SchoolNet: login falló")
            except Exception as e:
                print(f"   ⚠️ SchoolNet: {e}")
                connection_errors.append(f"SchoolNet: {e}")

        # Calendario (API pública del colegio)
        cal_url = colegio.get("calendario_url", "")
        if cal_url:
            try:
                categorias = [h.get("categoria_calendario", "") for h in user_cfg.get("hijos", []) if h.get("categoria_calendario")]
                # Fallback: inferir categoría del curso (ej: "5-A" → "5", "1-C" → "1", "1EM" → "1EM")
                if not categorias:
                    for h in user_cfg.get("hijos", []):
                        curso = h.get("curso", "")
                        if curso:
                            # Extraer número/nivel del curso
                            import re as _re
                            m = _re.match(r'^(\d+)', curso)
                            if m:
                                categorias.append(m.group(1))
                if categorias:
                    # Cache compartido: calendario es igual para todos del mismo colegio
                    colegio_id = _get_colegio_id(user_cfg)
                    cached = get_evaluaciones(colegio_id)
                    if cached is not None:
                        data["calendario"] = cached
                        print(f"   ✅ Calendario evaluaciones: {len(cached)} eventos (cache)")
                    else:
                        data["calendario"] = fetch_evaluaciones(categorias)
                        print(f"   ✅ Calendario evaluaciones: {len(data['calendario'])} eventos (categorías: {categorias})")
                        set_evaluaciones(colegio_id, data["calendario"])
            except Exception as e:
                print(f"   ⚠️ Calendario: {e}")

        # SC Info (si es Sagrado Corazón)
        if colegio.get("scinfo_url"):
            try:
                colegio_id = _get_colegio_id(user_cfg)
                cached = get_scinfo(colegio_id)
                if cached is not None:
                    data["scinfo"] = cached
                    print(f"   ✅ SC Info (cache)")
                else:
                    data["scinfo"] = fetch_scinfo_latest()
                    set_scinfo(colegio_id, data["scinfo"])
                    print(f"   ✅ SC Info")
            except Exception as e:
                print(f"   ⚠️ SC Info: {e}")

        # Casino/Menú del día (PDF mensual)
        if colegio.get("casino_url"):
            try:
                from src.sources.casino import fetch_casino_menu, fetch_casino_menu_today
                colegio_id = _get_colegio_id(user_cfg)
                cached_casino = get_casino(colegio_id)
                cached_hoy = get_casino_hoy(colegio_id)
                if cached_casino is not None:
                    data["casino"] = cached_casino
                    if cached_hoy:
                        data["casino_hoy"] = cached_hoy
                    print(f"   ✅ Casino (cache)")
                else:
                    data["casino"] = fetch_casino_menu(colegio["casino_url"])
                    menu_hoy = fetch_casino_menu_today(colegio["casino_url"])
                    if menu_hoy:
                        data["casino_hoy"] = menu_hoy
                    set_casino(colegio_id, data["casino"])
                    if menu_hoy:
                        set_casino_hoy(colegio_id, menu_hoy)
                    print(f"   ✅ Casino: {len(data['casino'].get('contenido', ''))} chars")
            except Exception as e:
                print(f"   ⚠️ Casino: {e}")

        # Web del colegio: noticias, calendario, talleres (complementa SchoolNet)
        web_urls = {}
        if colegio.get("calendario_url") and "calendar.json" not in colegio.get("calendario_url", ""):
            web_urls["calendario"] = colegio["calendario_url"]
        if colegio.get("noticias_url"):
            web_urls["noticias"] = colegio["noticias_url"]
        if colegio.get("talleres_url"):
            web_urls["talleres"] = colegio["talleres_url"]
        if colegio.get("extraprogramaticas_url"):
            web_urls["talleres"] = colegio["extraprogramaticas_url"]
        if colegio.get("deportiva_url"):
            web_urls["deportiva"] = colegio["deportiva_url"]

        if web_urls or colegio.get("web_url"):
            try:
                from src.sources.web_colegio import WebColegioScraper
                scraper = WebColegioScraper(colegio.get("web_url", ""), web_urls)
                web_data = scraper.scrape_all()
                if web_data:
                    data["web_colegio"] = web_data
                    topicos_encontrados = [k for k in web_data if not k.startswith("_")]
                    print(f"   ✅ Web colegio: {', '.join(topicos_encontrados)}")
            except Exception as e:
                print(f"   ⚠️ Web colegio: {e}")

    # Gmail
    gmail_cfg = user_cfg.get("gmail", {})
    if isinstance(gmail_cfg, dict) and gmail_cfg.get("accounts"):
        # Multi-account (Oscar)
        creds_file = gmail_cfg.get("credentials_file", "")
        for account in gmail_cfg.get("accounts", []):
            token_file = account.get("token_file", "")
            if token_file and os.path.exists(token_file) and creds_file and os.path.exists(creds_file):
                try:
                    gmail = GmailClient(creds_file, token_file)
                    gmail.authenticate()
                    from src.sources.gmail_source import SCHOOL_DOMAINS
                    original = SCHOOL_DOMAINS[:]
                    SCHOOL_DOMAINS.clear()
                    SCHOOL_DOMAINS.extend(account.get("school_domains", []))
                    data[f"emails_{account.get('hijo', 'general').lower()}"] = gmail.get_school_emails(days=7)
                    SCHOOL_DOMAINS.clear()
                    SCHOOL_DOMAINS.extend(original)
                except Exception as e:
                    print(f"   ⚠️ Gmail: {e}")
    elif isinstance(gmail_cfg, dict) and (gmail_cfg.get("credentials_file") or gmail_cfg.get("token_file")):
        # Single account con config explícita
        creds_file = gmail_cfg.get("credentials_file", "credentials.json")
        token_file = gmail_cfg.get("token_file", "token.json")
        # Fallback: token sincronizado de S3 (generado por landing OAuth)
        if not os.path.exists(token_file):
            s3_token = os.path.join("config", "tokens", f"{user_id}_gmail_token.json")
            if os.path.exists(s3_token):
                token_file = s3_token
                creds_file = ""  # No se necesita, el token S3 tiene client_id/secret embebido
                print(f"   📧 Usando token Gmail de landing (S3)")
        if os.path.exists(token_file):
            try:
                gmail = GmailClient(creds_file, token_file)
                gmail.authenticate()
                data["emails"] = gmail.get_school_emails(days=7)
            except Exception as e:
                print(f"   ⚠️ Gmail: {e}")
    else:
        # Fallback universal: buscar token de S3 aunque no haya config de Gmail
        s3_token = os.path.join("config", "tokens", f"{user_id}_gmail_token.json")
        if os.path.exists(s3_token):
            print(f"   📧 Usando token Gmail de landing (S3)")
            try:
                gmail = GmailClient("", s3_token)
                gmail.authenticate()
                data["emails"] = gmail.get_school_emails(days=7)
            except Exception as e:
                print(f"   ⚠️ Gmail: {e}")

    # WhatsApp messages (del archivo compartido)
    wa_cfg = user_cfg.get("whatsapp", {})
    wa_file = os.path.join("data", "whatsapp_messages.json")
    if os.path.exists(wa_file):
        with open(wa_file, "r", encoding="utf-8") as f:
            all_wa = json.load(f)
        
        # Método 1: grupos_lectura (mapeo explícito group_id → label)
        grupos_lectura = wa_cfg.get("grupos_lectura", {})
        if grupos_lectura:
            for group_id, label in grupos_lectura.items():
                if label in all_wa:
                    data[f"whatsapp_{label}"] = all_wa[label]
        else:
            # Método 2: usar whatsapp_groups de la landing (tiene id, name, hijo)
            # El wa_handler guarda con labels derivadas del nombre del grupo
            wa_groups = user_cfg.get("whatsapp_groups", [])
            if wa_groups:
                # Mapear: buscar labels en all_wa que coincidan con los grupos configurados
                for label, msgs in all_wa.items():
                    if msgs:
                        data[f"whatsapp_{label}"] = msgs
            else:
                # Fallback: cargar TODOS los mensajes disponibles (usuario con config legacy)
                for label, msgs in all_wa.items():
                    if msgs:
                        data[f"whatsapp_{label}"] = msgs

    # Monitor inputs (instrucciones de los padres)
    monitor_file = os.path.join("data", f"monitor_inputs_{user_id}.json")
    if os.path.exists(monitor_file):
        with open(monitor_file, "r", encoding="utf-8") as f:
            data["instrucciones_padres"] = json.load(f)
    elif os.path.exists(os.path.join("data", "monitor_inputs.json")) and user_id == "pablo_ardiles":
        with open(os.path.join("data", "monitor_inputs.json"), "r", encoding="utf-8") as f:
            data["instrucciones_padres"] = json.load(f)

    # Horarios
    data["horarios"] = _load_horarios()

    # Extraer eventos de WA y emails con AI (cumpleaños, paseos, partidos, etc.)
    print("\n🔍 Extrayendo eventos de mensajes...")
    try:
        ai_key = os.getenv("ANTHROPIC_API_KEY", "")
        if ai_key:
            from src.sources.event_extractor import process_and_store_events
            wa_msgs = {k.replace("whatsapp_", ""): v for k, v in data.items() if k.startswith("whatsapp_") and v}
            emails_data = data.get("emails", [])
            hijos = user_cfg.get("hijos", [])
            extracted = process_and_store_events(wa_msgs, emails_data, hijos, ai_key, user_id)
            if extracted:
                data["eventos_extraidos"] = extracted
    except Exception as e:
        print(f"   ⚠️ Event extraction: {e}")

    # Calendario persistente: actualizar con datos nuevos y cargar próximos eventos
    print("\n📅 Calendario persistente...")
    try:
        data["_user_cfg"] = user_cfg  # Para que calendar_store pueda asignar hijo por nivel
        new_events = update_calendar_from_sources(data, user_id=user_id)
        del data["_user_cfg"]
        upcoming = get_upcoming_events(days=14, user_id=user_id)
        data["calendario_persistente"] = upcoming
        print(f"   ✅ {new_events} eventos nuevos, {len(upcoming)} próximos 14 días")
    except Exception as e:
        print(f"   ⚠️ Calendario: {e}")
        data["calendario_persistente"] = get_upcoming_events(days=14, user_id=user_id)

    # Guardar contexto enriquecido para el bot conversacional
    try:
        bot_context = {}
        # Compañeros (por hijo) — solo los del MISMO CURSO del hijo
        hijos_cfg = user_cfg.get("hijos", [])
        for key in data:
            if key.startswith("companeros_"):
                companeros_data = data[key]
                if isinstance(companeros_data, dict) and companeros_data.get("companeros"):
                    hijo_name = key.replace("companeros_", "")
                    # Obtener curso del hijo desde config
                    hijo_curso = ""
                    for h in hijos_cfg:
                        if h.get("nombre", "").lower() == hijo_name.lower() or hijo_name.lower() in h.get("nombre", "").lower():
                            hijo_curso = h.get("curso", "").replace(" ", "").replace("-", "").lower()
                            break
                    # Filtrar: solo compañeros del mismo curso
                    all_comps = companeros_data["companeros"]
                    if hijo_curso:
                        filtered = [c for c in all_comps if c.get("curso", "").replace(" ", "").replace("-", "").lower() == hijo_curso]
                    else:
                        filtered = all_comps  # Sin filtro si no sabemos el curso
                    
                    bot_context.setdefault("companeros", {})[hijo_name] = [
                        {
                            "nombre": c.get("nombre", ""),
                            "cumple": c.get("fnacimiento", c.get("cumpleanos", c.get("cumple", ""))),
                            "telefono": c.get("telefono", c.get("celular", "")),
                            "direccion": c.get("direccioncompleta", c.get("direccion", "")),
                            "padre": c.get("nombrepadre", c.get("padre", "")),
                            "madre": c.get("nombremadre", c.get("madre", "")),
                            "celular_padre": c.get("celularpadre", ""),
                            "celular_madre": c.get("celularmadre", ""),
                            "email_padre": c.get("emailpadre", ""),
                            "email_madre": c.get("emailmadre", ""),
                            "curso": c.get("curso", ""),
                        }
                        for c in filtered
                    ]
        # Calificaciones (por hijo)
        for key in data:
            if key.startswith("calificaciones_") and not key.endswith("_sem2"):
                cal_data = data[key]
                if isinstance(cal_data, dict):
                    hijo_name = key.replace("calificaciones_", "")
                    # SchoolNet: "nombre" = asignaturas, "pf" = promedios finales
                    nombres_asigs = cal_data.get("nombre", [])
                    pf = cal_data.get("pf", [])
                    promedios_gen = cal_data.get("promedios", {})
                    if isinstance(nombres_asigs, list) and nombres_asigs:
                        notas = []
                        for i, asig in enumerate(nombres_asigs):
                            nota = pf[i] if i < len(pf) and pf[i] else ""
                            notas.append({"asignatura": asig, "promedio": nota})
                        bot_context.setdefault("calificaciones", {})[hijo_name] = notas
                        if isinstance(promedios_gen, dict) and promedios_gen.get("anual"):
                            bot_context.setdefault("promedios_generales", {})[hijo_name] = promedios_gen.get("anual", "")
                    # Fallback para otras plataformas
                    elif cal_data.get("asignaturas") or cal_data.get("calificaciones"):
                        asigs = cal_data.get("asignaturas", cal_data.get("calificaciones", []))
                        if isinstance(asigs, list):
                            bot_context.setdefault("calificaciones", {})[hijo_name] = [
                                {"asignatura": a.get("nombre", a.get("asignatura", "")), "promedio": a.get("promedio", "")}
                                for a in asigs[:20] if isinstance(a, dict)
                            ]
            # 2do semestre
            elif key.endswith("_sem2"):
                cal_data = data[key]
                if isinstance(cal_data, dict):
                    hijo_name = key.replace("calificaciones_", "").replace("_sem2", "")
                    nombres_asigs = cal_data.get("nombre", [])
                    pf = cal_data.get("pf", [])
                    if isinstance(nombres_asigs, list) and nombres_asigs:
                        notas = []
                        for i, asig in enumerate(nombres_asigs):
                            nota = pf[i] if i < len(pf) and pf[i] else ""
                            notas.append({"asignatura": asig, "promedio": nota})
                        bot_context.setdefault("calificaciones_sem2", {})[hijo_name] = notas
        # Conducta/anotaciones (por hijo)
        for key in data:
            if key.startswith("conducta_"):
                cond_data = data[key]
                if isinstance(cond_data, dict):
                    hijo_name = key.replace("conducta_", "")
                    anotaciones = cond_data.get("anotaciones", cond_data.get("conducta", []))
                    if isinstance(anotaciones, list):
                        bot_context.setdefault("conducta", {})[hijo_name] = anotaciones[-10:]  # últimas 10
        # Asistencia (por hijo)
        for key in data:
            if key.startswith("asistencia_"):
                asist_data = data[key]
                if isinstance(asist_data, dict):
                    hijo_name = key.replace("asistencia_", "")
                    bot_context.setdefault("asistencia", {})[hijo_name] = {
                        "inasistencias": len(asist_data.get("inasistencias", [])),
                        "ultimas": asist_data.get("inasistencias", [])[-5:],
                        "atrasos": asist_data.get("atrasos", []),
                    }
        # Profesores (de hijos config)
        bot_context["profesores"] = [
            {"hijo": h["nombre"], "profesora_jefe": h.get("profesora_jefe", ""), "curso": h.get("curso", "")}
            for h in user_cfg.get("hijos", [])
        ]
        # Agregar emails de profesores desde datos de SchoolNet (asistencia)
        for key in data:
            if key.startswith("asistencia_"):
                asist_data = data[key]
                if isinstance(asist_data, dict):
                    hijo_name = key.replace("asistencia_", "")
                    mail_prof = asist_data.get("mailProfJefe", [""])[0] if isinstance(asist_data.get("mailProfJefe"), list) else asist_data.get("mailProfJefe", "")
                    if mail_prof:
                        for p in bot_context["profesores"]:
                            if p["hijo"].lower() == hijo_name:
                                p["email"] = mail_prof
        # Colegio info
        colegio = user_cfg.get("colegio", {})
        if colegio:
            bot_context["colegio"] = {"nombre": colegio.get("nombre", ""), "web": colegio.get("scinfo_url", "")}
        # WhatsApp grupos monitoreados
        wa_cfg = user_cfg.get("whatsapp", {})
        bot_context["grupos_wa"] = list(wa_cfg.get("grupos_lectura", {}).values())
        # Últimos mensajes WA relevantes (para contexto reciente)
        wa_recientes = {}
        for key in data:
            if key.startswith("whatsapp_") and data[key]:
                msgs = data[key][-10:]  # últimos 10 por grupo
                wa_recientes[key.replace("whatsapp_", "")] = [
                    {"from": m.get("from", ""), "body": m.get("body", "")[:100], "date": m.get("date", "")}
                    for m in msgs
                ]
        if wa_recientes:
            bot_context["whatsapp_reciente"] = wa_recientes

        # Emails recientes
        if "emails" in data and data["emails"]:
            bot_context["emails_recientes"] = [
                {"fecha": e.get("fecha", ""), "de": e.get("de", ""), "asunto": e.get("asunto", ""), "resumen": e.get("body", "")[:200]}
                for e in data["emails"][:10]
            ]

        # SC Info
        if "scinfo" in data and data["scinfo"]:
            scinfo = data["scinfo"]
            bot_context["scinfo"] = {
                "fecha": scinfo.get("fecha", ""),
                "contenido": scinfo.get("contenido", "")[:1000]
            }

        # Pagos/Cobranza
        if "pagos" in data and data["pagos"]:
            bot_context["pagos"] = data["pagos"]

        # Avisos de cobranza (vencimientos futuros con montos pendientes)
        if "avisos_cobranza" in data and data["avisos_cobranza"]:
            bot_context["avisos_cobranza"] = data["avisos_cobranza"]

        # Casino/Menú del día
        if "casino_hoy" in data and data["casino_hoy"]:
            bot_context["casino_hoy"] = data["casino_hoy"]
        elif "casino" in data and data["casino"].get("contenido"):
            bot_context["casino_menu"] = data["casino"]["contenido"][:1000]

        # Web del colegio (noticias, calendario, talleres)
        if "web_colegio" in data and data["web_colegio"]:
            web = data["web_colegio"]
            if "noticias" in web and isinstance(web["noticias"], list):
                bot_context["noticias_colegio"] = web["noticias"][:5]
            if "calendario" in web and isinstance(web["calendario"], dict):
                cal_content = web["calendario"].get("contenido_html", "")
                pdfs_content = " ".join([p.get("contenido", "") for p in web["calendario"].get("pdfs", [])])
                bot_context["calendario_web"] = (cal_content + " " + pdfs_content)[:2000]
            if "talleres" in web and isinstance(web["talleres"], dict):
                tal_content = web["talleres"].get("contenido_html", "")
                pdfs_content = " ".join([p.get("contenido", "") for p in web["talleres"].get("pdfs", [])])
                bot_context["talleres"] = (tal_content + " " + pdfs_content)[:1500]

        # Calendario persistente (eventos próximos: pruebas, reuniones, actividades)
        if data.get("calendario_persistente"):
            bot_context["calendario"] = [
                {
                    "fecha": e.get("fecha", ""),
                    "hora": e.get("hora", ""),
                    "descripcion": e.get("descripcion", ""),
                    "tipo": e.get("tipo", ""),
                    "hijo": e.get("hijo", ""),
                    "lugar": e.get("lugar", ""),
                }
                for e in data["calendario_persistente"][:30]
            ]

        # PDFs recibidos por WhatsApp (circulares, calendarios de pruebas, etc.)
        try:
            wa_pdfs = get_pdf_summary_for_context(user_id)
            if wa_pdfs:
                bot_context["documentos_wa"] = wa_pdfs
                print(f"   ✅ PDFs WA: {len(wa_pdfs)} documentos procesados")
        except Exception as e:
            print(f"   ⚠️ PDFs WA: {e}")

        save_bot_context(user_id, bot_context)
        update_meta(user_id, "bot_context")
        print(f"   ✅ Bot context guardado ({len(json.dumps(bot_context))} chars)")

        # Indexar en RAG (si el servicio está disponible)
        try:
            import requests as _req
            _rag_url = os.environ.get("RAG_URL", "http://localhost:8086")
            r = _req.post(f"{_rag_url}/index/{user_id}", timeout=10)
            if r.status_code == 200:
                rag_result = r.json()
                print(f"   ✅ RAG indexado: {rag_result.get('chunks', 0)} chunks ({rag_result.get('backend', '?')})")
        except Exception:
            pass  # RAG opcional — si no está corriendo, no importa
    except Exception as e:
        print(f"   ⚠️ Bot context: {e}")

    return data


def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py [morning|evening|ingest|test]")
        sys.exit(1)

    mode = sys.argv[1].lower()

    # Cargar usuarios
    users = _load_users()
    if not users:
        print("❌ No hay usuarios configurados")
        sys.exit(1)

    # Check capacidad
    _check_capacity(users)

    if mode == "ingest":
        data = ingest_all()
        output_file = f"data/ingesta_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        os.makedirs("data", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Datos guardados en {output_file}")

    elif mode in ("morning", "evening"):
        today = datetime.now(CHILE_TZ)
        is_weekly = (today.weekday() == 6 and mode == "evening")

        # Si se pasa un user_id específico (para welcome message)
        if len(sys.argv) > 2:
            target_user = sys.argv[2]
            user_cfg = next((u for u in users if u["id"] == target_user), None)
            if user_cfg:
                print(f"\n{'🟡' * 25}")
                print(f"USUARIO: {user_cfg['nombre']} (individual)")
                print(f"{'🟡' * 25}")
                data = ingest_for_user(user_cfg)
                if data:
                    generate_and_send(mode, data, is_weekly=is_weekly, user_id=target_user, user_cfg=user_cfg, force_send=True)
            else:
                print(f"❌ Usuario '{target_user}' no encontrado")
            sys.exit(0)

        # Loop por todos los usuarios
        # Jitter anti-detección: distribuir scraping en ventana de tiempo
        # EC2_JITTER_OFFSET_MIN: offset base de esta EC2 (0, 10, 20...)
        # Cada usuario tiene delay adicional basado en su posición + hash
        ec2_offset = int(os.environ.get("EC2_JITTER_OFFSET_MIN", "0")) * 60  # segundos
        jitter_window = int(os.environ.get("JITTER_WINDOW_SEC", "0"))  # 0 = sin jitter (dev/pocos usuarios)
        
        for i, user_cfg in enumerate(users):
            user_id = user_cfg["id"]
            colores = ["🔵", "🟢", "🟡", "🟣", "🟠", "🔴", "⚪", "🟤"]
            color = colores[i % len(colores)]
            print(f"\n{color * 25}")
            print(f"USUARIO {i+1}/{len(users)}: {user_cfg['nombre']}")
            print(f"{color * 25}")

            # Jitter por usuario (solo si hay ventana configurada)
            if jitter_window > 0 and len(users) > 1:
                import hashlib as _hl
                user_jitter = int(_hl.md5(f"{user_id}{today.strftime('%Y%m%d')}".encode()).hexdigest(), 16) % jitter_window
                total_delay = ec2_offset + user_jitter
                if total_delay > 0:
                    print(f"   ⏳ Jitter: {total_delay}s (EC2 offset {ec2_offset}s + user {user_jitter}s)")
                    import time as _t
                    _t.sleep(total_delay)

            try:
                data = ingest_for_user(user_cfg)
                if data:
                    generate_and_send(mode, data, is_weekly=is_weekly, user_id=user_id, user_cfg=user_cfg)
                else:
                    print(f"   ⚠️ Sin datos para {user_cfg['nombre']}, saltando")
            except Exception as e:
                print(f"   ❌ Error procesando {user_cfg['nombre']}: {e}")

    elif mode == "test":
        # Test: primer usuario o especificar
        target = sys.argv[2] if len(sys.argv) > 2 else users[0]["id"]
        user_cfg = next((u for u in users if u["id"] == target), users[0])
        print(f"Test para: {user_cfg['nombre']}")
        data = ingest_for_user(user_cfg)
        summarizer = Summarizer(os.getenv("ANTHROPIC_API_KEY"), user_cfg=user_cfg)
        if len(sys.argv) > 3 and sys.argv[3] == "evening":
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
