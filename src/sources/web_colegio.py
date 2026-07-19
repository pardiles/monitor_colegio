"""
Fuente: Web pública del colegio.
Scraper genérico que busca los 12 tópicos fundamentales en la web de cualquier colegio.

Tópicos a buscar:
1. Calificaciones → generalmente NO están en la web (están en SchoolNet/Lirmi/Pronote)
2. Compañeros → generalmente NO están en la web
3. Asistencia → generalmente NO están en la web
4. Conducta → generalmente NO están en la web
5. Extraprogramáticas/Talleres → SÍ (PDF o HTML con horarios y actividades)
6. Actividades/Eventos → SÍ (noticias, galería, eventos)
7. Pagos → generalmente NO (están en la plataforma)
8. Casino/Menú → SÍ (PDF mensual generalmente)
9. Calendario → SÍ (HTML o PDF con fechas del semestre)
10. Noticias → SÍ (sección noticias/actualidad)
11. Comunicaciones → a veces (circulares en PDF)
12. Horarios → a veces (PDF con horarios por curso)

Este scraper complementa la plataforma académica (SchoolNet, Pronote, etc.)
con la info pública de la web del colegio.
"""

import requests
import re
import io
from typing import Dict, List, Optional
from urllib.parse import urljoin
from datetime import datetime


