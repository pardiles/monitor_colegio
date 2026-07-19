"""
Fuente: Oxford School Villarrica (web pública).
URL: https://www.oxfordschool.cl/

Busca los 12 tópicos fundamentales:
1. calificaciones → NO disponible (no tiene plataforma académica web)
2. companeros → NO disponible
3. asistencia → NO disponible
4. conducta → NO disponible
5. extraprogramaticas → Busca en PDFs de materiales/reglamentos
6. actividades → Noticias del RSS
7. pagos → NO disponible
8. casino → Busca link/PDF de casino en la web
9. calendario → Busca link/PDF de calendario en la web
10. noticias ✅ (RSS feed)
11. comunicaciones → Busca en PDFs
12. horarios → Busca en PDFs

No requiere login. Fuentes: RSS feed + PDFs públicos + scraping de links.
"""

import re
import requests
from typing import List, Dict
from datetime import datetime
from xml.etree import ElementTree

from src.utils.pdf_reader import read_pdf_from_url, extract_pdf_urls


BASE_URL = "https://www.oxfordschool.cl"
RSS_URL = f"{BASE_URL}/feed/"

# Páginas con PDFs relevantes
PDF_PAGES = [
    "/materiales-2025/",
    "/documentos-y-protocolos-2024/",
]


def fetch_oxford_noticias(max_noticias: int = 5) -> List[Dict]:
    """
    Obtener noticias del blog/feed RSS de Oxford School.

    Returns:
        Lista de dicts con: titulo, url, fecha, descripcion
    """
    try:
        r = requests.get(RSS_URL, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MonitorColegio/1.0)",
        })
        r.raise_for_status()
    except Exception as e:
        print(f"   ❌ Error obteniendo RSS: {e}")
        return []

    noticias = []
    try:
        root = ElementTree.fromstring(r.content)
        # RSS 2.0: channel > item
        channel = root.find("channel")
        if channel is None:
            return []

        for item in channel.findall("item")[:max_noticias]:
            titulo = item.findtext("title", "").strip()
            url = item.findtext("link", "").strip()
            fecha_str = item.findtext("pubDate", "")
            descripcion = item.findtext("description", "").strip()

            # Limpiar HTML de la descripción
            descripcion = re.sub(r'<[^>]+>', '', descripcion)
            descripcion = re.sub(r'\s+', ' ', descripcion).strip()

            # Parsear fecha RSS
            fecha = ""
            if fecha_str:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(fecha_str)
                    fecha = dt.strftime("%Y-%m-%d")
                except Exception:
                    fecha = fecha_str[:10]

            if titulo:
                noticias.append({
                    "titulo": titulo,
                    "url": url,
                    "fecha": fecha,
                    "descripcion": descripcion[:500],
                })
    except Exception as e:
        print(f"   ❌ Error parseando RSS: {e}")

    return noticias


