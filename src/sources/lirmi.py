"""
Fuente: Lirmi (https://www.lirmi.cl/cl)
Plataforma escolar chilena usada en múltiples colegios.
Login con Playwright → cookie de sesión → requests HTTP.

Datos a extraer:
- Calificaciones
- Asistencia (inasistencias + atrasos)
- Conducta / anotaciones
- Compañeros (nombre, teléfono, dirección, apoderados)
- Extraprogramáticas
- Actividades / eventos
- Pagos / cobranza

TODO: Implementar scraping. Requiere:
1. Obtener credenciales de prueba de un colegio que use Lirmi
2. Inspeccionar endpoints (Network tab) para mapear API interna
3. Implementar login y extracción de datos siguiendo patrón de SchoolNet
"""


class LirmiClient:
    """Cliente para Lirmi que maneja login y consultas."""

    BASE_URL = "https://www.lirmi.cl"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = None

    def login(self) -> bool:
        """Login con Playwright para obtener cookie de sesión."""
        # TODO: Implementar
        raise NotImplementedError("Lirmi scraping pendiente de implementar")

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
