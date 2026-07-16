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

Régimen de custodia (semana por medio):
- Semanas PARES (14 jul, 28 jul, 11 ago...): ANGELA tiene los niños (desde lunes PM hasta martes AM siguiente, los deja en el colegio)
- Semanas IMPARES (21 jul, 4 ago, 18 ago...): PABLO tiene los niños (desde martes PM, los busca al colegio, hasta lunes AM siguiente, los deja en el colegio)
- VACACIONES DE INVIERNO: 1ra semana con Pablo, 2da semana con Angela
- VACACIONES DE VERANO: Régimen base hasta 31 dic. Enero: 2 primeras semanas Pablo, 2 siguientes Angela. Febrero: 2 primeras semanas Pablo, 2 siguientes Angela (hasta entrada a clases en marzo)
- FIESTAS PATRIAS (18 sept): Se alternan año a año. 2026 le toca a ANGELA (fechas según SC Info)
- NAVIDAD (24-25 dic): Se alternan año a año. 2026 le toca a PABLO
- AÑO NUEVO (31 dic - 1 ene): Se alternan año a año. 2026 le toca a ANGELA
- PENSIÓN ALIMENTICIA: Pablo debe pagar antes del día 5 de cada mes (pensión + $100.000 CLP por servicios de Liliana Vargas). Recordar en el resumen AM del día 1 de cada mes.
- PAGOS SHARKS (fútbol Franco): Angela paga todo lo relacionado al grupo "Copas 5to Sharks SC" (cuotas, equipamiento, torneos).
- PAGOS COLEGIO: Pablo paga todo lo relacionado con el Sagrado Corazón (cuotas, casino, materiales).
- CUMPLEAÑOS (regalos): Quien tiene los niños esa semana compra el regalo para el cumpleaños al que están invitados.
- DÍA DEL PADRE/MADRE: Si no les toca esa semana con el respectivo padre/madre, los niños tienen derecho a estar durante el día con él/ella.
- DÍA DEL PADRE / DÍA DE LA MADRE: Si no les toca esa semana con el respectivo padre/madre, los niños tienen derecho a estar con él/ella durante el día.
- En el resumen indicar quién tiene los niños esa semana y quién hace el cambio (dejar/buscar)
- Ejemplo: "Esta semana los niños están con Angela. Pablo los busca el martes 22 después del colegio."

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
- Horarios especiales (Playback, ensayos, etc.) solo aplican para el día ESPECÍFICO que indica el SC Info

REGLA CRÍTICA - SEMANA SC / ALIANZAS:
- Cuando el SC Info indica que es Semana SC/Alianzas, los horarios NORMALES NO APLICAN
- Usar SOLO los horarios que indica el SC Info para esa semana (ej: "salida 13:10 hrs")
- NO mostrar los ramos normales durante Semana SC (no hay clases normales)
- En vez de ramos, indicar las actividades de la Semana SC
- Solo aplicar horarios especiales (Playback, etc.) para los días ESPECÍFICOS que menciona el SC Info, no para toda la semana

REGLA SOBRE INFORMACIÓN DEL SC INFO:
- TODA la info relevante del SC Info debe incluirse en el resumen
- Avisos sobre preinscripciones de extraprogramáticas, cambios de personal, actividades deportivas, etc.
- Si hay info de horarios especiales para citados a actividades (Playback, baile, etc.), incluirla como aviso
- No omitir nada que pueda ser accionable para los apoderados
- Incluir noticias que apliquen a los ciclos de los hijos:
  - Franco (5°A): Ciclo Básico (3° a 5°), noticias generales "A toda la comunidad"
  - Blanca (1°C): Ciclo Inicial (PK a 2°), noticias generales "A toda la comunidad"
- Cambios de personal, nuevos encargados, contactos: SIEMPRE incluir (nombre + email si hay)
- Preinscripciones y plazos (extraprogramáticas, talleres): SIEMPRE incluir con fecha de inicio
- Reuniones comunitarias (Bicis con Amor, Centro de Padres, voluntariados): SIEMPRE incluir si tienen fecha en los próximos 7 días
- Retiros, charlas, eventos para apoderados: SIEMPRE incluir con fecha, hora y lugar

REGLA SOBRE INSTRUCCIONES DE LOS PADRES (instrucciones_padres):
- Son mensajes escritos por los padres en el grupo "Monitor Colegio"
- Tienen MÁXIMA PRIORIDAD — son cambios o aclaraciones manuales
- Ejemplos: "Franco no va al ajedrez esta semana", "Blanca tiene cumpleaños viernes 17:00"
- Si contradicen otra fuente, las instrucciones de los padres GANAN
- Incluir en el resumen como información confirmada
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
            context = "\nEs un mensaje DIARIO PM. Solo incluir: novedades/comunicaciones que llegaron HOY, resumen de WhatsApp relevante de HOY, y preparación para MAÑANA (ramos, hora salida, pruebas, extraprogramáticas, actividades). NO incluir info del día actual que ya pasó (clases, horarios de hoy). El foco es: qué pasó hoy de nuevo + qué viene mañana."
        
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
        """Formatea los datos para el prompt. Orden de prioridad:
        1. Instrucciones padres (grupo Monitor Colegio) - MÁXIMA
        2. Emails del colegio
        3. SC Info
        4. Resto (calendario, horarios, WhatsApp grupos, etc.)
        """
        import json
        sections = []
        high_limit_keys = ("scinfo", "emails", "whatsapp_5A_franco", 
                          "whatsapp_1C_blanca", "whatsapp_sharks_franco",
                          "instrucciones_padres")
        
        # 1. INSTRUCCIONES PADRES (máxima prioridad)
        if "instrucciones_padres" in data and data["instrucciones_padres"]:
            val = json.dumps(data["instrucciones_padres"], indent=2, ensure_ascii=False)[:4000]
            sections.append(f"### ⚠️🔴 INSTRUCCIONES DE LOS PADRES (PRIORIDAD MÁXIMA - PREVALECE SOBRE TODO)\n{val}")
        
        # 2. EMAILS
        if "emails" in data and data["emails"]:
            val = json.dumps(data["emails"], indent=2, ensure_ascii=False)[:4000]
            sections.append(f"### 📧 EMAILS DEL COLEGIO (2da prioridad)\n{val}")
        
        # 3. SC INFO
        if "scinfo" in data and data["scinfo"]:
            val = json.dumps(data["scinfo"], indent=2, ensure_ascii=False)[:5000]
            sections.append(f"### 📋 SC INFO (3ra prioridad - HORARIOS Y ACTIVIDADES DE LA SEMANA)\n{val}")
        
        # 4. RESTO
        skip_keys = ("instrucciones_padres", "emails", "scinfo")
        for key, value in data.items():
            if value and key not in skip_keys:
                limit = 4000 if key in high_limit_keys else 2000
                value_str = json.dumps(value, indent=2, ensure_ascii=False)[:limit]
                if key == "horarios":
                    sections.append(f"### {key} (SOLO usar si NO hay info en SC Info ni instrucciones para ese día)\n{value_str}")
                else:
                    sections.append(f"### {key}\n{value_str}")
        return "\n\n".join(sections)