def fetch_oxford_pdfs(curso: str = "") -> List[Dict]:
    """
    Obtener PDFs relevantes de Oxford School.
    Filtra por curso si se especifica.

    Args:
        curso: Curso del hijo (ej: "4°A" → busca "4basico")

    Returns:
        Lista de dicts con: url, filename, contenido (texto extraído)
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; MonitorColegio/1.0)",
    })

    all_pdfs = []
    for page_path in PDF_PAGES:
        try:
            r = session.get(f"{BASE_URL}{page_path}", timeout=15)
            r.raise_for_status()
            pdf_urls = extract_pdf_urls(r.text, BASE_URL)

            for url in pdf_urls:
                filename = url.split("/")[-1].split("?")[0]

                # Filtrar por curso si se especifica
                if curso:
                    curso_key = _normalize_curso(curso)
                    if curso_key and curso_key not in filename.lower():
                        continue

                all_pdfs.append({"url": url, "filename": filename, "page": page_path})
        except Exception as e:
            print(f"   ⚠️ Error en {page_path}: {e}")

    # Leer contenido de PDFs relevantes (máx 3)
    result = []
    for pdf in all_pdfs[:3]:
        text = read_pdf_from_url(pdf["url"], max_chars=2000)
        if text:
            pdf["contenido"] = text
            result.append(pdf)

    return result


def _normalize_curso(curso: str) -> str:
    """Normalizar curso para buscar en filenames de PDFs.
    Ej: '4°A' → '4basico', '1° medio' → '1medio'
    """
    curso_lower = curso.lower().replace("°", "").replace(" ", "")
    # Mapear: 4a → 4basico, 1medio → 1medio
    m = re.match(r'(\d+)([a-z]?)', curso_lower)
    if m:
        num = m.group(1)
        letra = m.group(2)
        if letra in ('a', 'b', 'c', ''):
            return f"{num}basico"
        elif letra == 'm' or 'medio' in curso_lower:
            return f"{num}medio"
    return curso_lower


def fetch_oxford_all(curso: str = "", max_noticias: int = 5) -> Dict:
    """
    Obtener toda la info disponible de Oxford School.
    Busca los 12 tópicos fundamentales en la web.

    Returns:
        Dict con todos los tópicos encontrados
    """
    result = {
        "noticias": [],
        "pdfs": [],
        "calendario": [],
        "casino": {},
        "extraprogramaticas": [],
        "comunicaciones": [],
        "horarios": {},
        "_errors": [],
    }

    # 1. Noticias (RSS)
    print("   📰 RSS noticias...")
    try:
        result["noticias"] = fetch_oxford_noticias(max_noticias=max_noticias)
        print(f"   ✅ {len(result['noticias'])} noticias")
    except Exception as e:
        result["_errors"].append(f"noticias: {e}")

    # 2. PDFs (materiales, reglamentos, posible calendario/horarios)
    print("   📄 PDFs...")
    try:
        pdfs = fetch_oxford_pdfs(curso=curso)
        result["pdfs"] = pdfs
        print(f"   ✅ {len(pdfs)} PDFs leídos")

        # Clasificar PDFs por tópico (buscar keywords en nombre/contenido)
        for pdf in pdfs:
            fname = pdf.get("filename", "").lower()
            content = pdf.get("contenido", "").lower()
            if any(k in fname for k in ["calendario", "calendar", "fecha"]):
                result["calendario"].append(pdf)
            elif any(k in fname for k in ["casino", "menu", "minuta", "almuerzo"]):
                result["casino"] = {"contenido": pdf.get("contenido", ""), "url": pdf.get("url", "")}
            elif any(k in fname for k in ["taller", "extracurricular", "extra", "deport"]):
                result["extraprogramaticas"].append(pdf)
            elif any(k in fname for k in ["horario", "schedule"]):
                result["horarios"] = {"contenido": pdf.get("contenido", ""), "url": pdf.get("url", "")}
            elif any(k in fname for k in ["circular", "comunicado", "aviso"]):
                result["comunicaciones"].append(pdf)
    except Exception as e:
        result["_errors"].append(f"pdfs: {e}")

    # 3. Buscar links adicionales en la home (auto-discovery)
    print("   🔍 Auto-discovery web...")
    try:
        from src.sources.web_colegio import WebColegioScraper
        scraper = WebColegioScraper(BASE_URL)
        web_data = scraper._auto_discover()
        discovered = web_data.get("_discovered_urls", {})
        if discovered:
            print(f"   ✅ Descubierto: {', '.join(discovered.keys())}")
            # Merge discovered data
            if "calendario" in web_data and not result["calendario"]:
                result["calendario"] = web_data["calendario"] if isinstance(web_data["calendario"], list) else [web_data["calendario"]]
            if "noticias" in web_data and not result["noticias"]:
                result["noticias"] = web_data["noticias"]
    except Exception as e:
        result["_errors"].append(f"auto-discovery: {e}")

    return result
