"""
Procesador: Genera resúmenes diarios con Claude Haiku.
"""

import anthropic
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

CHILE_TZ = ZoneInfo("America/Santiago")

CONTEXT = """
Hijos:
- FRANCO ANTONIO - 5°A (Profesora jefe: María Valentina Mozó Laso)
- BLANCA FERNANDA - 1°C (Profesora jefe: Andrea Alejandra Ortega García)

Colegio: Colegio del Sagrado Corazón Apoquindo

Alianzas Semana SC 2026:
- Franco (5°A) → Alianza A = MÉXICO (colores naranjo, morado, fucsia)
- Blanca (1°C) → Alianza C = BRASIL (colores verde, amarillo, azul)
(La letra del curso = la letra de la alianza)

Extraprogramáticas (horario normal, se suspenden si hay evento especial):
- Ajedrez: LUN 16:30-17:30 (FRANCO) → sale a las 17:30
- Escalada I: LUN 16:15-17:30 (BLANCA) → sale a las 17:30
- Mini chef II: MIE 13:20-15:15 (BLANCA) → sale a las 15:15
- Polideportivo 1° y 2° básico: VIE 15:35-16:55 (BLANCA) → sale a las 16:55

REGLA HORA DE SALIDA:
- Si tiene extraprogramática: la hora de salida es cuando termina la extra
- Si hay semana especial/alianzas/evento y dice "sin extraprogramáticas": usar hora de salida del colegio ese día
- Si el SC Info o comunicaciones indican salida anticipada, usar esa hora
- SIEMPRE priorizar la info del SC Info sobre los horarios normales
- Franco está citado al Playback (si el SC Info menciona horario especial para Playback, aplicar a Franco)

REGLA SOBRE INFORMACIÓN DEL SC INFO:
- TODA la info relevante del SC Info debe incluirse en el resumen
- Avisos sobre preinscripciones de extraprogramáticas, cambios de personal, actividades deportivas, etc.
- Si hay info de horarios especiales para citados a actividades (Playback, baile, etc.), incluirla como aviso
- No omitir nada que pueda ser accionable para los apoderados
- Incluir noticias que apliquen a los ciclos de los hijos:
  - Franco (5°A): Ciclo Básico (3° a 5°), noticias generales "A toda la comunidad"
  - Blanca (1°C): Ciclo Inicial (PK a 2°), noticias generales "A toda la comunidad"
- Cambios de personal, nuevos encargados, contactos: SIEMPRE incluir (nombre + email si hay)
"""

MORNING_SYSTEM_PROMPT = f"""Eres un asistente que genera briefings matutinos para un apoderado.
{CONTEXT}

Formato:
📋 [Día y fecha]

🏫 HOY - FRANCO (5°A):
• Ramos: [lista]. Sale a las [hora real considerando extras o eventos]
• ⚠️ Prueba/evaluación si tiene hoy
• ⚽ Extraprogramática si tiene hoy (o indicar si está suspendida)

🏫 HOY - BLANCA (1°C):
• Ramos: [lista]. Sale a las [hora real]
• ⚽ Extraprogramática si tiene hoy (o indicar si está suspendida)

📅 ESTA SEMANA:
• [Día]: ⚠️ Prueba [materia] - FRANCO o BLANCA (tema)
• [Día]: 🎭 Actividad especial (indicar por hijo, qué llevar)
• Feriados/días sin clases/salidas anticipadas
• 🗓️ Entrevistas (fecha, hora, lugar, con quién)

🎂 CUMPLEAÑOS:
• Compañero/a de FRANCO o BLANCA - fecha y detalle

📨 PENDIENTES:
• Indicar a quién aplica (Franco/Blanca/ambos)

Reglas:
- SIEMPRE indicar si algo es de Franco o de Blanca
- El SC Info es la fuente más confiable para horarios y actividades de la semana
- Si el SC Info dice "sin extraprogramáticas", NO incluirlas
- Si el SC Info dice salida a las 13:10, usar esa hora (no la normal)
- Las entrevistas son MUY importantes: incluir fecha, hora y lugar
- Máximo 22 líneas
- Español chileno natural
"""

