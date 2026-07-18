"""
Scrape fuentes del colegio para un usuario nuevo.
Lee credenciales de S3, scrapea SchoolNet/Cuaderno Rojo, y guarda resultados en S3.

Uso: python3 scrape_for_user.py <user_id>
"""

import os
import sys
import json
import boto3
from dotenv import load_dotenv
load_dotenv()

from src.sources.schoolnet import SchoolNetClient
from src.sources.extracurriculares import fetch_extracurriculares

S3_BUCKET = "monitor-colegio-config-669294688330"
REGION = "us-east-2"
s3 = boto3.client("s3", region_name=REGION)

# Mapeo de colegios a su plataforma
COLEGIOS = {
    "Colegio del Sagrado Corazón Apoquindo": {"tipo": "schoolnet"},
    "Acuarela Montessori": {"tipo": "cuadernorojo"},
    "Oxford School": {"tipo": None},
}


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scrape_for_user.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    print(f"[SCRAPE] Iniciando para {user_id}")

    # Leer credenciales de S3
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=f"scrape/pending/{user_id}.json")
        creds = json.loads(obj["Body"].read())
    except Exception as e:
        print(f"[SCRAPE] Error leyendo credenciales: {e}")
        sys.exit(1)

    plat_user = creds.get("user", "")
    plat_pass = creds.get("pass", "")

    # Leer config del usuario para saber el colegio
    users_file = os.path.join("config", "users.json")
    users = []
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8") as f:
            users = json.load(f)

    user_cfg = next((u for u in users if u["id"] == user_id), None)
    colegio_nombre = ""
    if user_cfg:
        colegio_nombre = user_cfg.get("colegio", {}).get("nombre", "")

    # También buscar en prefill (S3 config)
    if not colegio_nombre:
        # Default: Sagrado Corazón si tiene credenciales SchoolNet
        colegio_nombre = "Colegio del Sagrado Corazón Apoquindo"

    result = {"hijos": [], "extras": [], "colegio": colegio_nombre}

    # Scrape según plataforma
    col_config = COLEGIOS.get(colegio_nombre, {})
    tipo = col_config.get("tipo")

    if tipo == "schoolnet" and plat_user and plat_pass:
        print(f"[SCRAPE] SchoolNet login...")
        try:
            sn = SchoolNetClient(plat_user, plat_pass)
            if sn.login():
                print("[SCRAPE] Login OK")

                # Detectar hijos desde asistencia (tiene nombre completo, curso, profesora jefe, inasistencias con fecha)
                try:
                    for idx in range(5):  # Max 5 hijos
                        try:
                            asist = sn._get("asistencia/index", {"alumno": idx})
                            if not asist or asist.get("error"):
                                break
                            nombre_curso = asist.get("nombreyCurso", "")
                            curso = asist.get("curso", "")
                            link_alumnos = asist.get("linkAlumnos", [])
                            prof_jefe = (asist.get("nombProfJefe", []) or [""])[0]

                            # Nombre: viene en "nombreyCurso" como "FRANCO ANTONIO ARDILES VALENZUELA - 5-A"
                            nombre_completo = nombre_curso.split(" - ")[0].strip() if " - " in nombre_curso else ""
                            # Nombre corto: desde linkAlumnos
                            nombre_corto = link_alumnos[idx] if idx < len(link_alumnos) else nombre_completo.split()[0] if nombre_completo else f"Hijo {idx+1}"

                            result["hijos"].append({
                                "nombre": nombre_corto,
                                "nombre_completo": nombre_completo,
                                "curso": curso,
                                "profesora_jefe": prof_jefe,
                                "ciclo": "",
                                "colegio": colegio_nombre,
                                "schoolnet_idx": idx,
                            })
                            print(f"[SCRAPE] Hijo {idx}: {nombre_corto} ({curso}) - Prof: {prof_jefe}")

                            # Solo necesitamos el primer request para obtener linkAlumnos con todos los nombres
                            if idx == 0 and len(link_alumnos) > 1:
                                # Obtener los demás hijos
                                for idx2 in range(1, len(link_alumnos)):
                                    asist2 = sn._get("asistencia/index", {"alumno": idx2})
                                    if asist2 and not asist2.get("error"):
                                        nc2 = asist2.get("nombreyCurso", "").split(" - ")[0].strip()
                                        c2 = asist2.get("curso", "")
                                        pj2 = (asist2.get("nombProfJefe", []) or [""])[0]
                                        result["hijos"].append({
                                            "nombre": link_alumnos[idx2] if idx2 < len(link_alumnos) else nc2.split()[0],
                                            "nombre_completo": nc2,
                                            "curso": c2,
                                            "profesora_jefe": pj2,
                                            "ciclo": "",
                                            "colegio": colegio_nombre,
                                            "schoolnet_idx": idx2,
                                        })
                                        print(f"[SCRAPE] Hijo {idx2}: {link_alumnos[idx2] if idx2 < len(link_alumnos) else nc2} ({c2}) - Prof: {pj2}")
                                break  # Ya obtuvimos todos
                        except Exception:
                            break
                except Exception as e:
                    print(f"[SCRAPE] Error detectando hijos: {e}")
                except Exception as e:
                    print(f"[SCRAPE] Error detectando hijos: {e}")

                # Extraprogramáticas
                try:
                    sso_url = sn.get_extracurriculares_url()
                    if sso_url:
                        extras_raw = fetch_extracurriculares(sso_url)
                        for e in extras_raw:
                            if e.dia and e.horario:
                                hora_salida = e.horario.split("-")[1] if "-" in e.horario else ""
                                result["extras"].append({
                                    "nombre": e.nombre,
                                    "dia": e.dia,
                                    "horario": e.horario,
                                    "hijo": result["hijos"][0]["nombre"] if result["hijos"] else "",
                                    "hora_salida_real": hora_salida,
                                })
                        print(f"[SCRAPE] {len(result['extras'])} extraprogramáticas")
                except Exception as e:
                    print(f"[SCRAPE] Extras error: {e}")
            else:
                print("[SCRAPE] Login falló")
                result["error"] = "Login falló. Verifica usuario y contraseña."
        except Exception as e:
            print(f"[SCRAPE] Error: {e}")
            result["error"] = str(e)

    elif tipo == "cuadernorojo" and plat_user and plat_pass:
        print("[SCRAPE] Cuaderno Rojo — hijos se detectarán del primer resumen")
        # Cuaderno Rojo no tiene endpoint para listar hijos fácilmente
        # Se poblarán con el primer run diario
        result["hijos"] = []
        result["extras"] = []

    else:
        print(f"[SCRAPE] Sin plataforma para {colegio_nombre}")

    # Guardar resultado en S3
    print(f"[SCRAPE] Guardando resultado: {len(result['hijos'])} hijos, {len(result['extras'])} extras")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"scrape/results/{user_id}.json",
        Body=json.dumps(result, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )

    # Limpiar pending
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=f"scrape/pending/{user_id}.json")
    except Exception:
        pass

    print(f"[SCRAPE] Completado para {user_id}")


if __name__ == "__main__":
    main()
