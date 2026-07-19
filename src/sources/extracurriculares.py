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


def fetch_extracurriculares(sso_url: str) -> List[Extracurricular]:
    """
    Obtiene las extracurriculares inscritas via SSO URL usando Playwright.
    Cloudflare protege extracurriculares.colegium.com, por lo que requests da 403.
    
    Args:
        sso_url: URL SSO obtenida de SchoolNet (get_extracurriculares_url())
        
    Returns:
        Lista de extracurriculares inscritas (solo las "pagadas")
    """
    from playwright.sync_api import sync_playwright
    import time

    actividades = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Navegar al SSO URL (Cloudflare lo deja pasar como browser real)
            page.goto(sso_url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Navegar a la pestaña "Inscritas"
            # La URL directa es extracurriculares.colegium.com/#tabInscritas
            current_url = page.url
            if "#tabInscritas" not in current_url:
                page.goto(current_url.split("#")[0] + "#tabInscritas", wait_until="networkidle", timeout=15000)
                time.sleep(2)

            # Intentar hacer click en tab "Inscritas" si existe
            try:
                tab = page.locator("text=Inscritas").first
                if tab.is_visible():
                    tab.click()
                    time.sleep(2)
            except Exception:
                pass

            # Extraer HTML de la página
            html = page.content()
            actividades = _parse_actividades(html)

            # Si no encontró actividades, intentar extraer de tablas/cards
            if not actividades:
                actividades = _parse_from_page(page)

        except Exception as e:
            print(f"   ⚠️ Extracurriculares Playwright: {e}")
        finally:
            browser.close()

    # Filtrar solo las pagadas
    return [a for a in actividades if a.estado in ("pagada", "sin costo")]


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
