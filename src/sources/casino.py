"""
Fuente: Casino/Menú del colegio.
Descarga PDF del menú mensual desde la web del colegio y extrae el contenido.
Soporta: Sagrado Corazón, LaFase, Saint George, y cualquier colegio con PDF de menú.
"""

import requests
import re
import io
from typing import Dict, Optional
from datetime import datetime


def fetch_casino_menu(casino_url: str, max_chars: int = 3000) -> Dict:
    """
    Obtiene el menú del casino desde la URL del colegio.
    Busca links a PDF en la página y extrae el texto.
    
    Args:
        casino_url: URL de la página de casino del colegio
        max_chars: Máximo de caracteres a extraer del PDF
        
    Returns:
        Dict con keys: contenido, url_pdf, fecha_descarga
    """
    if not casino_url:
        return {}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    try:
        # 1. Visitar la página del casino
        r = session.get(casino_url, timeout=15)
        r.raise_for_status()
        html = r.text

        # 2. Buscar links a PDFs
        pdf_links = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
        
        if not pdf_links:
            # Intentar buscar iframes con PDF
            iframe_srcs = re.findall(r'<iframe[^>]*src=["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
            pdf_links = iframe_srcs

        if not pdf_links:
            # Buscar links con "menu" o "casino" en el texto
            all_links = re.findall(r'href=["\']([^"\']+)["\']', html)
            pdf_links = [l for l in all_links if 'menu' in l.lower() or 'casino' in l.lower() or 'minuta' in l.lower()]

        if not pdf_links:
            return {"contenido": "", "error": "No se encontraron PDFs de menú"}

        # Hacer URL absoluta
        from urllib.parse import urljoin
        pdf_url = urljoin(casino_url, pdf_links[0])

        # 3. Descargar el PDF
        r_pdf = session.get(pdf_url, timeout=30)
        r_pdf.raise_for_status()

        # 4. Extraer texto del PDF
        text = _extract_pdf_text(r_pdf.content, max_chars)

        return {
            "contenido": text,
            "url_pdf": pdf_url,
            "fecha_descarga": datetime.now().strftime("%Y-%m-%d"),
        }

    except Exception as e:
        return {"contenido": "", "error": str(e)}


def fetch_casino_menu_today(casino_url: str) -> Optional[str]:
    """
    Intenta extraer solo el menú de HOY del PDF mensual.
    
    Returns:
        String con el menú del día, o None si no se puede determinar.
    """
    data = fetch_casino_menu(casino_url)
    if not data.get("contenido"):
        return None

    text = data["contenido"]
    today = datetime.now()
    
    # Buscar el día actual en el texto (formato: "21", "Lunes 21", etc.)
    day_str = str(today.day)
    dias_es = {0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 4: 'viernes'}
    dia_nombre = dias_es.get(today.weekday(), '')

    # Intentar encontrar la sección del día
    lines = text.split('\n')
    found_day = False
    menu_lines = []

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        # Detectar el día actual
        if (day_str in line and (dia_nombre in line_lower or len(line.strip()) < 20)) or \
           (dia_nombre and dia_nombre in line_lower and day_str in line):
            found_day = True
            menu_lines.append(line.strip())
            continue
        
        if found_day:
            # Parar cuando encuentre otro día
            if any(d in line_lower for d in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes'] if d != dia_nombre):
                break
            if line.strip():
                menu_lines.append(line.strip())
            if len(menu_lines) > 8:
                break

    if menu_lines:
        return '\n'.join(menu_lines)
    
    return None


def _extract_pdf_text(pdf_bytes: bytes, max_chars: int = 3000) -> str:
    """Extraer texto de un PDF (intenta pdfplumber, fallback PyPDF2)."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                if len(text) > max_chars:
                    break
            return text[:max_chars]
    except ImportError:
        pass

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            if len(text) > max_chars:
                break
        return text[:max_chars]
    except ImportError:
        pass

    return "Error: No se encontró pdfplumber ni PyPDF2 para leer el PDF"
