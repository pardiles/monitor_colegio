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
from src.sources.lirmi import LirmiClient
from src.sources.lafase import LaFaseClient
from src.sources.extracurriculares import fetch_extracurriculares

S3_BUCKET = "monitor-colegio-config-669294688330"
REGION = "us-east-2"
s3 = boto3.client("s3", region_name=REGION)

# Mapeo de colegios a su plataforma
COLEGIOS = {
    "Colegio del Sagrado Corazón Apoquindo": {"tipo": "schoolnet"},
    "Acuarela Montessori": {"tipo": "cuadernorojo"},
    "Oxford School": {"tipo": "lafase", "url": "https://www.oxfordschool.cl"},
    # Colegios con Lirmi
    "Colegio San Ignacio": {"tipo": "lirmi"},
    "Colegio Tabancura": {"tipo": "lirmi"},
    "Colegio Huelén": {"tipo": "lirmi"},
    # Colegios con LaFase
    "Colegio La Fase": {"tipo": "lafase", "url": "https://lafase.cl"},
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

            # Si ya tenemos extras guardadas en S3, no re-scrappear (solo cambian por semestre)
            existing_extras = []
            try:
                obj = s3.get_object(Bucket=S3_BUCKET, Key=f"config/users/{user_id}.json")
                existing_cfg = json.loads(obj["Body"].read())
                existing_extras = existing_cfg.get("extraprogramaticas", [])
            except Exception:
                pass

            if existing_extras:
                print(f"[SCRAPE] Ya hay {len(existing_extras)} extras guardadas, saltando scrape de extras")
                result["extras"] = existing_extras
            else:
                # Login + extraprogramáticas EN UNA SOLA SESIÓN
                try:
                    extras_raw_dicts = sn.login_and_fetch_extras()
                    for e in extras_raw_dicts:
                        if e.get("dia") and e.get("horario"):
                            hora_salida = e["horario"].split("-")[1] if "-" in e["horario"] else ""
                            result["extras"].append({
                                "nombre": e["nombre"],
                                "dia": e["dia"],
                                "horario": e["horario"],
                                "hijo": e.get("hijo", ""),
                                "hora_salida_real": hora_salida,
                            })
                    print(f"[SCRAPE] {len(result['extras'])} extraprogramáticas")
                except Exception as e:
                    print(f"[SCRAPE] Extras error: {e}")

            # Si login_and_fetch_extras hizo login, sn.cookies y sn.session están listos
            if not (sn.cookies and sn.session):
                # Fallback: login normal si login_and_fetch_extras falló
                if not sn.login():
                    print("[SCRAPE] Login falló")
                    result["error"] = "Login falló. Verifica usuario y contraseña."
                    raise Exception("Login failed")

            print("[SCRAPE] Login OK")

            # Detectar hijos desde asistencia
            try:
                for idx in range(5):
                    try:
                        sn.select_alumno(idx)
                        asist = sn._get("asistencia/index", {"alumno": idx})
                        if not asist or asist.get("error"):
                            break
                        nombre_curso = asist.get("nombreyCurso", "")
                        curso = asist.get("curso", "")
                        link_alumnos = asist.get("linkAlumnos", [])
                        prof_jefe = (asist.get("nombProfJefe", []) or [""])[0]

                        nombre_completo = nombre_curso.split(" - ")[0].strip() if " - " in nombre_curso else ""
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

                        if idx == 0 and len(link_alumnos) > 1:
                            for idx2 in range(1, len(link_alumnos)):
                                sn.select_alumno(idx2)
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
                            break
                    except Exception:
                        break
            except Exception as e:
                print(f"[SCRAPE] Error detectando hijos: {e}")

            # Asignar hijos a extraprogramáticas
            if result["extras"] and result["hijos"]:
                for e in result["extras"]:
                    if not e["hijo"]:
                        e["hijo"] = result["hijos"][0]["nombre"]

        except Exception as e:
            if not result.get("error"):
                print(f"[SCRAPE] Error: {e}")
                result["error"] = str(e)

    elif tipo == "cuadernorojo" and plat_user and plat_pass:
        print("[SCRAPE] Cuaderno Rojo — hijos se detectarán del primer resumen")
        # Cuaderno Rojo no tiene endpoint para listar hijos fácilmente
        # Se poblarán con el primer run diario
        result["hijos"] = []
        result["extras"] = []

    elif tipo == "lirmi" and plat_user and plat_pass:
        print(f"[SCRAPE] Lirmi login...")
        try:
            lirmi = LirmiClient(plat_user, plat_pass)
            if lirmi.login():
                print("[SCRAPE] Lirmi login OK")
                students = lirmi.get_students()
                for student in students:
                    name = student.get("name", student.get("nombre", ""))
                    result["hijos"].append({
                        "nombre": name.split()[0] if name else "Alumno",
                        "nombre_completo": name,
                        "curso": student.get("course", student.get("curso", "")),
                        "profesora_jefe": student.get("teacher", ""),
                        "colegio": colegio_nombre,
                    })
                    print(f"[SCRAPE] Hijo: {name}")

                # Scrape completo de datos
                all_data = lirmi.scrape_all()
                result["scrape_data"] = all_data
                print(f"[SCRAPE] Lirmi: {len(all_data)} tópicos obtenidos")
            else:
                print("[SCRAPE] Lirmi login falló")
                result["error"] = "Login Lirmi falló. Verifica usuario y contraseña."
        except Exception as e:
            print(f"[SCRAPE] Lirmi error: {e}")
            result["error"] = str(e)

    elif tipo == "lafase":
        print(f"[SCRAPE] LaFase scraping...")
        try:
            school_url = col_config.get("url", "https://lafase.cl")
            lafase = LaFaseClient(
                username=plat_user,
                password=plat_pass,
                school_url=school_url,
            )
            lafase.login()
            all_data = lafase.scrape_all()
            result["scrape_data"] = all_data
            print(f"[SCRAPE] LaFase: {len(all_data)} tópicos obtenidos")
        except Exception as e:
            print(f"[SCRAPE] LaFase error: {e}")
            result["error"] = str(e)

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
