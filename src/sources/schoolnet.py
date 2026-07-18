"""
Fuente: SchoolNet (Colegium).
Login con Playwright → cookie sn3app → requests HTTP.
Secciones: comunicaciones, calificaciones, asistencia, conducta, pagos, compañeros.
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
        sn3data = self.session.cookies.get("sn3data", "")
        if not sn3data:
            return
        # Reemplazar alum=X con el nuevo índice
        import re
        new_val = re.sub(r'alum=\d+', f'alum={idx}', sn3data)
        if new_val == sn3data and 'alum=' not in sn3data:
            new_val = f"alum={idx}&{sn3data}"
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

    def get_calificaciones(self, alumno: int = 0) -> Dict:
        """Obtener calificaciones por alumno (0=primero, 1=segundo)."""
        self.select_alumno(alumno)
        return self._get("calificaciones/index", {"tipocalificacion": "nota", "alumno": alumno})

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
