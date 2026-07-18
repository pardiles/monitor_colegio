"""
Fuente: Cuaderno Rojo (plataforma escolar).
URL: https://www.cuadernorojo.com / https://app.cuadernorojo.com
Login y scraping completo con Playwright (headed via xvfb-run en servidor).

Usado por: Acuarela Montessori (Simón Ardiles Cerda).

NOTA: En el servidor, ejecutar con `xvfb-run python3 ...` para proveer display virtual.
Cloudflare bloquea headless y requests, pero headed con xvfb funciona.
"""

import re
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright

from src.utils.pdf_reader import read_pdf_from_bytes, extract_pdf_urls


LOGIN_URL = "https://www.cuadernorojo.com/users/sign_in"
APP_BASE = "https://app.cuadernorojo.com"
WEB_BASE = "https://www.cuadernorojo.com"


def fetch_cuadernorojo(email: str, password: str,
                       max_comunicados: int = 10) -> Dict:
    """
    Login + obtener comunicados recientes de Cuaderno Rojo.
    Todo dentro de una sesión Playwright (Cloudflare bloquea requests).

    Args:
        email: Email de login
        password: Contraseña
        max_comunicados: Máximo de comunicados a leer en detalle

    Returns:
        Dict con: login_ok, comunicados (lista con asunto, fecha, contenido)
    """
    result = {"login_ok": False, "comunicados": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        # --- LOGIN ---
        page.goto(LOGIN_URL, wait_until="networkidle")
        time.sleep(3)

        body = page.inner_text("body")
        if "Verificación" in body or "challenge" in body.lower():
            print("   ⏳ Esperando Cloudflare challenge...")
            time.sleep(15)

        try:
            page.fill('#user_email', email)
            page.fill('#user_password', password)
            page.click('button[type="submit"]')
        except Exception as e:
            print(f"   ❌ Error llenando formulario: {e}")
            browser.close()
            return result

        try:
            page.wait_for_url("**/releases/**", timeout=15000)
        except Exception:
            time.sleep(8)

        if "sign_in" in page.url:
            print("   ❌ Login falló")
            browser.close()
            return result

        result["login_ok"] = True
        time.sleep(2)

        # --- LISTA DE COMUNICADOS (texto visible de la SPA) ---
        list_text = page.inner_text("body")
        comunicados_list = _parse_from_text(list_text)
        print(f"   📋 {len(comunicados_list)} comunicados en lista")

        # --- DETALLE: click en cada comunicado desde la lista ---
        for i, com in enumerate(comunicados_list[:max_comunicados]):
            try:
                # Volver a la lista
                page.goto(f"{APP_BASE}/releases/received", wait_until="networkidle")
                time.sleep(2)

                # Click en el link del comunicado por texto
                link = page.get_by_text(com["asunto"], exact=True).first
                if link:
                    link.click()
                    time.sleep(3)

                    # Extraer contenido del detalle
                    detail_text = page.inner_text("body")
                    detail_html = page.content()

                    com["contenido"] = _clean_detail(detail_text, com["asunto"])

                    # PDFs adjuntos (filtrar los de T&C de Cuaderno Rojo)
                    pdf_urls = extract_pdf_urls(detail_html, WEB_BASE)
                    # Excluir PDFs genéricos de la plataforma
                    skip_pdfs = ["terminos", "privacidad", "condiciones", "privacy", "terms"]
                    pdf_urls = [u for u in pdf_urls
                                if not any(s in u.lower() for s in skip_pdfs)]
                    pdfs = []
                    for pdf_url in pdf_urls[:2]:
                        filename = pdf_url.split("/")[-1].split("?")[0]
                        try:
                            resp = page.evaluate("""async (url) => {
                                const r = await fetch(url);
                                if (!r.ok) return null;
                                const buf = await r.arrayBuffer();
                                return Array.from(new Uint8Array(buf));
                            }""", pdf_url)
                            if resp:
                                pdf_text = read_pdf_from_bytes(bytes(resp), max_chars=2000)
                                if pdf_text:
                                    pdfs.append({"filename": filename, "contenido": pdf_text})
                        except Exception:
                            pass
                    com["pdfs"] = pdfs
                else:
                    com["contenido"] = ""
                    com["pdfs"] = []
            except Exception as e:
                print(f"   ⚠️ Error en '{com.get('asunto', '?')}': {e}")
                com["contenido"] = ""
                com["pdfs"] = []

        result["comunicados"] = comunicados_list[:max_comunicados]
        browser.close()

    return result


def _parse_from_text(text: str) -> List[Dict]:
    """Parsear comunicados desde el texto visible de la SPA."""
    comunicados = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    date_pattern = r'^(\d{2}/\d{2}/\d{2})$'
    estados_validos = {"CONFIRMADO", "ABIERTO", "PENDIENTE", "LEÍDO"}

    i = 0
    while i < len(lines):
        if i + 2 < len(lines):
            fecha_match = re.match(date_pattern, lines[i + 1])
            if fecha_match and lines[i + 2] in estados_validos:
                asunto = lines[i]
                fecha = lines[i + 1]
                estado = lines[i + 2]

                if asunto in ("ASUNTO", "FECHA DE RECEPCIÓN", "ESTADO"):
                    i += 1
                    continue

                comunicados.append({
                    "id": str(len(comunicados)),
                    "asunto": asunto,
                    "fecha": fecha,
                    "estado": estado,
                })
                i += 3
                continue
        i += 1

    return comunicados


def _clean_detail(text: str, asunto: str = "") -> str:
    """Limpiar el texto del detalle de un comunicado."""
    lines = text.split('\n')
    clean = []
    started = False

    # Palabras que indican fin del contenido real
    stop_words = [
        "NOTIFICADO", "CONFIRMADO", "ABIERTO", "PENDIENTE",
        "Términos y condiciones", "Política de privacidad",
        "Cuaderno Rojo", "Perfil", "Conversaciones",
        "Filas por página", "©",
    ]

    for line in lines:
        s = line.strip()
        if not s:
            continue
        # Empezar después del asunto del comunicado
        if not started and asunto and asunto in s:
            started = True
            continue
        # Fallback: empezar después de "Comunicados" header
        if not started and s == "Comunicados":
            started = True
            continue
        # Parar en footer/navegación
        if started and any(sw in s for sw in stop_words):
            break
        if started and len(s) > 3:
            clean.append(s)

    if not clean:
        # Fallback: tomar todo menos las primeras/últimas líneas (nav)
        all_lines = [l.strip() for l in lines if l.strip() and len(l.strip()) > 5]
        if len(all_lines) > 10:
            clean = all_lines[5:-5]
        else:
            clean = all_lines

    return '\n'.join(clean[:30])
