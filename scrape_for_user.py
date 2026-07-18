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

                # Detectar hijos desde agenda (tiene cursos) y compañeros (tiene nombre alumno)
                try:
                    agenda = sn._get("agenda/index")
                    cursos = agenda.get("cursos", [])
                    # cursos es [cantidad, "5-A", "1-C", ...]
                    cursos_list = [c for c in cursos if isinstance(c, str)]
                    print(f"[SCRAPE] Cursos detectados: {cursos_list}")

                    # Intentar obtener nombres desde la página index (tiene selector de alumnos)
                    nombres = []
                    try:
                        index_data = sn._get("index")
                        # Buscar alumnos en la respuesta
                        alumnos = index_data.get("alumnos", [])
                        if alumnos:
                            nombres = [a.get("nombre", "") for a in alumnos]
                        # Alternativa: puede estar en otro campo
                        if not nombres:
                            hijos_data = index_data.get("hijos", [])
                            if hijos_data:
                                nombres = [h.get("nombre", "") for h in hijos_data]
                        if not nombres:
                            # Buscar en cualquier lista que tenga "nombre"
                            for key, val in index_data.items():
                                if isinstance(val, list) and val and isinstance(val[0], dict) and "nombre" in val[0]:
                                    nombres = [v.get("nombre", "") for v in val]
                                    break
                        print(f"[SCRAPE] Nombres desde index: {nombres}")

                        # Extraer actividades/eventos recientes del index para calendario
                        actividades = index_data.get("actividades", []) or index_data.get("eventos", []) or index_data.get("proximos", [])
                        if actividades:
                            result["actividades_recientes"] = actividades[:10]
                            print(f"[SCRAPE] {len(actividades)} actividades recientes desde index")

                        # Guardar raw del index para debug
                        result["_index_keys"] = list(index_data.keys()) if isinstance(index_data, dict) else str(type(index_data))
                    except Exception as e:
                        print(f"[SCRAPE] No se pudieron obtener nombres desde index: {e}")

                    for idx, curso in enumerate(cursos_list):
                        nombre_alumno = nombres[idx] if idx < len(nombres) else f"Hijo {idx+1}"
                        result["hijos"].append({
                            "nombre": nombre_alumno,
                            "nombre_completo": nombre_alumno,
                            "curso": curso,
                            "profesora_jefe": "",
                            "ciclo": "",
                            "colegio": colegio_nombre,
                            "schoolnet_idx": idx,
                        })
                        print(f"[SCRAPE] Hijo {idx}: {nombre_alumno} ({curso})")
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
