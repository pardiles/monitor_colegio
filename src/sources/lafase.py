"""
Fuente: LaFase (https://lafase.cl/)
Plataforma de gestión escolar chilena.
Login con Playwright → cookie de sesión → requests HTTP.

URLs clave (contenido en PDF):
- Calendario escolar: https://lafase.cl/calendario_escolar/
- Extraprogramáticas: https://lafase.cl/vida-del-colegio/actividades-extraprogramaticas/
- Asociación deportiva: https://lafase.cl/vida-del-colegio/asociacion-deportiva/
- Casino/menú: https://lafase.cl/vida-del-colegio/casino/

NOTA: Todos estos recursos son PDFs embebidos o descargables.
Requiere: descargar PDF → extraer texto con PyPDF2/pdfplumber → parsear contenido.

Datos a extraer:
- Calificaciones
- Asistencia (inasistencias + atrasos)
- Conducta / anotaciones
- Compañeros (nombre, teléfono, dirección, apoderados)
- Extraprogramáticas (PDF)
- Actividades / eventos
- Pagos / cobranza
- Casino/menú (PDF)
- Calendario escolar (PDF)
- Asociación deportiva (PDF)

TODO: Implementar scraping. Requiere:
1. Obtener credenciales de prueba de un colegio que use LaFase
2. Scraping de PDFs: descargar → pdfplumber/PyPDF2 → texto → parsear
3. Para datos académicos (notas, asistencia): inspeccionar si LaFase tiene portal web con API interna
"""

import requests
import re
from typing import List, Dict


class LaFaseClient:
    """Cliente para LaFase que maneja login y consultas."""

    BASE_URL = "https://lafase.cl"

    # URLs de PDFs públicos (no requieren login)
    PDF_URLS = {
        "calendario": "https://lafase.cl/calendario_escolar/",
        "extraprogramaticas": "https://lafase.cl/vida-del-colegio/actividades-extraprogramaticas/",
        "deportiva": "https://lafase.cl/vida-del-colegio/asociacion-deportiva/",
        "casino": "https://lafase.cl/vida-del-colegio/casino/",
    }

    def __init__(self, username: str = "", password: str = ""):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

    def login(self) -> bool:
        """Login con Playwright para obtener cookie de sesión."""
        # TODO: Implementar si LaFase tiene portal privado
        raise NotImplementedError("LaFase scraping pendiente de implementar")

    def fetch_pdf_urls(self, page_url: str) -> List[str]:
        """Extraer URLs de PDFs desde una página de LaFase."""
        try:
            r = self.session.get(page_url, timeout=15)
            r.raise_for_status()
            # Buscar links a PDFs en el HTML
            pdf_links = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', r.text, re.IGNORECASE)
            # Hacer URLs absolutas
            from urllib.parse import urljoin
            return [urljoin(page_url, link) for link in pdf_links]
        except Exception:
            return []

    def download_and_parse_pdf(self, pdf_url: str, max_chars: int = 5000) -> str:
        """Descargar un PDF y extraer su texto."""
        try:
            r = self.session.get(pdf_url, timeout=30)
            r.raise_for_status()
            # Intentar con pdfplumber primero, fallback a PyPDF2
            try:
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                        if len(text) > max_chars:
                            break
                    return text[:max_chars]
            except ImportError:
                import PyPDF2
                import io
                reader = PyPDF2.PdfReader(io.BytesIO(r.content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                    if len(text) > max_chars:
                        break
                return text[:max_chars]
        except Exception as e:
            return f"Error: {e}"

    def get_calendario(self) -> Dict:
        """Obtener calendario escolar (desde PDF)."""
        pdfs = self.fetch_pdf_urls(self.PDF_URLS["calendario"])
        if pdfs:
            text = self.download_and_parse_pdf(pdfs[0])
            return {"fuente": "pdf", "url": pdfs[0], "contenido": text}
        return {}

    def get_extraprogramaticas(self) -> Dict:
        """Obtener extraprogramáticas (desde PDF)."""
        pdfs = self.fetch_pdf_urls(self.PDF_URLS["extraprogramaticas"])
        if pdfs:
            text = self.download_and_parse_pdf(pdfs[0])
            return {"fuente": "pdf", "url": pdfs[0], "contenido": text}
        return {}

    def get_casino(self) -> Dict:
        """Obtener menú del casino (desde PDF)."""
        pdfs = self.fetch_pdf_urls(self.PDF_URLS["casino"])
        if pdfs:
            text = self.download_and_parse_pdf(pdfs[0])
            return {"fuente": "pdf", "url": pdfs[0], "contenido": text}
        return {}

    def get_deportiva(self) -> Dict:
        """Obtener info asociación deportiva (desde PDF)."""
        pdfs = self.fetch_pdf_urls(self.PDF_URLS["deportiva"])
        if pdfs:
            text = self.download_and_parse_pdf(pdfs[0])
            return {"fuente": "pdf", "url": pdfs[0], "contenido": text}
        return {}

    def get_calificaciones(self, alumno: int = 0) -> dict:
        """Obtener calificaciones por alumno."""
        raise NotImplementedError

    def get_asistencia(self, alumno: int = 0) -> dict:
        """Obtener asistencia (inasistencias + atrasos)."""
        raise NotImplementedError

    def get_conducta(self, alumno: int = 0) -> dict:
        """Obtener conducta/anotaciones."""
        raise NotImplementedError

    def get_companeros(self, alumno: int = 0) -> dict:
        """Obtener lista de compañeros con datos de contacto."""
        raise NotImplementedError

    def get_pagos(self) -> dict:
        """Obtener pagos/cobranza pendientes."""
        raise NotImplementedError

    def get_comunicaciones(self) -> dict:
        """Obtener comunicaciones/circulares."""
        raise NotImplementedError
