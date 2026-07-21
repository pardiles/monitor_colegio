"""
Fuente: LaFase (https://lafase.cl/)
Plataforma de gestión escolar chilena.
Login con Playwright → cookie de sesión → requests HTTP.

Busca los 12 tópicos fundamentales:
1. calificaciones ✅ (notas por asignatura)
2. companeros → via lista de curso (si disponible)
3. asistencia ✅ (inasistencias + atrasos)
4. conducta ✅ (libro de clases online)
5. extraprogramaticas ✅ (PDF en web pública)
6. actividades ✅ (calendario escolar PDF)
7. pagos → NO disponible
8. casino ✅ (menú semanal PDF)
9. calendario ✅ (PDF calendario escolar)
10. noticias → web pública
11. comunicaciones ✅ (circulares internas)
12. horarios ✅ (horario del curso)

URLs clave:
- Portal apoderados: https://lafase.cl/portal-apoderados/
- Calendario escolar PDF: https://lafase.cl/calendario_escolar/
- Casino/menú PDF: https://lafase.cl/vida-del-colegio/casino/
- Extraprogramáticas: https://lafase.cl/vida-del-colegio/actividades-extraprogramaticas/

NOTA: Gran parte del contenido está en PDFs embebidos.
Se requiere: descargar PDF → extraer texto con pypdf → parsear contenido.
"""

import requests
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.pdf_reader import read_pdf_from_url, read_pdf_from_bytes, extract_pdf_urls

CHILE_TZ = ZoneInfo("America/Santiago")


