"""
Fuente: SchoolNet (Colegium).
Login con Playwright → cookie sn3app → requests HTTP.
Secciones: comunicaciones, calificaciones, asistencia, conducta, pagos, compañeros.

Busca los 12 tópicos fundamentales:
1. calificaciones ✅ (por semestre, con promedios)
2. companeros ✅ (nombre, teléfono, dirección, padres, emails)
3. asistencia ✅ (inasistencias + atrasos con fechas)
4. conducta ✅ (anotaciones)
5. extraprogramaticas ✅ (via SSO, requiere Playwright por Cloudflare)
6. actividades → via calendario del colegio (externo)
7. pagos ✅ (historial + avisos de cobranza)
8. casino → via web del colegio (externo, PDF)
9. calendario → via API JSON del colegio (externo)
10. noticias → via web del colegio (externo)
11. comunicaciones ✅ (circulares internas)
12. horarios → config local (JSON)
"""

import requests
import json
import time
from typing import Dict, Optional, Any
from playwright.sync_api import sync_playwright


class SchoolNetClient:
    """Cliente para SchoolNet que maneja login y consultas."""

    BASE_URL = "https://schoolnet.colegium.com/webapp/es_CL"
    LOGIN_URL = f"{BASE_URL}/login"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session: Optional[requests.Session] = None
        self.cookies: Dict[str, str] = {}

    def login(self) -> bool:
        """
        Login con Playwright para obtener cookie de sesión.
        Returns True si el login fue exitoso.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Proxy residencial si está configurado
            try:
                from src.proxy_config import get_playwright_proxy
                proxy = get_playwright_proxy()
            except Exception:
                proxy = None
            context = browser.new_context(proxy=proxy) if proxy else browser.new_context()
            page = context.new_page()

            page.goto(self.LOGIN_URL, wait_until="networkidle")
            page.fill("#signin_username", self.username)
            page.fill("#signin_password", self.password)
            page.click("#btn_login")

            try:
                page.wait_for_url("**/index**", timeout=15000)
                time.sleep(2)
            except Exception:
                browser.close()
                return False

            # Cerrar modal "contraseña no segura" si aparece
            try:
                cancelar = page.locator("button, a").filter(has_text="Cancelar").first
                if cancelar.is_visible(timeout=3000):
                    cancelar.click()
                    time.sleep(1)
            except Exception:
                pass

            # Extraer cookies
            self.cookies = {
                c["name"]: c["value"]
                for c in context.cookies()
                if "colegium" in c.get("domain", "")
            }
            browser.close()

        # Crear sesión de requests
        self._init_session()
        return True

    def login_and_fetch_extras(self) -> list:
        """
        Login + navegar a extracurriculares EN LA MISMA sesión de browser.
        Esto evita que el SSO URL expire entre el login y el fetch.
        
        Returns:
            Lista de dicts con actividades extraprogramáticas, o [] si falla.
        """
        import re
        
        extras = []
        
        with sync_playwright() as p:
            # Anti-detección: headless=False + stealth
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-CL",
                timezone_id="America/Santiago",
            )
            # Aplicar stealth para bypass Cloudflare
            try:
                from playwright_stealth import Stealth
                stealth = Stealth()
                stealth.apply(context)
            except Exception:
                # Fallback: script manual anti-detección
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}};
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['es-CL', 'es', 'en']});
                """)
            page = context.new_page()

            # 1. Login en SchoolNet
            page.goto(self.LOGIN_URL, wait_until="networkidle")
            page.fill("#signin_username", self.username)
            page.fill("#signin_password", self.password)
            page.click("#btn_login")

            try:
                page.wait_for_url("**/index**", timeout=15000)
                time.sleep(3)  # Esperar a que la sesión se estabilice
            except Exception:
                browser.close()
                return []

            # Cerrar modal "contraseña no segura" si aparece
            try:
                cancelar = page.locator("button, a").filter(has_text="Cancelar").first
                if cancelar.is_visible(timeout=3000):
                    cancelar.click()
                    time.sleep(1)
            except Exception:
                pass

            # Extraer cookies para la sesión de requests
            self.cookies = {
                c["name"]: c["value"]
                for c in context.cookies()
                if "colegium" in c.get("domain", "")
            }
            
            # 2. Navegar a extracurriculares desde SchoolNet (redirect SSO natural)
            self._init_session()
            time.sleep(1)
            
            # Interceptar responses de /datos
            datos_responses = []
            def capture_datos(response):
                if "/datos" in response.url and response.status == 200:
                    try:
                        body = response.text()
                        if len(body) > 50:
                            datos_responses.append(body)
                    except Exception:
                        pass
            page.on("response", capture_datos)
            
            # Navegar al link de extracurriculares dentro de SchoolNet
            # Esto hace el redirect SSO automáticamente en el mismo browser
            print("   🔗 Navegando a extracurriculares via SchoolNet...")
            page.goto(f"{self.BASE_URL}/extracurricularescondor/index", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            
            # Si SchoolNet devolvió JSON (no hizo redirect), obtener URL y navegar
            current_url = page.url
            if "extracurriculares.colegium.com" not in current_url:
                # Leer la URL del response JSON
                try:
                    page_content = page.evaluate("() => document.body.innerText || ''")
                    import json as _json2
                    data = _json2.loads(page_content)
                    sso_url = data.get("url", "")
                except Exception:
                    sso_url = self.get_extracurriculares_url()
                
                if not sso_url:
                    browser.close()
                    return []
                
                print(f"   🔗 SSO URL: {sso_url[:80]}")
                page.goto(sso_url, wait_until="networkidle", timeout=60000)
            
            # Esperar a que la página cargue completamente
            time.sleep(10)
            
            # Si Cloudflare muestra un challenge, esperar a que se resuelva
            try:
                # El challenge de Cloudflare genera un iframe con id "challenge-..."
                # Esperar a que desaparezca o a que la página tenga contenido real
                page.wait_for_function(
                    """() => !document.querySelector('iframe[src*="challenge"]') && document.body.innerText.length > 200""",
                    timeout=15000
                )
            except Exception:
                pass
            time.sleep(3)
            
            # Forzar recarga de datos: el SPA de extracurriculares llama a /datos al init
            # Si no se disparó automáticamente, recargar la página
            if not any(len(r) > 1000 for r in datos_responses):
                print("   🔄 Recargando página para obtener datos...")
                page.reload(wait_until="networkidle", timeout=30000)
                time.sleep(10)
            
            # Esperar /datos con datos reales (más de 1000 chars)
            for _ in range(10):
                if any(len(r) > 1000 for r in datos_responses):
                    break
                time.sleep(2)
            
            print(f"   📍 Landed: {page.url[:60]}")
            print(f"   📦 /datos: {len(datos_responses)} responses, {sum(len(r) for r in datos_responses)} total chars")
            
            # Verificar si la página cargó correctamente (no rate-limited)
            page_text = page.evaluate("() => document.body.innerText || ''")
            if "INTENTE MAS TARDE" in page_text.upper():
                print("   ⚠️ Colegium rate-limited, abortando extras")
                browser.close()
                return []
            
            # Si capturamos /datos, parsear el JSON y hacer POSTs por alumno
            if datos_responses:
                import json as _json
                print(f"   ✅ {len(datos_responses)} responses capturadas, parseando...")
                
                for resp_body in datos_responses:
                    try:
                        datos = _json.loads(resp_body)
                        parsed = self._parse_datos_json(datos)
                        if parsed:
                            extras.extend(parsed)
                    except Exception:
                        pass
                
                # Si obtuvimos UUIDs de alumnos pero no actividades, hacer click real por cada uno
                if not extras and hasattr(self, '_alumno_uuids') and self._alumno_uuids:
                    print(f"   🔄 Click real en alumnos para disparar POST...")
                    for alumno_info in self._alumno_uuids:
                        nombre = alumno_info["nombres"]
                        try:
                            # Remover overlay
                            page.evaluate("() => { document.querySelectorAll('[id*=bloquear]').forEach(el => el.remove()); }")
                            time.sleep(1)
                            
                            # Click REAL con Playwright (simula mouse, no JS) en el nombre del alumno
                            alumno_locator = page.locator(f"text={nombre}").first
                            if alumno_locator.is_visible(timeout=5000):
                                alumno_locator.click(force=True)
                                time.sleep(6)
                            
                            # Remover overlay post-click
                            page.evaluate("() => { document.querySelectorAll('[id*=bloquear]').forEach(el => el.remove()); }")
                            time.sleep(1)
                            
                            # Click REAL en tab Inscritas
                            inscritas_locator = page.locator("a[href='#tabInscritas']").first
                            if inscritas_locator.is_visible(timeout=5000):
                                inscritas_locator.click(force=True)
                                time.sleep(6)
                            
                            # Remover overlay otra vez
                            page.evaluate("() => { document.querySelectorAll('[id*=bloquear]').forEach(el => el.remove()); }")
                            
                            # Esperar a que aparezcan responses con inscritas
                            for _ in range(5):
                                new_responses = [r for r in datos_responses if '"inscritas"' in r]
                                if new_responses:
                                    break
                                time.sleep(2)
                            
                            # Parsear responses capturadas
                            new_responses = [r for r in datos_responses if '"inscritas"' in r]
                            for resp_body in new_responses:
                                try:
                                    act_data = _json.loads(resp_body)
                                    parsed = self._parse_datos_json(act_data)
                                    for e in parsed:
                                        e["hijo"] = nombre.title()
                                    extras.extend(parsed)
                                    print(f"   ✅ {nombre}: {len(parsed)} actividades")
                                except Exception:
                                    pass
                            
                            # Limpiar responses procesadas
                            datos_responses[:] = [r for r in datos_responses if '"inscritas"' not in r]
                            
                            if not new_responses:
                                print(f"   ⚠️ {nombre}: no se capturaron responses de inscritas")
                                text = page.evaluate("() => document.body.innerText")
                                horario_pat = re.compile(r'(LUN|MAR|MI[EÉ]|JUE|VIE)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', re.IGNORECASE)
                                for m in horario_pat.finditer(text):
                                    extras.append({
                                        "nombre": "Actividad",  # No podemos saber el nombre sin más contexto
                                        "dia": m.group(1)[:3].upper(),
                                        "horario": f"{m.group(2)}-{m.group(3)}",
                                        "hijo": nombre.title(),
                                        "hora_salida_real": m.group(3),
                                    })
                                if extras:
                                    print(f"   ✅ {nombre}: {len([e for e in extras if e['hijo'] == nombre.title()])} actividades (from DOM)")
                            
                            time.sleep(2)
                        except Exception as e:
                            print(f"   ⚠️ {nombre}: {e}")
                
                if extras:
                    browser.close()
                    return extras
            
            # Esperar a que carguen los nombres de alumnos (puede demorar 10-20s)
            try:
                page.wait_for_function(
                    """() => {
                        const els = document.querySelectorAll('a, span, div, img');
                        for (const el of els) {
                            const t = (el.textContent || el.alt || '').trim();
                            if (t && t === t.toUpperCase() && t.length > 4 && t.length < 25 
                                && t.includes(' ') && !t.includes('ACTIVIDAD') 
                                && !t.includes('EXTRAPROGRAMÁT') && !t.includes('INTENTE')
                                && !t.includes('PRIORIDAD') && !t.includes('POSTULAR')) {
                                return true;
                            }
                        }
                        return false;
                    }""",
                    timeout=30000
                )
                time.sleep(2)
            except Exception:
                print("   ⚠️ Timeout esperando nombres de alumnos, continuando de todos modos...")
            
            # 4. Detectar alumnos en la página
            try:
                alumno_names = page.evaluate("""() => {
                    const names = [];
                    const exclude = ['ACTIVIDAD', 'EXTRAPROGRAMÁT', 'DEPORTE', 'INTENTE',
                        'RESUMEN', 'INSCRIT', 'ABIERT', 'ESPERA', 'FINALIZ', 'RECHAZ',
                        'POSTULAR', 'ELIMINAR', 'CAMBIAR', 'AGREGAR', 'PAGAD', 'PAGO',
                        'PRIORIDAD', 'DEFINIR', 'PENDIENTE', 'SELECCIONE', 'DESTINO',
                        'ALUMNO', 'CERRAR', 'SESIÓN', 'INICIO', 'CORAZÓN', 'COLEGIO'];
                    document.querySelectorAll('a, span, div, li, img').forEach(el => {
                        const text = el.textContent ? el.textContent.trim() : (el.alt || '');
                        if (text && text === text.toUpperCase() && text.length > 4 && text.length < 25 
                            && text.includes(' ')
                            && !exclude.some(ex => text.includes(ex))) {
                            if (!names.includes(text)) names.push(text);
                        }
                    });
                    return names;
                }""")
            except Exception:
                alumno_names = []
            
            print(f"   👧 Alumnos: {alumno_names}")
            
            # Interceptar respuestas AJAX que contienen datos de actividades
            ajax_responses = []
            
            def handle_response(response):
                """Capturar respuestas JSON que contengan datos de actividades."""
                try:
                    if response.status == 200 and "application/json" in (response.headers.get("content-type") or ""):
                        body = response.text()
                        if body and len(body) > 50 and ("horario" in body.lower() or "inscrit" in body.lower() or "pagad" in body.lower()):
                            ajax_responses.append(body)
                except Exception:
                    pass
            
            page.on("response", handle_response)
            
            for alumno in alumno_names if alumno_names else [""]:
                # Remover overlay bloqueante de Colegium (bloquearTodo-1)
                page.evaluate("""() => {
                    document.querySelectorAll('[id*=bloquear], .loading-overlay, .modal-backdrop').forEach(el => {
                        el.style.display = 'none';
                        el.style.pointerEvents = 'none';
                    });
                }""")
                
                # Click en alumno
                if alumno:
                    try:
                        link = page.locator(f"text={alumno}").first
                        if link.is_visible():
                            link.click(force=True)
                            time.sleep(5)
                            # Remover overlay de nuevo (puede reaparecer después del click)
                            page.evaluate("""() => {
                                document.querySelectorAll('[id*=bloquear], .loading-overlay, .modal-backdrop').forEach(el => {
                                    el.style.display = 'none';
                                    el.style.pointerEvents = 'none';
                                });
                            }""")
                    except Exception:
                        pass
                
                # Click en "Inscritas"
                try:
                    # Remover overlay
                    page.evaluate("() => { document.querySelectorAll('[id*=bloquear]').forEach(el => el.remove()); }")
                    time.sleep(1)
                    tab = page.locator("a").filter(has_text="Inscritas").first
                    if tab.is_visible():
                        tab.click(force=True)
                        time.sleep(5)
                        # Remover overlay post-click
                        page.evaluate("() => { document.querySelectorAll('[id*=bloquear]').forEach(el => el.remove()); }")
                except Exception:
                    pass
                
                # Esperar a que cargue contenido dinámico
                try:
                    page.wait_for_function(
                        """() => document.body.innerText.match(/\\d{1,2}:\\d{2}\\s*[-–]\\s*\\d{1,2}:\\d{2}/)""",
                        timeout=20000
                    )
                    time.sleep(2)
                except Exception:
                    # Intentar click en "Pagadas" sub-tab
                    try:
                        pagadas = page.locator("a, span, h5, h4").filter(has_text="Pagadas").first
                        if pagadas.is_visible():
                            pagadas.click()
                            time.sleep(5)
                            try:
                                page.wait_for_function(
                                    """() => document.body.innerText.match(/\\d{1,2}:\\d{2}\\s*[-–]\\s*\\d{1,2}:\\d{2}/)""",
                                    timeout=15000
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                
                # Extraer texto completo de la página (innerText de todo el body)
                try:
                    full_text = page.evaluate("() => document.body.innerText")
                except Exception:
                    full_text = ""
                
                # Parsear actividades del texto
                lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                
                horario_pattern = re.compile(r'(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', re.IGNORECASE)
                horario_only = re.compile(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})')
                dia_pattern = re.compile(r'\b(LUN|MAR|MI[EÉ]|JUE|VIE)\b', re.IGNORECASE)
                
                for i, line in enumerate(lines):
                    # Primero intentar patrón completo "DIA HH:MM-HH:MM"
                    match = horario_pattern.search(line)
                    if match:
                        dia = match.group(1)[:3].upper()
                        horario = f"{match.group(2)}-{match.group(3)}"
                        hora_fin = match.group(3)
                    else:
                        # Patrón solo horario
                        match2 = horario_only.search(line)
                        if not match2:
                            continue
                        horario = f"{match2.group(1)}-{match2.group(2)}"
                        hora_fin = match2.group(2)
                        # Buscar día en la misma línea o adyacentes
                        dia_m = dia_pattern.search(line)
                        if dia_m:
                            dia = dia_m.group(1)[:3].upper()
                        else:
                            dia = ""
                            for j in range(max(0, i-2), min(len(lines), i+2)):
                                dm = dia_pattern.search(lines[j])
                                if dm:
                                    dia = dm.group(1)[:3].upper()
                                    break
                        if not dia:
                            continue
                    
                    # Normalizar día
                    dia_map = {"MIÉ": "MIE", "SÁB": "SAB"}
                    dia = dia_map.get(dia, dia)
                    
                    # Buscar nombre de la actividad (arriba en las líneas)
                    nombre = ""
                    for j in range(i - 1, max(0, i - 15), -1):
                        prev = lines[j]
                        if len(prev) > 4 and len(prev) < 80 and \
                           not prev.startswith("Fecha") and \
                           not prev.startswith("Profesor") and not prev.startswith("Costo") and \
                           not prev.startswith("Horario") and not prev.startswith("Inicio") and \
                           "inscripción" not in prev.lower() and \
                           not re.match(r'^[\d/$.\s]+$', prev) and \
                           not re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', prev) and \
                           "Sin profesor" not in prev and "Sin Costo" not in prev and \
                           "CLP" not in prev and \
                           prev not in ("Pagadas", "Pendientes de pago", "Horario:", "Horario"):
                            nombre = prev
                            break
                    
                    if nombre:
                        extras.append({
                            "nombre": nombre,
                            "dia": dia,
                            "horario": horario,
                            "hijo": alumno.title() if alumno else "",
                            "hora_salida_real": hora_fin,
                        })
                
                print(f"   📊 {alumno}: {len([e for e in extras if e.get('hijo','').upper() == alumno])} actividades")
            
            # Si no encontramos nada via DOM, intentar parsear respuestas AJAX capturadas
            if not extras and ajax_responses:
                print(f"   🔄 Intentando parsear {len(ajax_responses)} respuestas AJAX...")
                import json as _json
                for resp_text in ajax_responses:
                    try:
                        data = _json.loads(resp_text)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and (item.get("horario") or item.get("schedule")):
                                    extras.append({
                                        "nombre": item.get("nombre", item.get("name", "")),
                                        "dia": item.get("dia", ""),
                                        "horario": item.get("horario", item.get("schedule", "")),
                                        "hijo": "",
                                        "hora_salida_real": "",
                                    })
                    except Exception:
                        pass
            
            browser.close()
        
        return extras

    def _parse_datos_json(self, datos) -> list:
        """Parsear el JSON de /datos de extracurriculares.colegium.com.
        
        El GET /datos devuelve {error: false, result: [{uuid_usuario, nombres, ...}]}
        Después hay que hacer POST /datos con funcion=getUserApplications/inscritas
        para cada alumno para obtener sus actividades.
        
        Pero si datos ya viene con las actividades (capturado del POST), parsear directo.
        """
        import re
        extras = []
        
        if not datos or not isinstance(datos, dict):
            return []
        
        # Caso 1: Response del POST getUserApplications/inscritas
        # Estructura: {inscritas: [{nombre, martes, ma_hora_ini, ma_hora_fin, ...}]}
        if "inscritas" in datos and isinstance(datos["inscritas"], list):
            for act in datos["inscritas"]:
                if not isinstance(act, dict):
                    continue
                nombre = act.get("nombre", "")
                if not nombre:
                    continue
                
                # Mapeo de días: campo booleano + hora_ini + hora_fin
                dias = [
                    ("LUN", "lunes", "lu_hora_ini", "lu_hora_fin"),
                    ("MAR", "martes", "ma_hora_ini", "ma_hora_fin"),
                    ("MIE", "miercoles", "mi_hora_ini", "mi_hora_fin"),
                    ("JUE", "jueves", "ju_hora_ini", "ju_hora_fin"),
                    ("VIE", "viernes", "vi_hora_ini", "vi_hora_fin"),
                    ("SAB", "sabado", "sa_hora_ini", "sa_hora_fin"),
                ]
                
                for dia_code, dia_bool, hora_ini_key, hora_fin_key in dias:
                    if act.get(dia_bool) and act.get(hora_ini_key) and act.get(hora_fin_key):
                        hora_ini = act[hora_ini_key][:5]  # "16:15:00" → "16:15"
                        hora_fin = act[hora_fin_key][:5]
                        extras.append({
                            "nombre": nombre,
                            "dia": dia_code,
                            "horario": f"{hora_ini}-{hora_fin}",
                            "hijo": "",  # Se asigna después
                            "hora_salida_real": hora_fin,
                        })
            return extras
        
        # Caso 2: Response del GET /datos inicial
        # Estructura: {error: false, result: [{uuid_usuario, nombres, ...}]}
        alumnos_data = datos.get("result", [])
        if not isinstance(alumnos_data, list):
            return []
        
        # Guardar UUIDs para hacer POST después
        self._alumno_uuids = []
        for alumno in alumnos_data:
            if isinstance(alumno, dict) and alumno.get("uuid_usuario"):
                self._alumno_uuids.append({
                    "uuid": alumno["uuid_usuario"],
                    "nombres": alumno.get("nombres", ""),
                })
        
        return extras  # Vacío — las actividades se obtienen via POST separado
    
    def _extract_activity(self, act, alumno_name: str, extras: list):
        """Extraer datos de una actividad del JSON."""
        import re
        if not isinstance(act, dict):
            return
        
        nombre = act.get('nombre', act.get('name', act.get('actividad', '')))
        horario_raw = act.get('horario', act.get('schedule', act.get('hora', '')))
        estado = act.get('estado', act.get('status', '')).lower() if act.get('estado') or act.get('status') else 'pagada'
        
        # Solo actividades pagadas/sin costo
        if estado and estado not in ('pagada', 'sin costo', 'inscrita', 'activa', ''):
            return
        
        if not nombre:
            return
        
        # Parsear horario - puede ser "LUN 16:15-17:45" o separado
        dia_pattern = re.compile(r'(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)', re.IGNORECASE)
        time_pattern = re.compile(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})')
        
        if horario_raw:
            # Puede tener múltiples horarios separados por espacio/coma
            entries = re.split(r'[,;]|\s{3,}', str(horario_raw))
            for entry in entries:
                entry = entry.strip()
                dia_m = dia_pattern.search(entry)
                time_m = time_pattern.search(entry)
                if dia_m and time_m:
                    dia = dia_m.group(1)[:3].upper()
                    horario = f"{time_m.group(1)}-{time_m.group(2)}"
                    extras.append({
                        "nombre": nombre,
                        "dia": dia,
                        "horario": horario,
                        "hijo": alumno_name.title() if alumno_name else "",
                        "hora_salida_real": time_m.group(2),
                    })
        else:
            # Buscar dia y horario en campos separados
            dia = act.get('dia', act.get('day', ''))
            hora_inicio = act.get('hora_inicio', act.get('start_time', ''))
            hora_fin = act.get('hora_fin', act.get('end_time', ''))
            if dia and hora_inicio and hora_fin:
                extras.append({
                    "nombre": nombre,
                    "dia": dia[:3].upper(),
                    "horario": f"{hora_inicio}-{hora_fin}",
                    "hijo": alumno_name.title() if alumno_name else "",
                    "hora_salida_real": hora_fin,
                })

    def _init_session(self):
        """Inicializar sesión de requests con las cookies."""
        self.session = requests.Session()
        for name, value in self.cookies.items():
            self.session.cookies.set(name, value)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/html, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/index",
        })

    def select_alumno(self, idx: int):
        """Cambiar el alumno activo modificando la cookie sn3data."""
        import re
        # Buscar la cookie sn3data (puede haber duplicadas por dominio)
        sn3data = None
        for cookie in self.session.cookies:
            if cookie.name == "sn3data":
                sn3data = cookie.value
                break
        if not sn3data:
            return
        # Reemplazar alum=X con el nuevo índice
        new_val = re.sub(r'alum=\d+', f'alum={idx}', sn3data)
        if new_val == sn3data and 'alum=' not in sn3data:
            new_val = f"alum={idx}&{sn3data}"
        # Actualizar la cookie (borrar todas las sn3data y poner la nueva)
        self.session.cookies.set("sn3data", None)
        for cookie in list(self.session.cookies):
            if cookie.name == "sn3data":
                self.session.cookies.clear(cookie.domain, cookie.path, cookie.name)
        self.session.cookies.set("sn3data", new_val, domain="schoolnet.colegium.com")

    def _get(self, endpoint: str, params: Dict = None) -> Any:
        """GET a un endpoint de SchoolNet."""
        if not self.session:
            raise RuntimeError("No hay sesión activa. Llama login() primero.")
        r = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return r.text

    def get_comunicaciones(self) -> Dict:
        """Obtener comunicaciones/circulares del colegio."""
        return self._get("comunicaciones/index")

    def get_calificaciones(self, alumno: int = 0, periodo: int = 1) -> Dict:
        """Obtener calificaciones por alumno y periodo (1=primer semestre, 2=segundo)."""
        self.select_alumno(alumno)
        return self._get("calificaciones/index", {"tipocalificacion": "nota", "alumno": alumno, "periodo": periodo})

    def get_calificaciones_ambos_semestres(self, alumno: int = 0) -> Dict:
        """Obtener calificaciones de ambos semestres. Si periodo=2 devuelve vacío, intenta con periodo=0 (anual)."""
        self.select_alumno(alumno)
        # Intentar 1er semestre
        sem1 = self._get("calificaciones/index", {"tipocalificacion": "nota", "alumno": alumno, "periodo": 1})
        # Intentar 2do semestre
        sem2 = self._get("calificaciones/index", {"tipocalificacion": "nota", "alumno": alumno, "periodo": 2})
        # Intentar periodo 0 (anual/general)
        anual = self._get("calificaciones/index", {"tipocalificacion": "nota", "alumno": alumno, "periodo": 0})

        result = {"semestre_1": sem1, "semestre_2": sem2, "anual": anual}
        # Usar el que tenga datos
        nombres_s1 = sem1.get("nombre", []) if isinstance(sem1, dict) else []
        nombres_s2 = sem2.get("nombre", []) if isinstance(sem2, dict) else []
        nombres_anual = anual.get("nombre", []) if isinstance(anual, dict) else []

        if nombres_s2:
            result["activo"] = sem2
        elif nombres_anual:
            result["activo"] = anual
        elif nombres_s1:
            result["activo"] = sem1
        else:
            result["activo"] = sem1

        return result

    def get_asistencia(self, alumno: int = 0) -> Dict:
        """Obtener asistencia y conducta por alumno."""
        self.select_alumno(alumno)
        return self._get("asistencia/index", {"alumno": alumno})

    def get_conducta(self, alumno: int = 0) -> Dict:
        """Obtener conducta (anotaciones) por alumno."""
        self.select_alumno(alumno)
        return self._get("conducta/index", {"alumno": alumno})

    def get_pagos(self) -> Dict:
        """Obtener historial de pagos."""
        return self._get("pagos/index")

    def get_cobranza(self) -> Dict:
        """Obtener info de cobranza (devuelve URL con JWT)."""
        return self._get("cobranza/index")

    def get_avisos_cobranza(self) -> list:
        """Obtener avisos de cobranza (vencimientos futuros con montos pendientes).
        Llama al endpoint cobranza que devuelve un JWT, luego usa Playwright
        para acceder a sn4.colegium.com (protegido por Cloudflare)."""
        data = self.get_cobranza()
        url = data.get("url", "")
        if not url:
            return []
        try:
            from playwright.sync_api import sync_playwright
            import time

            avisos = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(3)

                # Buscar tab "Avisos de cobranza" y clickear
                try:
                    tab = page.locator("text=Avisos de Cobranza").first
                    if tab.is_visible():
                        tab.click()
                        time.sleep(2)
                except Exception:
                    pass

                # Extraer tabla de avisos
                html = page.content()
                browser.close()

            # Parsear tabla HTML
            import re
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 5:
                    # Limpiar celdas
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip().replace('\n', '').replace('  ', ' ') for c in cells]
                    # Formato típico: N° aviso, Emisión, Vencimiento, Monto Neto, Monto a Pagar
                    try:
                        aviso = {
                            "numero": clean_cells[0],
                            "emision": clean_cells[1],
                            "vencimiento": clean_cells[2],
                            "monto_neto": clean_cells[3].replace('.', '').replace('$', '').strip(),
                            "monto_a_pagar": clean_cells[4].replace('.', '').replace('$', '').strip() if len(clean_cells) > 4 else "0",
                        }
                        # Solo incluir si tiene vencimiento válido
                        if aviso["vencimiento"] and '/' in aviso["vencimiento"]:
                            avisos.append(aviso)
                    except (IndexError, ValueError):
                        pass

            return avisos

        except Exception as e:
            print(f"   ⚠️ Error avisos cobranza: {e}")
            return []

    def get_companeros(self, alumno: int = 0) -> Dict:
        """Obtener lista de compañeros (incluye cumpleaños)."""
        self.select_alumno(alumno)
        return self._get("companeros/index", {"alumno": alumno})

    def get_agenda(self) -> Dict:
        """Obtener agenda."""
        return self._get("agenda/index")

    def get_informes(self) -> Dict:
        """Obtener informes disponibles."""
        return self._get("informes/index")

    def get_salud(self, alumno: int = 0) -> Dict:
        """Obtener visitas a enfermería por alumno."""
        self.select_alumno(alumno)
        return self._get("salud/index", {"alumno": alumno})

    def get_extracurriculares_url(self) -> str:
        """Obtener URL SSO para extracurriculares."""
        data = self._get("extracurricularescondor/index")
        return data.get("url", "")
