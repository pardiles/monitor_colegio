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
    
    NOTA: Este scraper usa IP residencial Chile (Bright Data ISP) para
    bypass Cloudflare. Configurado en .env (PROXY_HOST, etc).
    Plan: 1 IP fija por cada 10 usuarios.
    
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
        
        # Proxy residencial (Bright Data ISP Chile) si está configurado
        from src.proxy_config import get_playwright_proxy
        proxy = get_playwright_proxy()
        
        context_opts = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 768},
            "locale": "es-CL",
            "timezone_id": "America/Santiago",
        }
        if proxy:
            context_opts["proxy"] = proxy
            print(f"   🌐 Usando proxy residencial: {proxy['server']}")
        
        context = browser.new_context(**context_opts)
        
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

            # === PASO 2: Obtener URL SSO de extracurriculares ===
            # La API interna de SchoolNet genera un token SSO temporal
            print("   🔗 Obteniendo URL SSO...")
            
            # Navegar a la API que devuelve la URL SSO (es una página que retorna JSON)
            api_url = f"{BASE_URL}/webapp/es_CL/extracurricularescondor/index"
            page.goto(api_url, wait_until="networkidle", timeout=15000)
            time.sleep(2)
            
            # Leer el JSON con la URL SSO
            sso_url = ""
            try:
                body_text = page.evaluate("() => document.body.innerText || document.body.textContent || ''")
                body_text = body_text.strip()
                if body_text.startswith("{"):
                    data = json.loads(body_text)
                    sso_url = data.get("url", "")
                elif "http" in body_text:
                    # Puede ser la URL directa
                    url_match = re.search(r'(https?://extracurriculares[^\s"<]+)', body_text)
                    if url_match:
                        sso_url = url_match.group(1)
            except Exception as e:
                print(f"   ⚠️ Error obteniendo SSO URL: {e}")

            if not sso_url:
                print("   ❌ No se pudo obtener URL SSO de extracurriculares")
                page.screenshot(path=os.path.join(debug_dir, "02b_no_sso_url.png"))
                with open(os.path.join(debug_dir, "02b_api_response.txt"), "w") as f:
                    f.write(body_text[:5000] if body_text else "EMPTY")
                browser.close()
                return []

            print(f"   🔗 SSO URL: {sso_url[:80]}...")

            # === PASO 3: Navegar al SSO URL en el MISMO browser ===
            print("   🌐 Navegando a extracurriculares.colegium.com...")
            page.goto(sso_url, wait_until="networkidle", timeout=60000)
            time.sleep(5)

            current_url = page.url
            print(f"   📍 URL actual: {current_url[:80]}")

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

            # === PASO 4: Click en cada alumno + tab Inscritas + leer texto ===
            # La propia app React hace el POST interno (Cloudflare lo acepta)
            # Nosotros solo leemos el resultado renderizado con innerText
            
            # Detectar nombres de alumnos en la página
            page_text = page.evaluate("() => document.body.innerText")
            alumno_names = []
            for line in page_text.split("\n"):
                line = line.strip()
                if line and line == line.upper() and 5 < len(line) < 35 and " " in line:
                    if line not in ("BLANCA FERNANDA", "FRANCO ANTONIO"):
                        pass  # Se agrega abajo
                    if not any(x in line for x in ["EXTRAPROGRAMÁTICA", "DEPORTE", "COLEGIO", "COLEGIUM", "COPYRIGHT"]):
                        alumno_names.append(line)
            # Fallback: buscar los que ya conocemos
            if not alumno_names:
                for name in ["BLANCA FERNANDA", "FRANCO ANTONIO"]:
                    if name in page_text:
                        alumno_names.append(name)
            
            # Quitar duplicados preservando orden
            seen = set()
            alumno_names = [n for n in alumno_names if not (n in seen or seen.add(n))]
            print(f"   👦 Alumnos: {alumno_names}")

            for alumno in alumno_names:
                try:
                    # Click en alumno (force=True para ignorar overlays)
                    page.locator(f"text={alumno}").first.click(force=True)
                    time.sleep(4)
                    
                    # Esperar a que desaparezca el overlay bloqueador
                    try:
                        page.wait_for_selector("#bloquearTodo-1", state="hidden", timeout=10000)
                    except Exception:
                        pass
                    time.sleep(2)
                    
                    # Click en tab "Inscritas" (force=True)
                    inscritas_tabs = page.locator("a, button, li, div").filter(has_text=re.compile(r"^Inscritas")).all()
                    if inscritas_tabs:
                        inscritas_tabs[0].click(force=True)
                        time.sleep(5)
                        # Esperar overlay otra vez
                        try:
                            page.wait_for_selector("#bloquearTodo-1", state="hidden", timeout=10000)
                        except Exception:
                            pass
                        time.sleep(2)
                    
                    # Leer texto visible
                    visible_text = page.evaluate("() => document.body.innerText")
                    page.screenshot(path=os.path.join(debug_dir, f"inscritas_{alumno.split()[0].lower()}.png"))
                    
                    # Parsear actividades del texto
                    parsed = _parse_inscritas_text(visible_text, alumno)
                    actividades.extend(parsed)
                    print(f"   ✅ {alumno}: {len(parsed)} actividades")
                    
                except Exception as e:
                    print(f"   ⚠️ Error con {alumno}: {e}")

            print(f"   📊 Total actividades: {len(actividades)}")

        except Exception as e:
            print(f"   ❌ Error extracurriculares: {e}")
            try:
                page.screenshot(path=os.path.join(debug_dir, "error.png"))
            except Exception:
                pass
        finally:
            browser.close()

    return actividades


