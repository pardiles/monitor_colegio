# Arquitectura Final - Monitor Colegio

## Decisiones técnicas

| Aspecto | Decisión |
|---|---|
| Infra | AWS SAM (Lambda Docker + EventBridge + S3) |
| Lenguaje | Python |
| IA para resumen | Claude Haiku (Anthropic API) |
| WhatsApp envío | Twilio WhatsApp API |
| WhatsApp lectura | whatsapp-web.js (Node.js, número secundario recomendado) |
| Login SchoolNet | Playwright (headless) → cookie → requests |
| Storage | S3 (JSON por día) |

## Hijos

| Nombre | Curso | Grupo WA ID | SchoolNet idx |
|---|---|---|---|
| Franco Antonio | 5°A | 120363022899821958@g.us | 0 |
| Blanca Fernanda | 1°C | 120363407876876956@g.us | 1 |

## Mensajes diarios

### Briefing matutino (7:00 AM)
Contenido: qué pasa HOY + qué viene en la semana
```
📋 Lunes 14 julio - Franco (5°A) y Blanca (1°C)

🏫 HOY:
• Franco: Matemáticas, Lenguaje, Ciencias, Ed. Física, Inglés. Sale 16:30
• Blanca: [horario]. Sale 15:30
• ⚠️ Prueba de Matemáticas (Franco) - Unidad 4 Fracciones
• 🎂 Cumpleaños de [compañero/a]
• ⚽ Extraprogramática: Fútbol (Franco, 17:00-18:00)

📅 ESTA SEMANA:
• Mar 15: Reunión apoderados 15:00 (profesora jefe Franco)
• Mié 16: Feriado - no hay clases
• Jue 17: Control lectura Lenguaje (Franco)
• Vie 18: Salida anticipada 13:00 (ambos)

📨 PENDIENTES:
• Entregar autorización salida pedagógica (Franco, plazo viernes)
```

### Resumen nocturno (20:00)
Contenido: lo nuevo que llegó durante el día
```
📬 Resumen del día - Lunes 14 julio

📧 EMAILS NUEVOS:
• "Información semana SC" - SubDirección Ciclo Inicial
  → Avisa salida anticipada viernes 13:00 por jornada docente

💬 GRUPO WA "5° básico A":
• Apoderada pregunta por materiales para feria de ciencias
• Profesora confirma cambio de horario prueba de historia

💬 GRUPO WA "1C SCA":
• Recordatorio: traer delantal para arte mañana

🔔 SCHOOLNET:
• Nueva comunicación: "SC Info 14-07-2026"
```

## Fuentes de datos

### Lambda 1: Ingesta (6:00 AM y 19:00)
Se ejecuta 2 veces al día para capturar info nueva.

1. **SchoolNet** (Playwright + requests)
   - Comunicaciones nuevas
   - Calificaciones nuevas
   - Anotaciones conducta
   - Pagos/cobranza pendientes

2. **Calendario evaluaciones** (API JSON pública)
   - Evaluaciones de la semana/mes
   - Feriados y días sin clases

3. **Gmail** (Gmail API)
   - Correos nuevos de @colegiodelsagradocorazon.cl

4. **Noticias web** (Scrapling HTTP)
   - Últimas noticias publicadas

5. **WhatsApp grupos** (whatsapp-web.js)
   - Mensajes nuevos de los 2 grupos

### Lambda 2: Resumen + Envío (7:00 AM y 20:00)
1. Lee datos del día desde S3
2. Arma contexto con info relevante (hoy + semana)
3. Llama a Claude Haiku para generar resumen natural
4. Envía por Twilio WhatsApp

## Detalles específicos para el resumen

El prompt de Claude debe incluir lógica para detectar y destacar:
- 🎂 Cumpleaños (de los hijos o compañeros, si está en datos)
- 📝 Evaluaciones del día o próximos 3 días
- ⚽ Extraprogramáticas del día (horarios, qué llevar)
- 🕐 Salidas anticipadas o cambios de horario
- 💰 Pagos pendientes o avisos de cobranza
- 📋 Entregas o tareas con plazo cercano
- 🏫 Reuniones de apoderados
- 📢 Información urgente de emails/SchoolNet/WhatsApp

## Infraestructura AWS (SAM)

```
EventBridge (cron 6:00 AM) → Lambda Ingesta → S3
EventBridge (cron 7:00 AM) → Lambda Resumen → Twilio → WhatsApp
EventBridge (cron 19:00)   → Lambda Ingesta → S3  
EventBridge (cron 20:00)   → Lambda Resumen → Twilio → WhatsApp
```

### Lambdas
- **ingesta**: Docker image (Python + Playwright + Scrapling)
- **resumen**: Lambda normal (Python, liviana, solo lee S3 + llama Claude + Twilio)

### S3 Bucket
```
s3://monitor-colegio-data/
  └── {fecha}/
      ├── schoolnet_comunicaciones.json
      ├── schoolnet_calificaciones.json
      ├── schoolnet_asistencia.json
      ├── calendario_evaluaciones.json
      ├── gmail_emails.json
      ├── noticias_web.json
      └── whatsapp_messages.json
```

### Secrets Manager
- SchoolNet credentials
- Gmail token
- Anthropic API key
- Twilio credentials
- WhatsApp session

## Diseño para multi-usuario (futuro)

El código se estructura parametrizado:
- Config de usuario (hijos, cursos, grupos WA, credenciales) como input
- Fácil migrar a DynamoDB + loop por usuario más adelante
- El prompt de Claude recibe contexto genérico, no hardcodeado

## Costo estimado mensual (1 usuario)

| Servicio | Costo |
|---|---|
| Lambda ingesta (2x/día, ~60s, Docker) | ~$1 |
| Lambda resumen (2x/día, ~10s) | ~$0.50 |
| S3 | ~$0.10 |
| Claude Haiku (2 calls/día) | ~$1 |
| Twilio WhatsApp (60 msgs/mes) | ~$5 |
| Secrets Manager | ~$0.40 |
| **Total** | **~$8/mes** |
