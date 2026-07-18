"""Fix: borrar eventos calendario_web y mostrar los re-generados."""
import json, sys, os
sys.path.insert(0, '/opt/monitor-colegio')
os.chdir('/opt/monitor-colegio')

from src.calendar_store import load_calendar, save_calendar

# Mostrar eventos del 27 julio con su hijo asignado
cal = load_calendar()
lun27 = [e for e in cal if e['fecha'] == '2026-07-27']
print(f"Eventos 27 julio ({len(lun27)}):")
for e in lun27:
    print(f"  hijo={e.get('hijo','?'):8} | {e.get('descripcion','')[:60]} | fuente={e.get('fuente','')}")

