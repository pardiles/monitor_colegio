"""
Fuente: Extracurriculares (Colegium).

Flujo:
1. Login en SchoolNet con Playwright (obtiene connect.sid)
2. Desde el MISMO browser, navegar al link de extracurriculares (SSO redirect automático)
3. Cloudflare ve un browser real con sesión legítima → lo deja pasar
4. Capturar HTML renderizado + screenshot
5. Parsear actividades del HTML

La clave es NO cerrar el browser entre SchoolNet y extracurriculares.
Cloudflare confía en el browser que ya pasó el challenge de SchoolNet.
"""

import re
import os
import time
import json
from typing import List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Extracurricular:
    nombre: str
    dia: str
    horario: str
    fecha_inicio: str
    profesor: str
    costo: str
    estado: str  # pagada, sin costo, pendiente
    hijo: str = ""


def fetch_extracurriculares_browser(username: str, password: str, debug_dir: str = None) -> List[Extracurricular]:
    """
    Scrape extracurriculares usando browser real.
    Login en SchoolNet → redirect SSO → extracurriculares.colegium.com
    
    Args:
        username: SchoolNet user
        password: SchoolNet pass
        debug_dir: Si se pasa, guarda HTML + screenshot para debugging
        
    Returns:
        Lista de extracurriculares inscritas
    """
    from playwright.sync_api import sync_playwright

    LOGIN_URL = "https://schoolnet.colegium.com/webapp/es_CL/login"
    EXTRAS_PATH = "/webapp/es_CL/indice/registroingreso?id=linkextracurriculares"
    BASE_URL = "https://schoolnet.colegium.com"

    actividades = []
    debug_dir = debug_dir or os.path.join("data", "debug_extras")
    os.makedirs(debug_dir, exist_ok=True)

    with sync_playwright() as p:
        # Browser real, headless con xvfb (Cloudflare no ve diferencia)
        browser = p.chromium.launch(
            headless=False,  # xvfb-run en EC2 lo hace "headed" sin pantalla real
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="es-CL",
            timezone_id="America/Santiago",
        )
        
        # Anti-detección básica
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['es-CL', 'es', 'en']});
        """)

        page = context.new_page()

        # Capturar XHR responses de /datos (donde vienen las actividades)
        xhr_responses = []
        def capture_response(response):
            url = response.url
            if "/datos" in url or "getUserApplications" in url or "inscritas" in url:
                try:
                    body = response.text()
                    if len(body) > 50:
                        xhr_responses.append({"url": url, "status": response.status, "body": body})
                        print(f"   📡 XHR capturado: {url[:80]} ({len(body)} chars)")
                except Exception:
                    pass
        page.on("response", capture_response)

        try:
            # === PASO 1: Login en SchoolNet ===
            print("   🔑 Login SchoolNet...")
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=20000)
            page.fill("#signin_username", username)
            page.fill("#signin_password", password)
            page.click("#btn_login")

            try:
                page.wait_for_url("**/index**", timeout=15000)
            except Exception:
                print("   ❌ Login falló")
                page.screenshot(path=os.path.join(debug_dir, "01_login_failed.png"))
                browser.close()
                return []

            time.sleep(2)

            # Cerrar modal "contraseña no segura" si aparece
            try:
                cancelar = page.locator("button, a").filter(has_text="Cancelar").first
                if cancelar.is_visible(timeout=3000):
                    cancelar.click()
                    time.sleep(1)
            except Exception:
                pass

            print("   ✅ Login OK")
            page.screenshot(path=os.path.join(debug_dir, "02_schoolnet_logged.png"))

            # === PASO 2: Navegar a extracurriculares (SSO redirect) ===
            print("   🔗 Navegando a extracurriculares...")
            
            # Opción A: navegar directamente al link de extracurriculares
            extras_url = f"{BASE_URL}{EXTRAS_PATH}"
            page.goto(extras_url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            current_url = page.url
            print(f"   📍 URL actual: {current_url[:80]}")

            # Si SchoolNet hizo el SSO redirect, ahora estamos en extracurriculares.colegium.com
            if "extracurriculares.colegium.com" in current_url:
                print("   ✅ Redirect SSO exitoso → extracurriculares.colegium.com")
            else:
                # Puede que SchoolNet devolvió un JSON con la URL SSO
                try:
                    body_text = page.evaluate("() => document.body.innerText || ''")
                    if body_text.startswith("{"):
                        data = json.loads(body_text)
                        sso_url = data.get("url", "")
                        if sso_url:
                            print(f"   🔗 SSO URL obtenida: {sso_url[:80]}")
                            page.goto(sso_url, wait_until="networkidle", timeout=60000)
                            current_url = page.url
                            print(f"   📍 URL después de SSO: {current_url[:80]}")
                except Exception:
                    pass

            # === PASO 3: Esperar carga + Cloudflare challenge ===
            time.sleep(5)

            # Si Cloudflare muestra challenge, esperar hasta 30s
            for i in range(6):
                title = page.title()
                if "just a moment" in title.lower() or "cloudflare" in title.lower():
                    print(f"   ⏳ Cloudflare challenge... ({(i+1)*5}s)")
                    time.sleep(5)
                else:
                    break

            page.screenshot(path=os.path.join(debug_dir, "03_extracurriculares_page.png"))

            # === PASO 4: Capturar HTML ===
            html = page.content()
            with open(os.path.join(debug_dir, "04_extracurriculares.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"   📄 HTML guardado ({len(html)} chars)")

            # === PASO 5: Interactuar — click en tabs, alumnos ===
            # Esperar a que cargue el contenido dinámico (React/Angular)
            time.sleep(3)

            # Detectar nombres de alumnos
            alumno_elements = page.locator("[class*='alumno'], [class*='student'], [class*='avatar'], [role='tab']").all()
            print(f"   👦 Elementos de alumnos detectados: {len(alumno_elements)}")

            # Click en "Inscritas" tab si existe
            try:
                tabs = page.locator("a, button, li, div[role='tab']").filter(has_text=re.compile(r"inscrit", re.IGNORECASE)).all()
                if tabs:
                    tabs[0].click()
                    time.sleep(3)
                    print("   📋 Tab 'Inscritas' clickeado")
                    page.screenshot(path=os.path.join(debug_dir, "05_inscritas_tab.png"))
            except Exception as e:
                print(f"   ⚠️ Tab inscritas: {e}")

            # Capturar HTML final después de interacciones
            html_final = page.content()
            with open(os.path.join(debug_dir, "06_final.html"), "w", encoding="utf-8") as f:
                f.write(html_final)

            # === PASO 6: Parsear actividades ===
            # Primero intentar desde XHR responses (más confiable)
            if xhr_responses:
                print(f"   📡 {len(xhr_responses)} XHR responses capturados")
                for xhr in xhr_responses:
                    with open(os.path.join(debug_dir, f"xhr_{len(actividades)}.json"), "w", encoding="utf-8") as f:
                        f.write(xhr["body"])
                    parsed = _parse_xhr_response(xhr["body"])
                    if parsed:
                        actividades.extend(parsed)

            # Si no hay XHR, parsear HTML
            if not actividades:
                actividades = _parse_html_actividades(html_final)

            print(f"   📊 Total actividades encontradas: {len(actividades)}")

            # Guardar XHR capturados para debugging
            with open(os.path.join(debug_dir, "xhr_all.json"), "w", encoding="utf-8") as f:
                json.dump(xhr_responses, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"   ❌ Error extracurriculares: {e}")
            try:
                page.screenshot(path=os.path.join(debug_dir, "error.png"))
            except Exception:
                pass
        finally:
            browser.close()

    return actividades


def _parse_xhr_response(body: str) -> List[Extracurricular]:
    """Parsear respuesta JSON del XHR de actividades."""
    actividades = []
    try:
        data = json.loads(body)
        # El formato puede ser array de actividades o un objeto con una key
        items = data if isinstance(data, list) else data.get("actividades", data.get("data", data.get("inscritas", [])))
        
        if not isinstance(items, list):
            return []

        for item in items:
            if not isinstance(item, dict):
                continue
            nombre = item.get("nombre", item.get("actividad", item.get("name", "")))
            dia = item.get("dia", item.get("day", ""))
            horario = item.get("horario", item.get("hora", item.get("schedule", "")))
            fecha_inicio = item.get("fecha_inicio", item.get("fechaInicio", item.get("startDate", "")))
            profesor = item.get("profesor", item.get("teacher", ""))
            costo = item.get("costo", item.get("cost", ""))
            estado = item.get("estado", item.get("status", "pagada"))
            hijo = item.get("alumno", item.get("student", ""))

            if nombre:
                actividades.append(Extracurricular(
                    nombre=nombre, dia=dia, horario=horario,
                    fecha_inicio=fecha_inicio, profesor=profesor,
                    costo=str(costo), estado=estado, hijo=hijo,
                ))
    except (json.JSONDecodeError, TypeError):
        pass
    return actividades


def _parse_html_actividades(html: str) -> List[Extracurricular]:
    """Parsear actividades del HTML renderizado."""
    actividades = []

    # Limpiar HTML a texto
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Buscar patrones de horario: DIA HH:MM-HH:MM
    horario_pattern = re.compile(
        r'(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})',
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        match = horario_pattern.search(line)
        if match:
            dia = match.group(1).upper()
            horario = f"{match.group(2)}-{match.group(3)}"

            # Buscar nombre (líneas anteriores)
            nombre = ""
            fecha_inicio = ""
            costo = ""
            profesor = ""
            estado = "pagada"

            for j in range(max(0, i - 12), i):
                prev = lines[j]
                if "Inicio:" in prev:
                    fecha_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', prev)
                    if fecha_match:
                        # Convertir DD/MM/YYYY → YYYY-MM-DD
                        parts = fecha_match.group(1).split("/")
                        if len(parts) == 3:
                            fecha_inicio = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                elif "Profesor:" in prev:
                    profesor = prev.replace("Profesor:", "").strip()
                elif "Sin Costo" in prev:
                    costo = "Sin Costo"
                    estado = "sin costo"
                elif "$" in prev and "CLP" in prev:
                    costo = prev.strip()
                    estado = "pagada"
                elif not nombre and len(prev) > 5 and not any(x in prev for x in ["Fecha", "Profesor", "Costo", "Horario", "Inicio", "inscripción"]):
                    if not re.match(r'^[\d/]+$', prev):
                        nombre = prev

            if nombre:
                actividades.append(Extracurricular(
                    nombre=nombre, dia=dia, horario=horario,
                    fecha_inicio=fecha_inicio, profesor=profesor,
                    costo=costo, estado=estado,
                ))

    return actividades


# Legacy function (mantener compatibilidad con main.py)
def fetch_extracurriculares(sso_url: str, cookies: dict = None) -> List[Extracurricular]:
    """
    Legacy wrapper. Intenta con Playwright directo al SSO URL.
    Para el nuevo approach usar fetch_extracurriculares_browser().
    """
    from playwright.sync_api import sync_playwright

    actividades = []
    debug_dir = os.path.join("data", "debug_extras")
    os.makedirs(debug_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        if cookies:
            cookie_list = [{"name": k, "value": v, "domain": ".colegium.com", "path": "/"} for k, v in cookies.items()]
            context.add_cookies(cookie_list)

        page = context.new_page()

        # Capturar XHR
        xhr_responses = []
        def capture(response):
            if "/datos" in response.url or "inscritas" in response.url:
                try:
                    body = response.text()
                    if len(body) > 50:
                        xhr_responses.append(body)
                except Exception:
                    pass
        page.on("response", capture)

        try:
            page.goto(sso_url, wait_until="networkidle", timeout=60000)
            time.sleep(8)

            # Wait for Cloudflare
            for _ in range(6):
                if "just a moment" in page.title().lower():
                    time.sleep(5)
                else:
                    break

            html = page.content()
            with open(os.path.join(debug_dir, "legacy_page.html"), "w", encoding="utf-8") as f:
                f.write(html)
            page.screenshot(path=os.path.join(debug_dir, "legacy_page.png"))

            # Parse XHR first
            for body in xhr_responses:
                parsed = _parse_xhr_response(body)
                if parsed:
                    actividades.extend(parsed)

            # Fallback HTML
            if not actividades:
                actividades = _parse_html_actividades(html)

        except Exception as e:
            print(f"   ⚠️ Extracurriculares legacy: {e}")
        finally:
            browser.close()

    return [a for a in actividades if a.estado in ("pagada", "sin costo")]
