"""
Utilidad: Lectura de PDFs desde múltiples fuentes.
Soporta: URL, bytes, archivo local.
Dependencia: pypdf (liviana, funciona en Lambda).
"""

import os
import re
import requests
from io import BytesIO
from typing import Optional, Dict
import pypdf


def read_pdf_from_url(url: str, cookies: Dict[str, str] = None,
                      headers: Dict[str, str] = None,
                      max_pages: int = 20,
                      max_chars: int = 5000) -> Optional[str]:
    """
    Descarga y extrae texto de un PDF desde una URL.

    Args:
        url: URL del PDF
        cookies: Cookies de sesión (para PDFs protegidos)
        headers: Headers HTTP adicionales
        max_pages: Máximo de páginas a leer
        max_chars: Máximo de caracteres a retornar

    Returns:
        Texto extraído del PDF, o None si falla
    """
    try:
        h = headers or {}
        h.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        r = requests.get(url, cookies=cookies, headers=h, timeout=30)
        r.raise_for_status()

        if "application/pdf" not in r.headers.get("Content-Type", "") and \
           not url.lower().endswith(".pdf"):
            return None

        return read_pdf_from_bytes(r.content, max_pages=max_pages, max_chars=max_chars)
    except Exception as e:
        print(f"   ⚠️ Error leyendo PDF {url}: {e}")
        return None


def read_pdf_from_bytes(data: bytes, max_pages: int = 20,
                        max_chars: int = 5000) -> Optional[str]:
    """
    Extrae texto de un PDF desde bytes en memoria.

    Args:
        data: Contenido del PDF como bytes
        max_pages: Máximo de páginas a leer
        max_chars: Máximo de caracteres a retornar

    Returns:
        Texto extraído, o None si falla
    """
    try:
        reader = pypdf.PdfReader(BytesIO(data))
        pages = reader.pages[:max_pages]
        text_parts = []

        for page in pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())

        full_text = "\n\n".join(text_parts)
        # Limpiar espacios múltiples
        full_text = re.sub(r"[ \t]+", " ", full_text)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)

        return full_text[:max_chars] if full_text else None
    except Exception as e:
        print(f"   ⚠️ Error parseando PDF: {e}")
        return None


def read_pdf_from_file(filepath: str, max_pages: int = 20,
                       max_chars: int = 5000) -> Optional[str]:
    """
    Extrae texto de un archivo PDF local.

    Args:
        filepath: Ruta al archivo PDF
        max_pages: Máximo de páginas a leer
        max_chars: Máximo de caracteres a retornar

    Returns:
        Texto extraído, o None si no existe o falla
    """
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "rb") as f:
            return read_pdf_from_bytes(f.read(), max_pages=max_pages, max_chars=max_chars)
    except Exception as e:
        print(f"   ⚠️ Error leyendo PDF {filepath}: {e}")
        return None


def extract_pdf_urls(html: str, base_url: str = "") -> list:
    """
    Extrae URLs de PDFs de un HTML.

    Args:
        html: Contenido HTML
        base_url: URL base para resolver URLs relativas

    Returns:
        Lista de URLs absolutas a PDFs
    """
    pattern = r'href=["\']([^"\']*\.pdf[^"\']*)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)

    urls = []
    for match in matches:
        if match.startswith("http"):
            urls.append(match)
        elif match.startswith("/"):
            urls.append(base_url.rstrip("/") + match)
        else:
            urls.append(base_url.rstrip("/") + "/" + match)

    return list(set(urls))  # Deduplicar
