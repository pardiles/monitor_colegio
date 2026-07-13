"""
Fuente: SC Info (newsletter semanal del colegio).
URL: https://colegiodelsagradocorazon.cl/scinfos
Requiere Playwright para expandir secciones colapsables.
"""

from playwright.sync_api import sync_playwright
import re
import time
from typing import Dict


SCINFOS_URL = "https://colegiodelsagradocorazon.cl/scinfos"


def fetch_scinfo_latest() -> Dict:
    """
    Scrapea el último SC Info expandiendo todas las secciones.
    Returns dict con url, fecha, contenido.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_default_timeout(30000)

        page.goto(SCINFOS_URL, wait_until="load", timeout=30000)
        time.sleep(4)

        # Expandir secciones colapsables
        toggles = page.query_selector_all("[data-toggle='collapse'], [role='button'], summary")
        for toggle in toggles:
            try:
                toggle.dispatch_event("click")
            except Exception:
                pass
        time.sleep(1)

        for section in ["Noticia Destacada", "A toda la comunidad",
                        "Ciclo Inicial", "Ciclo Básico"]:
            try:
                el = page.query_selector(f"text='{section}'")
                if el:
                    el.dispatch_event("click")
            except Exception:
                pass
        time.sleep(2)

        body_text = page.inner_text("body")

        fecha = ""
        m = re.search(r"(\d{2})\s*·\s*(\d{2})\s*·\s*(\d{4})", body_text)
        if m:
            fecha = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        browser.close()

    contenido = _clean_content(body_text)
    return {"url": SCINFOS_URL, "fecha": fecha, "contenido": contenido}


def _clean_content(text: str) -> str:
    """Limpia el texto eliminando navegación y footer."""
    lines = text.split("\n")
    clean = []
    started = False

    for line in lines:
        s = line.strip()
        if not started and "SC INFO" in s:
            started = True
        if started and "Santa Magdalena Sofía 277" in s:
            break
        if started and s and len(s) > 3:
            clean.append(s)

    return "\n".join(clean)