class LaFaseClient:
    """Cliente para LaFase que maneja login y consultas."""

    BASE_URL = "https://lafase.cl"
    PORTAL_URL = f"{BASE_URL}/portal-apoderados"

    # URLs públicas con PDFs
    PUBLIC_URLS = {
        "calendario": f"{BASE_URL}/calendario_escolar/",
        "casino": f"{BASE_URL}/vida-del-colegio/casino/",
        "extraprogramaticas": f"{BASE_URL}/vida-del-colegio/actividades-extraprogramaticas/",
        "deportes": f"{BASE_URL}/vida-del-colegio/asociacion-deportiva/",
    }

    def __init__(self, username: str = "", password: str = "", school_url: str = ""):
        self.username = username
        self.password = password
        self.school_url = school_url or self.BASE_URL
        self.session: Optional[requests.Session] = None
        self.cookies: Dict[str, str] = {}
        self.logged_in = False

    def login(self) -> bool:
        """
        Login con Playwright para obtener cookie de sesión.
        Returns True si el login fue exitoso.
        """
        if not self.username or not self.password:
            # Sin credenciales, solo scraping público
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            })
            return True

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(self.PORTAL_URL, wait_until="networkidle")
            time.sleep(1)

            # Buscar formulario de login
            try:
                page.fill('input[name="username"], input[name="user"], input[type="email"]', self.username)
                page.fill('input[name="password"], input[type="password"]', self.password)
                page.click('button[type="submit"], input[type="submit"]')
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(2)
            except Exception as e:
                print(f"   ⚠️ LaFase login: {e}")
                browser.close()
                return False

            # Extraer cookies
            self.cookies = {
                c["name"]: c["value"]
                for c in context.cookies()
            }
            browser.close()

        self._init_session()
        self.logged_in = True
        return True

    def _init_session(self):
        """Inicializar sesión de requests con cookies."""
        self.session = requests.Session()
        for name, value in self.cookies.items():
            self.session.cookies.set(name, value)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        })

    def scrape_public_pdfs(self) -> Dict[str, Any]:
        """
        Scraping de PDFs públicos (no requiere login).
        Busca en las URLs públicas del colegio.
        
        Returns:
            Dict con tópicos extraídos de PDFs.
        """
        if not self.session:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            })

        results = {}

        for topic, url in self.PUBLIC_URLS.items():
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code != 200:
                    continue

                html = r.text
                # Buscar PDFs embebidos o links a PDFs
                pdf_urls = extract_pdf_urls(html, base_url=self.school_url)

                # Buscar iframes con PDFs (Google Docs viewer, etc.)
                iframe_pattern = re.compile(r'<iframe[^>]*src=["\']([^"\']*\.pdf[^"\']*|[^"\']*docs\.google[^"\']*)["\']', re.IGNORECASE)
                for match in iframe_pattern.finditer(html):
                    iframe_url = match.group(1)
                    if "docs.google.com" in iframe_url:
                        # Extraer URL del PDF de Google Docs viewer
                        pdf_match = re.search(r'url=([^&]+)', iframe_url)
                        if pdf_match:
                            from urllib.parse import unquote
                            pdf_urls.append(unquote(pdf_match.group(1)))
                    elif iframe_url.endswith(".pdf"):
                        if not iframe_url.startswith("http"):
                            iframe_url = self.school_url.rstrip("/") + "/" + iframe_url.lstrip("/")
                        pdf_urls.append(iframe_url)

                # Descargar y extraer texto de cada PDF
                topic_content = []
                for pdf_url in pdf_urls[:3]:  # Máximo 3 PDFs por tópico
                    text = read_pdf_from_url(pdf_url, max_chars=3000)
                    if text:
                        topic_content.append({
                            "url": pdf_url,
                            "contenido": text,
                        })

                # Extraer contenido HTML relevante (regex, sin dependencias extra)
                # Remover scripts, estilos, nav, footer
                clean_html = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
                # Extraer texto dentro de <main>, <article>, o div con class content/entry/post
                main_match = re.search(r'<(main|article)[^>]*>(.*?)</\1>', clean_html, re.DOTALL | re.IGNORECASE)
                if not main_match:
                    main_match = re.search(r'<div[^>]*class=["\'][^"\']*(?:content|entry|post)[^"\']*["\'][^>]*>(.*?)</div>', clean_html, re.DOTALL | re.IGNORECASE)
                if main_match:
                    raw_text = main_match.group(2) if main_match.lastindex == 2 else main_match.group(1)
                    # Strip tags
                    text_content = re.sub(r'<[^>]+>', ' ', raw_text)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()[:2000]
                    if len(text_content) > 100:
                        topic_content.append({
                            "url": url,
                            "contenido": text_content,
                        })

                if topic_content:
                    results[topic] = topic_content
                    print(f"   ✅ LaFase {topic}: {len(topic_content)} fuentes")

            except Exception as e:
                print(f"   ⚠️ LaFase {topic}: {e}")

        return results

    def get_calificaciones(self) -> Dict:
        """Obtener calificaciones (requiere login)."""
        if not self.logged_in:
            return {}
        # TODO: Inspeccionar endpoints del portal una vez con credenciales reales
        return {}

    def get_asistencia(self) -> Dict:
        """Obtener asistencia (requiere login)."""
        if not self.logged_in:
            return {}
        return {}

    def get_comunicaciones(self) -> List[Dict]:
        """Obtener circulares/comunicaciones (requiere login)."""
        if not self.logged_in:
            return []
        return []

    def scrape_all(self) -> Dict[str, Any]:
        """
        Ejecutar scraping completo.
        Público (PDFs) + privado (portal, si hay login).
        
        Returns:
            Dict con todos los tópicos encontrados.
        """
        all_data = {}

        # Siempre intentar scraping público de PDFs
        public = self.scrape_public_pdfs()
        all_data.update(public)

        # Si hay login, intentar portal privado
        if self.logged_in:
            cal = self.get_calificaciones()
            if cal:
                all_data["calificaciones"] = cal
            asist = self.get_asistencia()
            if asist:
                all_data["asistencia"] = asist
            comms = self.get_comunicaciones()
            if comms:
                all_data["comunicaciones"] = comms

        return all_data