EVENING_SYSTEM_PROMPT = f"""Eres un asistente que genera resúmenes nocturnos para un apoderado. Cubre lo que pasó hoy y prepara para mañana.
{CONTEXT}

Formato:
📬 Resumen del día - [Día y fecha]

📧 COMUNICACIONES NUEVAS:
• Resumen (indicar si aplica a Franco, Blanca o ambos)

💬 GRUPO WA "5° básico A" (FRANCO):
• Resumen de lo relevante

💬 GRUPO WA "Copas 5to Sharks" (FRANCO - deporte):
• Resumen si hay info relevante (partidos, horarios)

💬 GRUPO WA "1C SCA" (BLANCA):
• Resumen de lo relevante

🎂 CUMPLEAÑOS:
• Compañero/a de FRANCO o BLANCA - fecha, lugar, hora, quiénes confirmaron

📝 ANOTACIONES:
• FRANCO: [positiva/negativa] - motivo (profesor)
• BLANCA: [positiva/negativa] - motivo (profesor)

📚 MAÑANA [día] - FRANCO (5°A):
• Ramos: [lista]. Sale a las [hora real]
• ⚠️ Prueba si tiene mañana (materia + qué estudiar)
• ⚽ Extraprogramática si tiene (o "suspendida" si aplica)

📚 MAÑANA [día] - BLANCA (1°C):
• Ramos: [lista]. Sale a las [hora real]
• ⚽ Extraprogramática si tiene (o "suspendida" si aplica)

🗓️ ENTREVISTAS/REUNIONES:
• FRANCO: fecha, hora, lugar, con quién
• BLANCA: fecha, hora, lugar, con quién

🎭 ACTIVIDADES ESPECIALES:
• FRANCO: qué llevar/hacer (disfraz, ropa, materiales)
• BLANCA: qué llevar/hacer

Reglas:
- SIEMPRE separar por hijo (Franco vs Blanca)
- Si mañana es fin de semana, mostrar ramos del lunes
- El SC Info es la fuente principal para horarios y actividades
- Si SC Info dice salida anticipada o sin extras, usar esa info
- Entrevistas: incluir SIEMPRE fecha, hora y lugar
- Omitir secciones vacías
- Máximo 30 líneas
- Español chileno natural
"""


class Summarizer:
    """Genera resúmenes usando Claude Haiku."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"

    def generate_morning_briefing(self, data: Dict[str, Any], is_weekly: bool = False) -> str:
        """Genera el briefing matutino."""
        today = datetime.now(CHILE_TZ)
        
        context = ""
        if is_weekly:
            context = "\nIMPORTANTE: Es el RESUMEN SEMANAL (domingo PM). Incluye el panorama completo de TODA la semana que viene: cada día con sus ramos, pruebas, actividades, extraprogramáticas y horarios de salida para ambos hijos."
        else:
            context = "\nEs un mensaje DIARIO. Solo incluir si hay algo relevante para HOY (prueba, evento, salida especial, entrevista, cumpleaños). Si no hay nada especial hoy, responder solo con: '✅ Día normal sin novedades.' y los ramos/hora de salida."
        
        user_content = f"""Fecha de hoy: {today.strftime('%A %d de %B de %Y')}{context}

Datos disponibles:
{self._format_data(data)}

Genera el briefing matutino."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500 if is_weekly else 1200,
            system=MORNING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

    def generate_evening_summary(self, data: Dict[str, Any], is_weekly: bool = False) -> str:
        """Genera el resumen nocturno."""
        today = datetime.now(CHILE_TZ)
        
        context = ""
        if is_weekly:
            context = "\nIMPORTANTE: Es el RESUMEN SEMANAL (domingo PM). Incluye el panorama completo de TODA la semana que viene día por día: ramos, pruebas, actividades, extraprogramáticas, horarios de salida, entrevistas y todo lo relevante para ambos hijos."
        else:
            context = "\nEs un mensaje DIARIO. Incluir: comunicaciones nuevas del día, resumen de WhatsApp si hay algo relevante, ramos y hora de salida de MAÑANA. Si no hay novedades del día, solo indicar los ramos de mañana."
        
        user_content = f"""Fecha de hoy: {today.strftime('%A %d de %B de %Y')}{context}

Datos del día:
{self._format_data(data)}

Genera el resumen nocturno."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000 if is_weekly else 1500,
            system=EVENING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

    def _format_data(self, data: Dict[str, Any]) -> str:
        """Formatea los datos para el prompt."""
        import json
        sections = []
        high_limit_keys = ("scinfo", "emails", "whatsapp_5A_franco", 
                          "whatsapp_1C_blanca", "whatsapp_sharks_franco")
        for key, value in data.items():
            if value:
                limit = 4000 if key in high_limit_keys else 2000
                value_str = json.dumps(value, indent=2, ensure_ascii=False)[:limit]
                sections.append(f"### {key}\n{value_str}")
        return "\n\n".join(sections)
