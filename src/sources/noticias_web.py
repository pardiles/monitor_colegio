"""
Fuente: Noticias de la web del colegio.
Scraping HTML (no requiere login).
"""

import requests
import re
from typing import List, Dict
from datetime import datetime


NOTICIAS_URL = "https://colegiodelsagradocorazon.cl/noticias"


def fetch_noticias(max_noticias: int = 10) -> List[Dict]:
    """
    Scrapea las últimas noticias de la web del colegio.
    
    Returns:
        Lista de dicts con: titulo, url, imagen_url
    """
    r = requests.get(NOTICIAS_URL, timeout=15)
    r.raise_for_status()

    noticias = []
    
    # Extraer noticias del HTML
    # Patrón: links a /noticias/slug con texto
    pattern = r'<a[^>]*href="(https://colegiodelsagradocorazon\.cl/noticias/[^"]+)"[^>]*>(.*?)</a>'
    matches = re.findall(pattern, r.text, re.DOTALL)
    
    seen_urls = set()
    for url, text in matches:
        # Limpiar texto
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if clean_text and url not in seen_urls and len(clean_text) > 5:
            seen_urls.add(url)
            noticias.append({
                "titulo": clean_text,
                "url": url,
                "fecha_scrape": datetime.now().strftime("%Y-%m-%d"),
            })
    
    return noticias[:max_noticias]


def fetch_noticia_detalle(url: str) -> str:
    """Obtener el contenido de una noticia específica."""
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    
    # Extraer el contenido principal (simplificado)
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text[:3000]
