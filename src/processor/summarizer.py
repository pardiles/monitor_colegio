"""
Procesador: Genera resúmenes diarios con Claude Haiku.
Soporta múltiples usuarios con contexto dinámico.
"""

import json
import anthropic
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional

CHILE_TZ = ZoneInfo("America/Santiago")


def build_context(user_cfg: Optional[Dict] = None) -> str:
    """Genera el contexto del prompt dinámicamente desde la config del usuario."""
    if not user_cfg:
        return ""

    lines = []

    # Hijos
    hijos = user_cfg.get("hijos", [])
    if hijos:
        lines.append("Hijos:")
        for h in hijos:
            nombre = h.get("nombre_completo") or h.get("nombre", "")
            curso = h.get("curso", "")
            profe = h.get("profesora_jefe", "")
            colegio = h.get("colegio", "")
            line = f"- {nombre}"
            if curso:
                line += f" - {curso}"
            if profe:
                line += f" (Profesora jefe: {profe})"
            if colegio:
                line += f" [{colegio}]"
            lines.append(line)

    # Colegio(s)
    colegio = user_cfg.get("colegio", {})
    colegios = user_cfg.get("colegios", [])
    if colegio:
        lines.append(f"\nColegio: {colegio.get('nombre', '')}")
    elif colegios:
        lines.append("\nColegios:")
        for c in colegios:
            lines.append(f"- {c.get('nombre', '')} ({c.get('hijo', '')})")

    # Régimen de custodia
    regimen = user_cfg.get("regimen")
    if regimen:
        lines.append(f"\nRégimen de custodia ({regimen.get('tipo', '')}):")
        if regimen.get("padre") and regimen.get("madre"):
            lines.append(f"- Padre: {regimen['padre']}, Madre: {regimen['madre']}")
        if regimen.get("detalle_padre"):
            lines.append(f"- {regimen['padre']}: {regimen['detalle_padre']}")
        if regimen.get("detalle_madre"):
            lines.append(f"- {regimen['madre']}: {regimen['detalle_madre']}")
        if regimen.get("semana_actual"):
            lines.append(f"- Semana referencia {regimen.get('semana_referencia', '')}: {regimen['semana_actual']}")
        lines.append("- En el resumen indicar quién tiene los niños esta semana")

    # Extraprogramáticas
    extras = user_cfg.get("extraprogramaticas", [])
    if extras:
        lines.append("\nExtraprogramáticas:")
        for e in extras:
            lines.append(f"- {e['nombre']}: {e['dia']} {e['horario']} ({e['hijo']}) → sale a las {e.get('hora_salida_real', '')}")

    # Pagos
    pagos = user_cfg.get("pagos")
    if pagos:
        lines.append("\nPagos/Recordatorios:")
        if isinstance(pagos, dict):
            for k, v in pagos.items():
                lines.append(f"- {k}: {v}")
        elif isinstance(pagos, list):
            for p in pagos:
                lines.append(f"- {p.get('concepto', '')}: día {p.get('dia', '')} - {p.get('monto', '')}")

    # Alianzas (si aplica)
    alianzas = user_cfg.get("alianzas_2026")
    if alianzas:
        lines.append("\nAlianzas 2026:")
        for hijo, info in alianzas.items():
            lines.append(f"- {hijo} → Alianza {info['alianza']} = {info['pais']} ({info['colores']})")

    # Reglas generales
    lines.append("""
REGLAS GENERALES:
- SIEMPRE indicar a qué hijo aplica cada información
- Las comunicaciones/SC Info son la fuente más confiable para horarios y actividades
- Si las comunicaciones indican salida anticipada o sin extras, usar esa info
- Entrevistas/reuniones: incluir SIEMPRE fecha, hora y lugar
- Omitir secciones vacías
- Español chileno natural

PRIORIDAD ABSOLUTA - FECHAS Y HORARIOS:
- SIEMPRE incluir qué toca MAÑANA: pruebas, entrevistas, reuniones, actividades, hora de salida
- Si hay entrevista/reunión con hora y lugar, NUNCA omitirla
- El calendario_persistente tiene eventos futuros con fecha y hora — REVISAR SIEMPRE
- En el resumen semanal, incluir TODOS los eventos del calendario de la semana día por día

REGLA SOBRE INSTRUCCIONES DE LOS PADRES (instrucciones_padres):
- Son mensajes escritos por los padres en el grupo "Monitor Colegio"
- Tienen MÁXIMA PRIORIDAD — son cambios o aclaraciones manuales
- Si contradicen otra fuente, las instrucciones de los padres GANAN
- Incluir en el resumen como información confirmada
""")

    return "\n".join(lines)


