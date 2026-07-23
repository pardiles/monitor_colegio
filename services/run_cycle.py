#!/usr/bin/env python3
"""
Entry point ligero que ejecuta un ciclo via microservicios.
Reemplaza la ejecución monolítica de main.py.

Uso:
    python services/run_cycle.py morning          # Ciclo AM para todos
    python services/run_cycle.py evening          # Ciclo PM para todos
    python services/run_cycle.py morning pablo_ardiles  # Solo un usuario

Requiere: orchestrator (8083) corriendo.
Fallback: si orchestrator no responde, ejecuta main.py directamente.
"""

import sys
import os
import requests
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8083")


def main():
    if len(sys.argv) < 2:
        print("Uso: python services/run_cycle.py [morning|evening] [user_id]")
        sys.exit(1)

    mode = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    now = datetime.now(CHILE_TZ)

    print(f"[{now.strftime('%H:%M:%S')}] Ciclo {mode}" + (f" para {user_id}" if user_id else " para todos"))

    # Intentar via orchestrator
    try:
        if user_id:
            r = requests.post(f"{ORCHESTRATOR_URL}/run/{user_id}", json={"mode": mode}, timeout=300)
        else:
            r = requests.post(f"{ORCHESTRATOR_URL}/run-all/{mode}", timeout=300)

        if r.status_code == 200:
            result = r.json()
            print(f"[OK] Orchestrator respondió:")
            if "log" in result:
                for line in result["log"]:
                    print(f"  {line}")
            elif "results" in result:
                for uid, res in result["results"].items():
                    status = "✅" if res.get("ok") else "❌"
                    print(f"  {status} {uid}")
            return
        else:
            print(f"[WARN] Orchestrator error {r.status_code}: {r.text[:200]}")
    except requests.ConnectionError:
        print(f"[WARN] Orchestrator no disponible en {ORCHESTRATOR_URL}")
    except Exception as e:
        print(f"[WARN] Orchestrator error: {e}")

    # Fallback: ejecutar main.py directamente
    print("[FALLBACK] Ejecutando main.py directamente...")
    cmd = ["python3", "main.py", mode]
    if user_id:
        cmd.append(user_id)
    result = subprocess.run(cmd, timeout=300)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
