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
            context = browser.new_context()
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
