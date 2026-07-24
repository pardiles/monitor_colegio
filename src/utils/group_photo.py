"""
Genera foto de perfil para el grupo Monitor Colegio.
Imagen cuadrada (500x500) con:
  - Fondo azul oscuro
  - "Monitor" (arriba, blanco)
  - "{Colegio}" (medio, cyan)
  - "{Apellido}" (abajo, blanco)
"""

import os

def generate_group_photo(colegio: str, apellido: str, output_path: str = None) -> str:
    """Genera imagen PNG para el grupo WA.
    
    Args:
        colegio: Nombre del colegio (ej: "Sagrado Corazón")
        apellido: Apellido del usuario (ej: "Ardiles")
        output_path: Ruta donde guardar. Si None, usa /tmp/
        
    Returns:
        Path al archivo PNG generado
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # Pillow no instalado — retornar None
        return None

    if not output_path:
        output_path = f"/tmp/group_photo_{apellido.lower()}.png"

    # Crear imagen
    size = 500
    img = Image.new('RGB', (size, size), color=(10, 10, 26))  # Fondo azul oscuro
    draw = ImageDraw.Draw(img)

    # Intentar cargar font (fallback a default)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    # Emoji/icono (📚) como texto
    icon = "📚"
    try:
        # Draw icon placeholder (circle)
        draw.ellipse([200, 50, 300, 150], fill=(79, 195, 247))
        draw.text((220, 65), "M", fill=(10, 10, 26), font=font_large)
    except Exception:
        pass

    # "Monitor" (arriba)
    text_monitor = "Monitor"
    bbox = draw.textbbox((0, 0), text_monitor, font=font_large)
    w = bbox[2] - bbox[0]
    draw.text(((size - w) / 2, 170), text_monitor, fill=(255, 255, 255), font=font_large)

    # Colegio (medio, cyan)
    # Acortar si es muy largo
    if len(colegio) > 20:
        colegio = colegio[:20]
    bbox = draw.textbbox((0, 0), colegio, font=font_medium)
    w = bbox[2] - bbox[0]
    x = max(10, (size - w) / 2)
    draw.text((x, 250), colegio, fill=(79, 195, 247), font=font_medium)

    # Apellido (abajo, blanco)
    bbox = draw.textbbox((0, 0), apellido, font=font_medium)
    w = bbox[2] - bbox[0]
    draw.text(((size - w) / 2, 330), apellido, fill=(255, 255, 255), font=font_medium)

    # Línea decorativa
    draw.line([(100, 420), (400, 420)], fill=(79, 195, 247), width=2)

    # Footer
    footer = "Resúmenes diarios"
    bbox = draw.textbbox((0, 0), footer, font=font_small)
    w = bbox[2] - bbox[0]
    draw.text(((size - w) / 2, 440), footer, fill=(136, 136, 136), font=font_small)

    img.save(output_path, "PNG")
    return output_path
