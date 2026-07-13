"""
Fuente: Extracurriculares (Colegium).
Acceso via SSO desde SchoolNet → scraping HTML.
"""

import requests
import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class Extracurricular:
    nombre: str
    dia: str
    horario: str
    fecha_inicio: str
    profesor: str
    costo: str
    estado: str  # pagada, sin costo, pendiente


def fetch_extracurriculares(sso_url: str) -> List[Extracurricular]:
    """
    Obtiene las extracurriculares inscritas via SSO URL.
    
    Args:
        sso_url: URL SSO obtenida de SchoolNet
        
    Returns:
        Lista de extracurriculares inscritas
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    })
    
    # Seguir SSO URL para obtener sesión
    r = s.get(sso_url, allow_redirects=True, timeout=15)
    r.raise_for_status()
    
    html = r.text
    actividades = _parse_actividades(html)
    return actividades


def _parse_actividades(html: str) -> List[Extracurricular]:
    """Parsear el HTML de extracurriculares para extraer actividades."""
    actividades = []
    
    # Limpiar HTML a texto
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Buscar patrones de actividades
    # Formato: nombre, luego "Inicio: fecha", "Horario: DIA HH:MM-HH:MM"
    i = 0
    while i < len(lines):
        # Detectar inicio de actividad por "Inicio:"
        if i + 1 < len(lines) and "Inicio:" in lines[i + 1]:
            nombre = lines[i]
            fecha_inicio = ""
            horario = ""
            dia = ""
            costo = ""
            estado = ""
            profesor = ""
            
            # Recorrer líneas siguientes buscando datos
            j = i + 1
            while j < len(lines) and j < i + 12:
                line = lines[j]
                if line.startswith("Inicio:"):
                    fecha_inicio = line.replace("Inicio:", "").strip()
                elif line.startswith("Profesor:"):
                    profesor = line.replace("Profesor:", "").strip()
                elif line.startswith("Horario:"):
                    pass  # El horario viene en la siguiente línea
                elif re.match(r'^(LUN|MAR|MIE|JUE|VIE|SAB|DOM)\s', line):
                    parts = line.split()
                    dia = parts[0]
                    horario = parts[1] if len(parts) > 1 else ""
                elif "Pagada" in line:
                    estado = "pagada"
                elif "Sin Costo" in line:
                    estado = "sin costo"
                    costo = "Sin Costo"
                elif "$" in line or "CLP" in line:
                    costo = line.strip()
                j += 1
            
            if nombre and (horario or fecha_inicio):
                actividades.append(Extracurricular(
                    nombre=nombre,
                    dia=dia,
                    horario=horario,
                    fecha_inicio=fecha_inicio,
                    profesor=profesor,
                    costo=costo,
                    estado=estado,
                ))
            i = j
        else:
            i += 1
    
    return actividades