def build_morning_prompt(context: str) -> str:
    """Prompt de sistema para briefing matutino."""
    return f"""Eres un asistente que genera briefings matutinos para un apoderado.
{context}

FORMATO OBLIGATORIO:

📋 [Día y fecha]

📢 AVISOS GENERALES:
• [Aviso] (fuente: SC Info/email/WA)
• [Aviso] (fuente: ...)

🏫 HOY [día] - [HIJO] ([curso]):
• Ramos: [lista]. Sale a las [hora]
• ⚠️ Prueba/evaluación (fuente: calendario)
• ⚽ Extraprogramática (fuente: config)
(repetir para cada hijo)

📅 MAÑANA [día]:
• [HIJO]: [qué toca, hora salida, pruebas, actividades] (fuente: ...)
(si es resumen semanal, repetir para cada día de la semana)

📨 PENDIENTES:
• [Entrega/plazo] - [HIJO] (fuente: ...)

REGLAS DE FORMATO:
- Agrupar por DÍA, no por fuente. Si 2 fuentes dicen lo mismo, usar la que tenga más detalle
- Al final de cada punto, indicar la fuente entre paréntesis: (SC Info), (email), (WA 5°A), (calendario), (SchoolNet)
- NO repetir la misma info si viene de múltiples fuentes — fusionar en 1 línea con la fuente más completa
- SIEMPRE incluir hora de salida por hijo
- ⚠️ REUNIONES/ENTREVISTAS del calendario_persistente con hora: INCLUIR SIEMPRE con ⚠️, fecha, hora y lugar. NUNCA omitirlas. Son citas confirmadas.
- SIEMPRE revisar calendario_persistente para HOY y próximos 5 días
- Máximo 22 líneas
- Español chileno natural
"""


def build_evening_prompt(context: str) -> str:
    """Prompt de sistema para resumen nocturno."""
    return f"""Eres un asistente que genera resúmenes nocturnos para un apoderado. Cubre SOLO lo nuevo de hoy (que no estaba en el resumen AM) y prepara para mañana.
{context}

FORMATO OBLIGATORIO:

📬 Resumen del día - [Día y fecha]

📢 NOVEDADES DE HOY (solo info nueva que llegó durante el día):
• [Novedad] (fuente: email/SchoolNet/WA grupo)
(Si no hay novedades nuevas, omitir esta sección)

💬 WA GRUPOS (solo si hubo mensajes relevantes hoy):
• [Grupo]: [resumen corto] (WA 5°A / WA 1°C)

📅 MAÑANA [día]:
🏫 [HIJO] ([curso]):
• Ramos: [lista]. Sale a las [hora]
• ⚠️ Prueba/evaluación si tiene (fuente: calendario)
• ⚽ Extraprogramática (fuente: config)
(repetir para cada hijo)

📅 PRÓXIMOS DÍAS (si hay eventos relevantes en los próximos 3 días):
• [Día]: [Evento] - [HIJO] (fuente: ...)

REGLAS DE FORMATO:
- NO repetir info que ya se dijo en el resumen AM de hoy (avisos generales, calendario, etc.)
- Solo incluir NOVEDADES: emails/comunicaciones que llegaron HOY, mensajes WA de HOY
- La sección MAÑANA SÍ se repite siempre (es la preparación para el día siguiente)
- Agrupar por DÍA, no por fuente. Fusionar si 2 fuentes dicen lo mismo
- Indicar fuente al final: (SC Info), (email), (WA 5°A), (calendario)
- ⚠️ REUNIONES/ENTREVISTAS del calendario_persistente con hora: INCLUIR SIEMPRE con ⚠️, fecha, hora y lugar. NUNCA omitirlas.
- SIEMPRE revisar calendario_persistente para mañana y próximos 5 días
- Si mañana es fin de semana, mostrar info del lunes
- Omitir secciones vacías
- Máximo 25 líneas
- Español chileno natural

RESUMEN SEMANAL (domingo PM):
Si es domingo PM, cambiar el formato a panorama COMPLETO de la semana que viene:
📋 Semana [fecha inicio] al [fecha fin]

📢 AVISOS GENERALES DE LA SEMANA:
• [avisos que aplican a toda la semana]

📅 LUNES [fecha]:
🏫 [HIJO]: [ramos, hora salida, pruebas, actividades] (fuente)
(repetir por cada hijo)

📅 MARTES [fecha]:
...
(repetir para cada día lunes a viernes)

📨 PENDIENTES/PLAZOS DE LA SEMANA:
• [entrega/plazo] - [HIJO] (fuente)

En el semanal SÍ incluir TODO del calendario_persistente para esa semana.
"""


