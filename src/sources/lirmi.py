"""
Fuente: Lirmi (https://chile.lirmi.com / https://www.lirmi.com/cl)
Plataforma escolar chilena usada en múltiples colegios.
Login con Playwright → cookie de sesión → requests HTTP.

Busca los 12 tópicos fundamentales:
1. calificaciones ✅ (notas por asignatura, promedios)
2. companeros ✅ (nombre, apoderados, contacto)
3. asistencia ✅ (inasistencias + atrasos)
4. conducta ✅ (anotaciones / observaciones)
5. extraprogramaticas → NO disponible en Lirmi
6. actividades ✅ (eventos/calendario)
7. pagos → NO disponible en Lirmi (usa pasarela externa)
8. casino → NO disponible
9. calendario ✅ (evaluaciones programadas)
10. noticias ✅ (comunicaciones/circulares)
11. comunicaciones ✅ (mensajes internos)
12. horarios ✅ (horario semanal del curso)

URLs clave:
- Login: https://chile.lirmi.com/login
- API interna: https://chile.lirmi.com/api/v1/...
- Notas: /api/v1/students/{id}/grades
- Asistencia: /api/v1/students/{id}/attendance
- Calendario: /api/v1/school/calendar
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")


class LirmiClient:
    """Cliente para Lirmi que maneja login y consultas."""

    BASE_URL = "https://chile.lirmi.com"
    LOGIN_URL = f"{BASE_URL}/login"
    API_URL = f"{BASE_URL}/api/v1"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session: Optional[requests.Session] = None
        self.cookies: Dict[str, str] = {}
        self.students: List[Dict] = []
        self.token: str = ""

    def login(self) -> bool:
        """
        Login con Playwright para obtener cookie de sesión y token JWT.
        Returns True si el login fue exitoso.
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Capturar token JWT del localStorage o de respuestas API
            token_found = []

            def handle_response(response):
                if "/api/" in response.url and response.status == 200:
                    auth = response.request.headers.get("authorization", "")
                    if auth.startswith("Bearer "):
                        token_found.append(auth.replace("Bearer ", ""))

            page.on("response", handle_response)

            page.goto(self.LOGIN_URL, wait_until="networkidle")
            time.sleep(1)

            # Completar login
            page.fill('input[name="email"], input[type="email"]', self.username)
            page.fill('input[name="password"], input[type="password"]', self.password)
            page.click('button[type="submit"]')

            try:
                page.wait_for_url("**/dashboard**", timeout=15000)
                time.sleep(3)
            except Exception:
                # Intentar detectar error de login
                try:
                    error = page.query_selector(".alert-danger, .error-message")
                    if error:
                        print(f"   ⚠️ Lirmi login error: {error.text_content()}")
                except Exception:
                    pass
                browser.close()
                return False

            # Extraer cookies
            self.cookies = {
                c["name"]: c["value"]
                for c in context.cookies()
                if "lirmi" in c.get("domain", "")
            }

            # Intentar obtener token del localStorage
            try:
                self.token = page.evaluate("localStorage.getItem('token') || localStorage.getItem('access_token') || ''")
            except Exception:
                pass

            # Usar token capturado de las respuestas
            if not self.token and token_found:
                self.token = token_found[-1]

            browser.close()

        if not self.token and not self.cookies:
            return False

        # Crear sesión de requests
        self._init_session()
        return True

    def _init_session(self):
        """Inicializar sesión de requests con cookies y/o token."""
        self.session = requests.Session()
        for name, value in self.cookies.items():
            self.session.cookies.set(name, value)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _get(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        """GET request a la API de Lirmi."""
        if not self.session:
            return None
        try:
            url = f"{self.API_URL}/{endpoint.lstrip('/')}"
            r = self.session.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            print(f"   ⚠️ Lirmi GET {endpoint}: HTTP {r.status_code}")
            return None
        except Exception as e:
            print(f"   ⚠️ Lirmi GET {endpoint}: {e}")
            return None

    def get_students(self) -> List[Dict]:
        """Obtener lista de alumnos (hijos) del apoderado."""
        data = self._get("parents/students") or self._get("guardian/children")
        if data and isinstance(data, list):
            self.students = data
        elif data and isinstance(data, dict):
            self.students = data.get("data", data.get("students", []))
        return self.students

    def get_calificaciones(self, student_id: str) -> Dict:
        """Obtener calificaciones de un alumno."""
        data = self._get(f"students/{student_id}/grades")
        if not data:
            # Intentar endpoint alternativo
            data = self._get(f"students/{student_id}/qualifications")
        if not data:
            return {}

        # Normalizar formato
        grades = data if isinstance(data, dict) else {"data": data}
        result = {"nombre": [], "pf": [], "promedios": {}}

        subjects = grades.get("data", grades.get("subjects", grades.get("asignaturas", [])))
        if isinstance(subjects, list):
            for subj in subjects:
                name = subj.get("name", subj.get("nombre", subj.get("subject", "")))
                avg = subj.get("average", subj.get("promedio", subj.get("final_grade", "")))
                result["nombre"].append(name)
                result["pf"].append(str(avg) if avg else "")

        return result

    def get_asistencia(self, student_id: str) -> Dict:
        """Obtener registro de asistencia."""
        data = self._get(f"students/{student_id}/attendance")
        if not data:
            return {}

        attendance = data if isinstance(data, dict) else {"data": data}
        result = {"inasistencias": [], "atrasos": []}

        records = attendance.get("data", attendance.get("records", []))
        if isinstance(records, list):
            for record in records:
                status = record.get("status", record.get("estado", ""))
                fecha = record.get("date", record.get("fecha", ""))
                if status in ("absent", "ausente", "inasistente"):
                    result["inasistencias"].append({
                        "fecha": fecha,
                        "asig": record.get("subject", record.get("asignatura", "")),
                    })
                elif status in ("late", "atrasado", "atraso"):
                    result["atrasos"].append({
                        "fecha": fecha,
                        "asig": record.get("subject", record.get("asignatura", "")),
                    })

        return result

    def get_conducta(self, student_id: str) -> Dict:
        """Obtener anotaciones/conducta."""
        data = self._get(f"students/{student_id}/observations")
        if not data:
            data = self._get(f"students/{student_id}/annotations")
        if not data:
            return {"anotaciones": []}

        observations = data if isinstance(data, dict) else {"data": data}
        records = observations.get("data", observations.get("observations", []))

        result = {"anotaciones": []}
        if isinstance(records, list):
            for obs in records[-15:]:  # últimas 15
                result["anotaciones"].append({
                    "fecha": obs.get("date", obs.get("fecha", "")),
                    "motivo": obs.get("description", obs.get("motivo", obs.get("observation", ""))),
                    "profesor": obs.get("teacher", obs.get("profesor", "")),
                    "tipo": obs.get("type", obs.get("tipo", "")),
                })

        return result

    def get_companeros(self, student_id: str) -> Dict:
        """Obtener compañeros del curso."""
        data = self._get(f"students/{student_id}/classmates")
        if not data:
            data = self._get(f"courses/{student_id}/students")
        if not data:
            return {"companeros": []}

        classmates = data if isinstance(data, dict) else {"data": data}
        records = classmates.get("data", classmates.get("students", classmates.get("classmates", [])))

        result = {"companeros": []}
        if isinstance(records, list):
            for c in records[:40]:
                result["companeros"].append({
                    "nombre": c.get("name", c.get("nombre", c.get("full_name", ""))),
                    "telefono": c.get("phone", c.get("telefono", "")),
                    "direccion": c.get("address", c.get("direccion", "")),
                    "nombrepadre": c.get("father_name", c.get("padre", "")),
                    "nombremadre": c.get("mother_name", c.get("madre", "")),
                    "celularpadre": c.get("father_phone", ""),
                    "celularmadre": c.get("mother_phone", ""),
                    "emailpadre": c.get("father_email", ""),
                    "emailmadre": c.get("mother_email", ""),
                })

        return result

    def get_calendario(self, student_id: str) -> List[Dict]:
        """Obtener evaluaciones/eventos programados."""
        data = self._get(f"students/{student_id}/evaluations")
        if not data:
            data = self._get("school/calendar")
        if not data:
            return []

        events = data if isinstance(data, list) else data.get("data", data.get("events", []))
        result = []
        today = datetime.now(CHILE_TZ).strftime("%Y-%m-%d")

        if isinstance(events, list):
            for ev in events:
                fecha = ev.get("date", ev.get("fecha", ""))
                if fecha >= today:
                    result.append({
                        "fecha": fecha,
                        "descripcion": ev.get("title", ev.get("description", ev.get("nombre", ""))),
                        "tipo": ev.get("type", ev.get("tipo", "evaluacion")),
                        "asignatura": ev.get("subject", ev.get("asignatura", "")),
                    })

        return result

    def get_comunicaciones(self) -> List[Dict]:
        """Obtener comunicaciones/circulares."""
        data = self._get("communications") or self._get("messages/inbox")
        if not data:
            return []

        messages = data if isinstance(data, list) else data.get("data", data.get("messages", []))
        result = []

        if isinstance(messages, list):
            for msg in messages[:10]:
                result.append({
                    "fecha": msg.get("date", msg.get("created_at", "")),
                    "asunto": msg.get("subject", msg.get("title", "")),
                    "contenido": msg.get("body", msg.get("content", ""))[:500],
                    "de": msg.get("from", msg.get("sender", "")),
                })

        return result

    def get_horario(self, student_id: str) -> Dict:
        """Obtener horario semanal del alumno."""
        data = self._get(f"students/{student_id}/schedule")
        if not data:
            data = self._get(f"students/{student_id}/timetable")
        if not data:
            return {}

        schedule = data if isinstance(data, dict) else {"data": data}
        return schedule.get("data", schedule)

    def scrape_all(self, hijo_name: str = "") -> Dict[str, Any]:
        """
        Ejecutar scraping completo para todos los hijos.
        
        Returns:
            Dict con todos los tópicos encontrados por hijo.
        """
        if not self.students:
            self.get_students()

        if not self.students:
            print("   ⚠️ Lirmi: no se encontraron alumnos")
            return {}

        all_data = {}

        for student in self.students:
            sid = str(student.get("id", student.get("student_id", "")))
            name = student.get("name", student.get("nombre", student.get("full_name", "unknown")))
            name_key = name.lower().split()[0] if name else "alumno"

            # Filtrar por hijo si se especifica
            if hijo_name and hijo_name.lower() not in name.lower():
                continue

            print(f"   📚 Lirmi scraping: {name}...")

            cal = self.get_calificaciones(sid)
            if cal.get("nombre"):
                all_data[f"calificaciones_{name_key}"] = cal

            asist = self.get_asistencia(sid)
            if asist.get("inasistencias") or asist.get("atrasos"):
                all_data[f"asistencia_{name_key}"] = asist

            cond = self.get_conducta(sid)
            if cond.get("anotaciones"):
                all_data[f"conducta_{name_key}"] = cond

            comp = self.get_companeros(sid)
            if comp.get("companeros"):
                all_data[f"companeros_{name_key}"] = comp

            calendario = self.get_calendario(sid)
            if calendario:
                all_data[f"calendario_{name_key}"] = calendario

            horario = self.get_horario(sid)
            if horario:
                all_data[f"horario_{name_key}"] = horario

        # Comunicaciones (nivel cuenta, no por alumno)
        comunicaciones = self.get_comunicaciones()
        if comunicaciones:
            all_data["comunicaciones"] = comunicaciones

        return all_data
