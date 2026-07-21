"""
Fuente: Extracurriculares (Colegium).
Acceso via SSO desde SchoolNet → scraping HTML con Playwright (Cloudflare protege el sitio).
"""

import re
from typing import List
from dataclasses import dataclass


@dataclass
class Extracurricular:
    nombre: str
    dia: str
    horario: str
    fecha_inicio: str
    profesor: str
    costo: str
    estado: str  # pagada, sin costo, pendiente


def fetch_extracurriculares(sso_url: str, cookies: dict = None) -> List[Extracurricular]:
    """
    Obtiene las extracurriculares inscritas via SSO URL usando Playwright.
    Cloudflare protege extracurriculares.colegium.com, por lo que requests da 403.
    
    Args:
        sso_url: URL SSO obtenida de SchoolNet (get_extracurriculares_url())
        cookies: Cookies de la sesión SchoolNet (para pasar Cloudflare más rápido)
        
    Returns:
        Lista de extracurriculares inscritas (pagadas + sin costo)
    """
    from playwright.sync_api import sync_playwright
    import time

    actividades = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Agregar cookies de SchoolNet si las tenemos
        if cookies:
            cookie_list = []
            for name, value in cookies.items():
                cookie_list.append({
                    "name": name,
                    "value": value,
                    "domain": ".colegium.com",
                    "path": "/",
                })
            context.add_cookies(cookie_list)
        
        page = context.new_page()

        try:
            # Navegar al SSO URL
            page.goto(sso_url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Detectar alumnos disponibles (avatares/links con nombre en la parte superior)
            alumnos = page.locator("a[href*='#'], .alumno, .student-selector, img[alt]").all()
            alumno_names = []
            
            # Buscar links/divs que contengan nombres de alumnos (típicamente en la nav superior)
            all_links = page.locator("a, div[onclick], span[onclick]").all()
            for link in all_links:
                try:
                    text = link.inner_text().strip()
                    # Los nombres de alumnos son todo mayúsculas y cortos
                    if text and text == text.upper() and 3 < len(text) < 30 and " " in text:
                        if text not in alumno_names and text not in ("ACTIVIDADES", "EXTRAPROGRAMÁTICAS"):
                            alumno_names.append(text)
                except Exception:
                    pass

            if not alumno_names:
                # Fallback: buscar en el HTML directamente
                html_content = page.content()
                # Buscar patrón de nombres de alumnos (MAYUSCULAS antes de tabs)
                name_matches = re.findall(r'>([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})+)<', html_content)
                for name in name_matches:
                    if name not in alumno_names and len(name) < 30:
                        alumno_names.append(name)

            print(f"   📋 Alumnos detectados: {alumno_names}")

            # Para cada alumno, obtener sus actividades
            for alumno_name in alumno_names if alumno_names else [""]:
                # Click en el alumno si hay más de uno
                if alumno_name:
                    try:
                        alumno_link = page.locator(f"text={alumno_name}").first
                        if alumno_link.is_visible():
                            alumno_link.click()
                            time.sleep(2)
                    except Exception:
                        pass

                # Click en tab "Inscritas"
                try:
                    inscritas_tab = page.locator("a, li").filter(has_text="Inscritas").first
                    if inscritas_tab.is_visible():
                        inscritas_tab.click()
                        time.sleep(2)
                except Exception:
                    pass

                # Extraer actividades de las cards visibles
                html = page.content()
                found = _parse_cards_colegium(html, alumno_name)
                actividades.extend(found)

        except Exception as e:
            print(f"   ⚠️ Extracurriculares Playwright: {e}")
        finally:
            browser.close()

    # Filtrar solo las pagadas/sin costo
    return [a for a in actividades if a.estado in ("pagada", "sin costo")]


def _parse_cards_colegium(html: str, alumno: str = "") -> List[Extracurricular]:
    """
    Parsear cards de extracurriculares de Colegium.
    
    Formato de cada card:
    - Nombre de la actividad (ej: "Polideportivo 1° y 2° básico")
    - Inicio: DD/MM/YYYY
    - Profesor: nombre
    - Fecha de inscripción: DD/MM/YYYY
    - Costo: "Sin Costo" o "77.000 $ CLP"
    - Horario: "VIE 15:35-16:55" o "LUN 16:15-17:30"
    """
    actividades = []

    # Limpiar HTML a texto línea por línea
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Buscar patrones de horario para identificar actividades
    # Formato: DIA HH:MM-HH:MM (ej: VIE 15:35-16:55, LUN 16:15-17:30)
    horario_pattern = re.compile(
        r'(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})',
        re.IGNORECASE
    )

    # Buscar cada horario y extraer contexto alrededor (nombre, costo, etc.)
    for i, line in enumerate(lines):
        match = horario_pattern.search(line)
        if match:
            dia = match.group(1).upper()
            hora_inicio = match.group(2)
            hora_fin = match.group(3)
            horario = f"{hora_inicio}-{hora_fin}"

            # Buscar nombre de la actividad (líneas anteriores)
            nombre = ""
            fecha_inicio = ""
            costo = ""
            profesor = ""
            estado = ""

            # Recorrer hacia atrás buscando nombre y datos
            for j in range(max(0, i - 15), i):
                prev = lines[j]
                if prev.startswith("Inicio:") or "Inicio:" in prev:
                    fecha_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', prev)
                    if fecha_match:
                        fecha_inicio = fecha_match.group(1)
                elif "Profesor:" in prev:
                    profesor = prev.replace("Profesor:", "").strip()
                elif "Costo:" in prev or "Sin Costo" in prev:
                    if "Sin Costo" in prev:
                        costo = "Sin Costo"
                        estado = "sin costo"
                    else:
                        costo = prev.replace("Costo:", "").strip()
                        estado = "pagada"
                elif "$" in prev and "CLP" in prev:
                    costo = prev.strip()
                    estado = "pagada"
                elif not nombre and len(prev) > 3 and not prev.startswith("Fecha") and \
                     not prev.startswith("Profesor") and not prev.startswith("Costo") and \
                     not prev.startswith("Horario") and not prev.startswith("Inicio"):
                    # Candidato a nombre de actividad
                    if not re.match(r'^[\d/]+$', prev) and "inscripción" not in prev.lower():
                        nombre = prev

            # Si no encontramos estado, asumir pagada (están bajo "Pagadas")
            if not estado:
                estado = "pagada"

            if nombre:
                actividades.append(Extracurricular(
                    nombre=nombre,
                    dia=dia,
                    horario=horario,
                    fecha_inicio=fecha_inicio,
                    profesor=profesor,
                    costo=costo,
                    estado=estado,
                ))

    # Fallback: buscar con el patrón original si no encontramos nada
    if not actividades:
        actividades = _parse_actividades(html)

    return actividades


def _parse_from_page(page) -> List[Extracurricular]:
    """Intentar extraer datos directamente del DOM con selectores."""
    actividades = []
    try:
        # Buscar cards/rows de actividades
        cards = page.locator(".activity-card, .inscrita-card, tr.activity, .card-body").all()
        for card in cards:
            text = card.inner_text()
            nombre = ""
            dia = ""
            horario = ""
            estado = ""

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                nombre = lines[0]

            for line in lines:
                if re.match(r'^(LUN|MAR|MIE|MIÉ|JUE|VIE|SÁB|SAB|DOM)', line, re.IGNORECASE):
                    parts = line.split()
                    dia = parts[0].upper()
                    horario = " ".join(parts[1:])
                if "pagad" in line.lower():
                    estado = "pagada"
                elif "sin costo" in line.lower():
                    estado = "sin costo"

            if nombre and (dia or horario or estado):
                actividades.append(Extracurricular(
                    nombre=nombre, dia=dia, horario=horario,
                    fecha_inicio="", profesor="", costo="", estado=estado
                ))
    except Exception:
        pass
    return actividades


def _parse_actividades(html: str) -> List[Extracurricular]:
    """Parsear el HTML de extracurriculares para extraer actividades."""
    actividades = []
    
    # Limpiar HTML a texto
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Buscar patrones de actividades
    i = 0
    while i < len(lines):
        # Detectar inicio de actividad por "Inicio:" o patrones de horario
        if i + 1 < len(lines) and ("Inicio:" in lines[i + 1] or re.match(r'^(LUN|MAR|MIE|MIÉ|JUE|VIE)', lines[i + 1], re.IGNORECASE)):
            nombre = lines[i]
            fecha_inicio = ""
            horario = ""
            dia = ""
            costo = ""
            estado = ""
            profesor = ""
            
            # Recorrer líneas siguientes buscando datos
            j = i + 1
            while j < len(lines) and j < i + 15:
                line = lines[j]
                if line.startswith("Inicio:"):
                    fecha_inicio = line.replace("Inicio:", "").strip()
                elif "Profesor:" in line:
                    profesor = line.replace("Profesor:", "").strip()
                elif re.match(r'^(LUN|MAR|MIE|MIÉ|JUE|VIE|SAB|SÁB|DOM)\s', line, re.IGNORECASE):
                    parts = line.split()
                    dia = parts[0].upper()
                    horario = " ".join(parts[1:]) if len(parts) > 1 else ""
                elif "pagad" in line.lower():
                    estado = "pagada"
                elif "sin costo" in line.lower():
                    estado = "sin costo"
                    costo = "Sin Costo"
                elif "pendiente" in line.lower():
                    estado = "pendiente"
                elif "$" in line or "CLP" in line:
                    costo = line.strip()
                # Detectar inicio de siguiente actividad
                if j > i + 2 and ("Inicio:" in line or (j + 1 < len(lines) and "Inicio:" in lines[j + 1])):
                    break
                j += 1
            
            if nombre and len(nombre) > 2 and (horario or fecha_inicio or estado):
                actividades.append(Extracurricular(
                    nombre=nombre,
                    dia=dia,
                    horario=horario,
                    fecha_inicio=fecha_inicio,
                    profesor=profesor,
                    costo=costo,
                    estado=estado,
                ))
            i = j
        else:
            i += 1
    
    return actividades