class Summarizer:
    """Genera resúmenes usando Claude Haiku."""

    def __init__(self, api_key: str, user_cfg: Optional[Dict] = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.context = build_context(user_cfg)

    def generate_morning_briefing(self, data: Dict[str, Any], is_weekly: bool = False) -> str:
        """Genera el briefing matutino."""
        today = datetime.now(CHILE_TZ)

        context_note = ""
        if is_weekly:
            context_note = "\nIMPORTANTE: Es el RESUMEN SEMANAL (domingo PM). Incluye el panorama completo de TODA la semana que viene."
        else:
            context_note = "\nEs un mensaje DIARIO. Solo incluir si hay algo relevante para HOY. Si no hay nada especial, responder con los ramos/hora de salida y '✅ Sin novedades adicionales.'"

        user_content = f"""Fecha de hoy: {today.strftime('%A %d de %B de %Y')}{context_note}

Datos disponibles:
{self._format_data(data)}

Genera el briefing matutino."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500 if is_weekly else 1200,
            system=build_morning_prompt(self.context),
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

    def generate_evening_summary(self, data: Dict[str, Any], is_weekly: bool = False) -> str:
        """Genera el resumen nocturno."""
        today = datetime.now(CHILE_TZ)

        context_note = ""
        if is_weekly:
            context_note = "\nIMPORTANTE: Es el RESUMEN SEMANAL (domingo PM). Incluye el panorama completo de TODA la semana que viene día por día."
        else:
            context_note = "\nEs un mensaje DIARIO PM. Foco: novedades de HOY + preparación para MAÑANA."

        user_content = f"""Fecha de hoy: {today.strftime('%A %d de %B de %Y')}{context_note}

Datos del día:
{self._format_data(data)}

Genera el resumen nocturno."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000 if is_weekly else 1500,
            system=build_evening_prompt(self.context),
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

    def _format_data(self, data: Dict[str, Any]) -> str:
        """Formatea los datos para el prompt. Orden de prioridad:
        1. Instrucciones padres - MÁXIMA
        2. Emails/comunicaciones
        3. SC Info / Cuaderno Rojo
        4. Resto
        """
        sections = []
        high_priority = ("instrucciones_padres", "emails", "comunicaciones",
                        "scinfo", "cuadernorojo_comunicados")

        # 1. Instrucciones padres
        if "instrucciones_padres" in data and data["instrucciones_padres"]:
            val = json.dumps(data["instrucciones_padres"], indent=2, ensure_ascii=False)[:4000]
            sections.append(f"### ⚠️🔴 INSTRUCCIONES DE LOS PADRES (MÁXIMA PRIORIDAD)\n{val}")

        # 2. Emails
        for key in ("emails", "emails_ambos", "emails_esperanza", "emails_simón"):
            if key in data and data[key]:
                val = json.dumps(data[key], indent=2, ensure_ascii=False)[:4000]
                sections.append(f"### 📧 {key.upper()}\n{val}")

        # 3. Comunicaciones (SchoolNet / Cuaderno Rojo)
        if "comunicaciones" in data and data["comunicaciones"]:
            val = json.dumps(data["comunicaciones"], indent=2, ensure_ascii=False)[:4000]
            sections.append(f"### 🏫 COMUNICACIONES SCHOOLNET\n{val}")
        if "cuadernorojo_comunicados" in data and data["cuadernorojo_comunicados"]:
            val = json.dumps(data["cuadernorojo_comunicados"], indent=2, ensure_ascii=False)[:4000]
            sections.append(f"### 📕 COMUNICADOS CUADERNO ROJO\n{val}")

        # 4. SC Info
        if "scinfo" in data and data["scinfo"]:
            val = json.dumps(data["scinfo"], indent=2, ensure_ascii=False)[:5000]
            sections.append(f"### 📋 SC INFO (HORARIOS Y ACTIVIDADES DE LA SEMANA)\n{val}")

        # 5. Calendario persistente (eventos futuros con fecha/hora)
        if "calendario_persistente" in data and data["calendario_persistente"]:
            val = json.dumps(data["calendario_persistente"], indent=2, ensure_ascii=False)[:4000]
            sections.append(f"### 📅 CALENDARIO PERSISTENTE (EVENTOS FUTUROS CON FECHA Y HORA - REVISAR SIEMPRE)\n{val}")

        # 6. Resto
        skip = set(high_priority) | {"emails_ambos", "emails_esperanza", "emails_simón", "calendario_persistente"}
        for key, value in data.items():
            if value and key not in skip:
                limit = 4000 if "whatsapp" in key else 2000
                value_str = json.dumps(value, indent=2, ensure_ascii=False)[:limit]
                sections.append(f"### {key}\n{value_str}")

        return "\n\n".join(sections)