def _parse_inscritas_text(text: str, alumno: str) -> List[Extracurricular]:
    """
    Parsear texto visible de la página de inscritas.
    
    Formato del texto (innerText):
        Nombre actividad\n
        Inicio: DD/MM/YYYY\n
        Profesor: ...\n
        Fecha de inscripción: DD/MM/YYYY\n
        Costo:\n
        Sin Costo | XX.XXX $ CLP\n
        Horario:\n
        DIA HH:MM-HH:MM\n
        [DIA HH:MM-HH:MM]\n  (puede haber 2 horarios)
    """
    actividades = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Encontrar sección "Pagadas" y "Pendientes de pago"
    # Las actividades están después de "Pagadas" o "No registra..."
    in_section = False
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detectar inicio de actividad: línea que es un nombre
        # (no es un keyword conocido, tiene >5 chars, no es header)
        if (line.startswith("Inicio:") or 
            (i + 1 < len(lines) and lines[i + 1].startswith("Inicio:"))):
            
            # Si la línea actual es "Inicio:", el nombre es la línea anterior
            if line.startswith("Inicio:"):
                nombre = lines[i - 1] if i > 0 else ""
                inicio_line = line
            else:
                nombre = line
                i += 1
                if i >= len(lines):
                    break
                inicio_line = lines[i]

            # Skip si el nombre es un header/keyword
            skip_names = ["Pagadas", "Pendientes de pago", "No registra", "Agregar", 
                         "Aceptadas", "En espera", "Cambiar", "Horario:", "Costo:",
                         "© Copyright", "Políticas", "Condiciones", "Síguenos"]
            if any(nombre.startswith(s) for s in skip_names) or len(nombre) < 4:
                i += 1
                continue

            # Parsear datos de la actividad
            fecha_inicio = ""
            profesor = ""
            costo = ""
            estado = ""
            horarios = []

            # Leer líneas siguientes
            j = i
            while j < len(lines) and j < i + 12:
                l = lines[j]
                if l.startswith("Inicio:"):
                    fecha_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', l)
                    if fecha_match:
                        parts = fecha_match.group(1).split("/")
                        fecha_inicio = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                elif l.startswith("Profesor:"):
                    profesor = l.replace("Profesor:", "").strip()
                elif l == "Sin Costo":
                    costo = "Sin Costo"
                    estado = "sin costo"
                elif "$" in l and "CLP" in l:
                    costo = l.strip()
                    estado = "pagada"
                elif re.match(r'^(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)\s+\d{1,2}:\d{2}', l, re.IGNORECASE):
                    horarios.append(l.strip())
                # Detectar inicio de siguiente actividad
                elif j > i + 1 and not l.startswith("Fecha") and not l.startswith("Costo") and not l.startswith("Horario") and not l.startswith("Profesor") and not l.startswith("Inicio") and not l.startswith("Sin ") and "$" not in l and not re.match(r'^(LUN|MAR|MI|JUE|VIE|SA|DOM)', l, re.IGNORECASE):
                    if len(l) > 5 and l[0].isupper():
                        break
                j += 1

            # Crear una entrada por horario (o una sola si hay múltiples días)
            if nombre and horarios:
                for h in horarios:
                    h_match = re.match(r'(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)\s+(\d{1,2}:\d{2}[-–]\d{1,2}:\d{2})', h, re.IGNORECASE)
                    if h_match:
                        dia = h_match.group(1).upper()
                        horario = h_match.group(2)
                        actividades.append(Extracurricular(
                            nombre=nombre,
                            dia=dia,
                            horario=horario,
                            fecha_inicio=fecha_inicio,
                            profesor=profesor,
                            costo=costo,
                            estado=estado or "pagada",
                            hijo=alumno,
                        ))
            elif nombre and fecha_inicio:
                # Actividad sin horario visible
                actividades.append(Extracurricular(
                    nombre=nombre, dia="", horario="",
                    fecha_inicio=fecha_inicio, profesor=profesor,
                    costo=costo, estado=estado or "pagada", hijo=alumno,
                ))

            i = j
        else:
            i += 1

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
