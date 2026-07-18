"""
Fuente: SC Info (newsletter semanal del colegio).
URL: https://colegiodelsagradocorazon.cl/scinfos
Requiere Playwright para expandir secciones colapsables.
Incluye extracción de PDFs adjuntos.
"""

from playwright.sync_api import sync_playwright
import re
import time
from typing import Dict, List

from src.utils.pdf_reader import read_pdf_from_url, extract_pdf_urls


SCINFOS_URL = "https://colegiodelsagradocorazon.cl/scinfos"
BASE_URL = "https://colegiodelsagradocorazon.cl"


def fetch_scinfo_latest() -> Dict:
    """
    Scrapea el último SC Info expandiendo todas las secciones.
    Returns dict con url, fecha, contenido, pdfs.
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
        page_html = page.content()

        fecha = ""
        m = re.search(r"(\d{2})\s*·\s*(\d{2})\s*·\s*(\d{4})", body_text)
        if m:
            fecha = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        browser.close()

    contenido = _clean_content(body_text)
    pdfs = _extract_and_read_pdfs(page_html)

    return {"url": SCINFOS_URL, "fecha": fecha, "contenido": contenido, "pdfs": pdfs}


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


def _extract_and_read_pdfs(html: str) -> List[Dict]:
    """Extrae URLs de PDFs del HTML y lee su contenido."""
    pdf_urls = extract_pdf_urls(html, BASE_URL)
    pdfs = []

    for url in pdf_urls[:5]:  # Máximo 5 PDFs por SC Info
        # Extraer nombre del archivo de la URL
        filename = url.split("/")[-1].split("?")[0]
        text = read_pdf_from_url(url, max_chars=3000)
        if text:
            pdfs.append({
                "url": url,
                "filename": filename,
                "contenido": text,
            })
            print(f"   📄 PDF: {filename} ({len(text)} chars)")

    return pdfs