class WebColegioScraper:
    """Scraper genérico para páginas web de colegios."""

    def __init__(self, base_url: str, urls: Dict[str, str] = None):
        """
        Args:
            base_url: URL base del colegio (ej: https://saintgeorge.cl/)
            urls: Dict con URLs específicas por tópico:
                {
                    "calendario": "https://...",
                    "noticias": "https://...",
                    "casino": "https://...",
                    "talleres": "https://...",
                    "deportiva": "https://...",
                }
        """
        self.base_url = base_url.rstrip("/")
        self.urls = urls or {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def scrape_all(self) -> Dict:
        """Ejecutar scraping de todos los tópicos disponibles."""
        result = {}

        # Casino/Menú
        if self.urls.get("casino"):
            result["casino"] = self._scrape_page(self.urls["casino"], "casino")

        # Calendario
        if self.urls.get("calendario"):
            result["calendario"] = self._scrape_page(self.urls["calendario"], "calendario")

        # Noticias
        if self.urls.get("noticias"):
            result["noticias"] = self._scrape_noticias(self.urls["noticias"])

        # Talleres/Extraprogramáticas
        if self.urls.get("talleres"):
            result["talleres"] = self._scrape_page(self.urls["talleres"], "talleres")

        # Asociación deportiva
        if self.urls.get("deportiva"):
            result["deportiva"] = self._scrape_page(self.urls["deportiva"], "deportiva")

        # Comunicaciones/Circulares
        if self.urls.get("comunicaciones"):
            result["comunicaciones"] = self._scrape_page(self.urls["comunicaciones"], "comunicaciones")

        # Horarios
        if self.urls.get("horarios"):
            result["horarios"] = self._scrape_page(self.urls["horarios"], "horarios")

        # Auto-discovery: buscar links en la home si no se pasaron URLs
        if not self.urls:
            result = self._auto_discover()

        return result

    def _scrape_page(self, url: str, topico: str) -> Dict:
        """Scrapear una página: detecta si tiene PDF, Google Calendar embed, o HTML y extrae contenido."""
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()

            # Detectar Google Calendar embed (iframe)
            gcal_match = re.search(r'src="https://calendar\.google\.com/calendar/embed\?([^"]+)"', r.text)
            if gcal_match or 'calendar.google.com' in r.text:
                # Extraer calendar ID del iframe
                cal_id = None
                id_match = re.search(r'src=["\'][^"\']*calendar\.google\.com[^"\']*[?&]src=([^&"\']+)', r.text)
                if id_match:
                    from urllib.parse import unquote
                    cal_id = unquote(id_match.group(1))
                return {
                    "url": url,
                    "topico": topico,
                    "tipo": "google_calendar",
                    "calendar_id": cal_id,
                    "fecha_scrape": datetime.now().strftime("%Y-%m-%d"),
                    "contenido_html": "",
                    "pdfs": [],
                    "nota": "Google Calendar embebido. Usar Google Calendar API o iCal feed para extraer eventos.",
                }

            # Buscar PDFs en la página
            pdfs = self._find_pdfs(r.text, url)

            # Extraer contenido HTML principal
            html_content = self._extract_main_content(r.text)

            result = {
                "url": url,
                "topico": topico,
                "fecha_scrape": datetime.now().strftime("%Y-%m-%d"),
                "contenido_html": html_content[:3000] if html_content else "",
                "pdfs": [],
            }

            # Descargar y parsear PDFs encontrados (max 3)
            for pdf_url in pdfs[:3]:
                pdf_text = self._download_pdf(pdf_url)
                if pdf_text:
                    result["pdfs"].append({
                        "url": pdf_url,
                        "contenido": pdf_text[:3000],
                    })

            return result

        except Exception as e:
            return {"url": url, "topico": topico, "error": str(e)}

    def _scrape_noticias(self, url: str) -> List[Dict]:
        """Extraer noticias/posts de la web del colegio."""
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            html = r.text

            noticias = []

            # Buscar artículos/posts (patrones comunes en WordPress y otros CMS)
            # Patrón 1: <article> tags
            articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)

            if not articles:
                # Patrón 2: divs con clase post/noticia/entry
                articles = re.findall(r'<div[^>]*class="[^"]*(?:post|noticia|entry|news)[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)

            for art in articles[:10]:
                # Extraer título
                titulo = ""
                title_match = re.search(r'<h[1-4][^>]*>(.*?)</h[1-4]>', art, re.DOTALL)
                if title_match:
                    titulo = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

                # Extraer fecha
                fecha = ""
                date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4})', art, re.IGNORECASE)
                if date_match:
                    fecha = date_match.group(1)

                # Extraer resumen
                resumen = ""
                p_match = re.search(r'<p[^>]*>(.*?)</p>', art, re.DOTALL)
                if p_match:
                    resumen = re.sub(r'<[^>]+>', '', p_match.group(1)).strip()[:200]

                # Extraer link
                link = ""
                link_match = re.search(r'href=["\']([^"\']+)["\']', art)
                if link_match:
                    link = urljoin(url, link_match.group(1))

                if titulo:
                    noticias.append({
                        "titulo": titulo,
                        "fecha": fecha,
                        "resumen": resumen,
                        "url": link,
                    })

            return noticias

        except Exception as e:
            return [{"error": str(e)}]

    def _auto_discover(self) -> Dict:
        """Auto-descubrir secciones relevantes desde la home del colegio."""
        result = {}
        try:
            r = self.session.get(self.base_url, timeout=15)
            r.raise_for_status()
            html = r.text

            # Buscar links que contengan palabras clave
            all_links = re.findall(r'href=["\']([^"\']+)["\']', html)
            keywords = {
                "calendario": ["calendario", "calendar", "fechas", "agenda"],
                "noticias": ["noticias", "news", "actualidad", "novedades", "blog"],
                "casino": ["casino", "menu", "minuta", "almuerzo", "alimentacion"],
                "talleres": ["taller", "extracurricular", "extraprogramat", "cocurricular", "actividades"],
                "deportiva": ["deport", "athletic", "sport"],
                "comunicaciones": ["circular", "comunicacion", "comunicado", "aviso"],
            }

            discovered = {}
            for topico, kws in keywords.items():
                for link in all_links:
                    link_lower = link.lower()
                    if any(kw in link_lower for kw in kws):
                        full_url = urljoin(self.base_url, link)
                        if full_url.startswith("http") and self.base_url.split("//")[1].split("/")[0] in full_url:
                            discovered[topico] = full_url
                            break

            if discovered:
                result["_discovered_urls"] = discovered
                # Scrapear las URLs descubiertas
                for topico, url in discovered.items():
                    if topico == "noticias":
                        result[topico] = self._scrape_noticias(url)
                    else:
                        result[topico] = self._scrape_page(url, topico)

        except Exception as e:
            result["_error"] = str(e)

        return result

    def _find_pdfs(self, html: str, page_url: str) -> List[str]:
        """Encontrar links a PDFs en una página HTML."""
        pdf_links = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
        # También buscar iframes con PDF
        iframe_pdfs = re.findall(r'<iframe[^>]*src=["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
        pdf_links.extend(iframe_pdfs)
        # Hacer URLs absolutas
        return [urljoin(page_url, link) for link in pdf_links]

    def _download_pdf(self, pdf_url: str, max_chars: int = 3000) -> str:
        """Descargar PDF y extraer texto."""
        try:
            r = self.session.get(pdf_url, timeout=30)
            r.raise_for_status()

            # Intentar pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(r.content)) as pdf:
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

            # Fallback PyPDF2
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(r.content))
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

            return ""
        except Exception:
            return ""

    def _extract_main_content(self, html: str) -> str:
        """Extraer contenido principal de HTML (sin nav, footer, scripts)."""
        # Remover scripts, styles, nav, footer, header
        clean = re.sub(r'<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remover tags HTML
        text = re.sub(r'<[^>]+>', '\n', clean)
        # Limpiar espacios
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 3]
        return '\n'.join(lines)
