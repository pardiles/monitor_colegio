"""
Fuente: Pronote (https://4170004n.index-education.net/pronote/)
Plataforma de gestión escolar de Index Éducation (Francia).
Usada en liceos franceses de Chile (Alliance Française, Lycée, etc.).
Login con Playwright → cookie de sesión → requests HTTP.

URL base por colegio: https://{instance_id}.index-education.net/pronote/

Datos a extraer:
- Calificaciones (notes)
- Asistencia (absences + retards)
- Conducta / observaciones (vie scolaire)
- Compañeros (liste de classe)
- Emploi du temps (horarios)
- Cahier de textes (tareas/actividades)
- Communication (mensajes internos)
- Pagos (si aplica)

Nota: Pronote tiene una API interna JSON bastante estructurada.
Existe también la librería Python `pronotepy` que puede facilitar la integración.
Ver: https://github.com/bain3/pronotepy

TODO: Implementar scraping. Requiere:
1. Obtener credenciales de prueba (tipo "parent")
2. Evaluar si pronotepy funciona con la instancia chilena
3. Si no, inspeccionar endpoints y replicar con Playwright + requests
"""


class PronoteClient:
    """Cliente para Pronote que maneja login y consultas."""

    def __init__(self, instance_url: str, username: str, password: str):
        """
        Args:
            instance_url: URL de la instancia (ej: https://4170004n.index-education.net/pronote/)
            username: Usuario (apoderado)
            password: Contraseña
        """
        self.instance_url = instance_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = None

    def login(self) -> bool:
        """Login con Playwright o pronotepy para obtener sesión."""
        # TODO: Evaluar pronotepy primero, fallback a Playwright
        raise NotImplementedError("Pronote scraping pendiente de implementar")

    def get_calificaciones(self, alumno: int = 0) -> dict:
        """Obtener calificaciones (notes) por alumno."""
        raise NotImplementedError

    def get_asistencia(self, alumno: int = 0) -> dict:
        """Obtener asistencia (absences + retards)."""
        raise NotImplementedError

    def get_conducta(self, alumno: int = 0) -> dict:
        """Obtener conducta/observaciones (vie scolaire)."""
        raise NotImplementedError

    def get_companeros(self, alumno: int = 0) -> dict:
        """Obtener lista de compañeros de la clase."""
        raise NotImplementedError

    def get_horarios(self, alumno: int = 0) -> dict:
        """Obtener emploi du temps (horario semanal)."""
        raise NotImplementedError

    def get_tareas(self, alumno: int = 0) -> dict:
        """Obtener cahier de textes (tareas y actividades)."""
        raise NotImplementedError

    def get_comunicaciones(self) -> dict:
        """Obtener mensajes internos/comunicaciones."""
        raise NotImplementedError

    def get_pagos(self) -> dict:
        """Obtener pagos pendientes (si aplica)."""
        raise NotImplementedError
