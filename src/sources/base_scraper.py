"""
Base Scraper — Interfaz obligatoria para todos los scrapers.

REGLA: Todo scraper DEBE buscar los 12 tópicos fundamentales.
Si un tópico no está disponible en la plataforma/web, devolver lista/dict vacío.
Pero SIEMPRE intentar buscarlo (en la página, en PDFs, en links internos).

Tópicos obligatorios:
1.  calificaciones    — notas por asignatura, promedios
2.  companeros        — nombre, teléfono, dirección, padre, madre, email
3.  asistencia        — inasistencias con fechas + atrasos con fechas
4.  conducta          — anotaciones con fecha, motivo, profesor
5.  extraprogramaticas — nombre, día, horario, estado, profesor
6.  actividades       — eventos con fecha, descripción, lugar
7.  pagos             — historial + pendientes con vencimiento y monto
8.  casino            — menú del día o semanal (generalmente PDF)
9.  calendario        — evaluaciones, feriados, reuniones, salidas anticipadas
10. noticias          — últimas publicaciones de la web del colegio
11. comunicaciones    — circulares, avisos oficiales
12. horarios          — ramos por día + hora de salida por curso
"""

from typing import Dict, List, Any


class BaseScraper:
    """Interfaz base que todos los scrapers deben implementar."""

    def __init__(self, **kwargs):
        self.results = {
            "calificaciones": [],
            "companeros": [],
            "asistencia": {},
            "conducta": [],
            "extraprogramaticas": [],
            "actividades": [],
            "pagos": {},
            "casino": {},
            "calendario": [],
            "noticias": [],
            "comunicaciones": [],
            "horarios": {},
            "_errors": [],  # Errores encontrados al buscar tópicos
            "_source": "",  # Nombre de la fuente (SchoolNet, Pronote, etc.)
        }

    def scrape_all(self) -> Dict[str, Any]:
        """Ejecutar scraping de TODOS los tópicos. Devuelve dict con resultados."""
        self.results["_source"] = self.__class__.__name__

        # Cada método intenta buscar su tópico y guarda error si falla
        for topic, method in [
            ("calificaciones", self.get_calificaciones),
            ("companeros", self.get_companeros),
            ("asistencia", self.get_asistencia),
            ("conducta", self.get_conducta),
            ("extraprogramaticas", self.get_extraprogramaticas),
            ("actividades", self.get_actividades),
            ("pagos", self.get_pagos),
            ("casino", self.get_casino),
            ("calendario", self.get_calendario),
            ("noticias", self.get_noticias),
            ("comunicaciones", self.get_comunicaciones),
            ("horarios", self.get_horarios),
        ]:
            try:
                data = method()
                if data:
                    self.results[topic] = data
            except NotImplementedError:
                self.results["_errors"].append(f"{topic}: no implementado")
            except Exception as e:
                self.results["_errors"].append(f"{topic}: {str(e)[:100]}")

        return self.results

    # --- MÉTODOS A IMPLEMENTAR POR CADA SCRAPER ---

    def get_calificaciones(self) -> List[Dict]:
        """Notas por asignatura, promedios parciales y finales."""
        return []

    def get_companeros(self) -> List[Dict]:
        """Lista de compañeros con nombre, teléfono, dirección, padres, emails."""
        return []

    def get_asistencia(self) -> Dict:
        """Inasistencias con fechas + atrasos con fechas."""
        return {}

    def get_conducta(self) -> List[Dict]:
        """Anotaciones con fecha, motivo, profesor."""
        return []

    def get_extraprogramaticas(self) -> List[Dict]:
        """Talleres/actividades con nombre, día, horario, estado, profesor."""
        return []

    def get_actividades(self) -> List[Dict]:
        """Eventos con fecha, descripción, lugar, curso afectado."""
        return []

    def get_pagos(self) -> Dict:
        """Historial de pagos + pendientes con vencimiento y monto."""
        return {}

    def get_casino(self) -> Dict:
        """Menú del día o semanal (contenido de PDF si aplica)."""
        return {}

    def get_calendario(self) -> List[Dict]:
        """Evaluaciones, feriados, reuniones, salidas anticipadas."""
        return []

    def get_noticias(self) -> List[Dict]:
        """Últimas publicaciones de la web del colegio."""
        return []

    def get_comunicaciones(self) -> List[Dict]:
        """Circulares, avisos oficiales del colegio."""
        return []

    def get_horarios(self) -> Dict:
        """Ramos por día + hora de salida por curso."""
        return {}
