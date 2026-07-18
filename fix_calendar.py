"""Agregar entrevistas de Franco y Blanca al calendario persistente."""
import sys, os
sys.path.insert(0, '/opt/monitor-colegio')
os.chdir('/opt/monitor-colegio')

from src.calendar_store import add_event, load_calendar

# Franco: Reunión cierre primer semestre - jueves 23 julio, 11:10-11:40, oficina Miss Isabel
added1 = add_event(
    fecha="2026-07-23",
    descripcion="Reunión cierre Primer Semestre Franco con Subdirectora Isabel Soublette y Profesora Jefe Valentina Mozó. Franco debe asistir.",
    tipo="reunion",
    hijo="franco",
    fuente="email",
    hora="11:10",
    lugar="Oficina de Miss Isabel",
)
print(f"Franco reunión 23/07: {'AGREGADO' if added1 else 'ya existía'}")

# Blanca: Si hay info de su entrevista (sin hora según el usuario)
added2 = add_event(
    fecha="2026-07-22",
    descripcion="Entrevistas de apoderados - Blanca (jornada completa, sin clases)",
    tipo="reunion",
    hijo="blanca",
    fuente="email",
)
print(f"Blanca entrevista 22/07: {'AGREGADO' if added2 else 'ya existía'}")

# Mostrar eventos futuros
cal = load_calendar()
print(f"\nTotal eventos en calendario: {len(cal)}")
future = [e for e in cal if e['fecha'] >= '2026-07-18']
print(f"Eventos futuros: {len(future)}")
for e in sorted(future, key=lambda x: x['fecha']):
    hora = e.get('hora', '')
    lugar = e.get('lugar', '')
    print(f"  {e['fecha']} {hora or ''} | {e['descripcion'][:70]} | hijo={e.get('hijo','')} {'📍'+lugar if lugar else ''}")
