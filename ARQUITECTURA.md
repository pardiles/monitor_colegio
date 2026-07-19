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

5. **WhatsApp grupos** (Baileys)
   - Mensajes nuevos de los 3 grupos (última semana)

6. **Fuentes futuras (pendientes de implementar)**
   - **Lirmi** (https://www.lirmi.cl/cl) — Plataforma escolar usada en varios colegios de Chile. Scraping con Playwright + requests.
   - **LaFase** (https://lafase.cl/) — Plataforma de gestión escolar. PDFs públicos (calendario, extracurriculares, deportiva, casino).
   - **Pronote** (https://4170004n.index-education.net/pronote/) — Plataforma francesa de gestión escolar usada en liceos franceses de Chile (Alliance Française, Lycée, etc.). Evaluar librería `pronotepy`.
   - Cada nueva fuente debe extraer: calificaciones, compañeros, asistencia, conducta, extraprogramáticas, actividades, atrasos, pagos, **casino/menú del día**, **calendario** (evaluaciones, feriados, eventos, reuniones), **noticias** (web del colegio).

   **REGLA FUNDAMENTAL DE SCRAPING:**
   Todo webscrapper desarrollado para cualquier colegio/plataforma SIEMPRE debe buscar cómo extraer los tópicos fundamentales con el mayor detalle posible. La lista de tópicos obligatorios es:

   | # | Tópico | Detalle mínimo esperado |
   |---|---|---|
   | 1 | Calificaciones | Por asignatura, por semestre, promedios parciales y finales |
   | 2 | Compañeros | Nombre, teléfono, dirección, padre, madre, emails, cumpleaños |
   | 3 | Asistencia | Inasistencias con fechas + atrasos con fechas |
   | 4 | Conducta | Anotaciones con fecha, motivo, profesor |
   | 5 | Extraprogramáticas | Nombre, día, horario, estado (pagada/inscrita), profesor |
   | 6 | Actividades/Eventos | Fecha, hora, descripción, lugar, curso afectado |
   | 7 | Pagos/Cobranza | Historial pagados + avisos pendientes con vencimiento y monto |
   | 8 | Casino/Menú | Menú del día o semanal (generalmente PDF mensual) |
   | 9 | Calendario | Evaluaciones, feriados, reuniones, salidas anticipadas — siempre con FECHA y HORA |
   | 10 | Noticias | Últimas publicaciones de la web del colegio |
   | 11 | Comunicaciones | Circulares, avisos oficiales del colegio |
   | 12 | Horarios | Ramos por día + hora de salida por curso |

   **REGLA: Todo dato que tenga fecha DEBE incluir la hora si está disponible.** Pruebas, entrevistas, reuniones, actividades, eventos — siempre día + hora. Si la hora no está explícita, indicar "hora no especificada".

   Si un tópico no está disponible en la plataforma, documentar por qué y buscar fuente alternativa (web del colegio, PDF, email, etc.).

   **ARQUITECTURA DE EJECUCIÓN DE SCRAPERS:**

   Por usuario se ejecutan TODAS sus fuentes configuradas, y CADA fuente busca TODOS los tópicos:

   ```
   Usuario → [SchoolNet] → 12 tópicos
           → [Web colegio] → 12 tópicos  
           → [Gmail] → 12 tópicos (extraer info relevante de emails: cumpleaños, paseos, reuniones, pagos)
           → [WhatsApp] → 12 tópicos (extraer de mensajes: cumpleaños, paseos, horarios, actividades)
   ```

   **Ejecución:**
   - Primera vinculación: TODAS las fuentes se ejecutan en secuencial (real-time, ~2-5 min)
   - Ejecución diaria (cron): secuencial por usuario, fuente por fuente
   - Futuro (escalamiento): paralelizar fuentes por usuario con asyncio/threads

   **Gmail y WhatsApp como fuentes de tópicos:**
   No solo monitorear mensajes — también EXTRAER datos relevantes:
   - Cumpleaños mencionados en grupos → calendario
   - "Mañana no hay clases" → calendario
   - "Paseo el viernes al parque" → actividades
   - "Casino: menú de la semana" (adjunto PDF) → casino
   - "Reunión de apoderados martes 15:00" → calendario
   - Emails de cobranza → pagos
   - Emails con horarios/calendario adjunto → horarios, calendario

   **Además de los 12 tópicos, Gmail y WA deben extraer DATOS GENERALES relevantes:**
   - Conflictos entre apoderados o con el colegio
   - Juntas fuera del colegio (cumpleaños de compañeros, asados, salidas grupales)
   - Partidos y eventos deportivos
   - Cambios de horario mencionados informalmente
   - Actividades sociales del curso (rifas, colectas, regalos profesores)
   - Info de transporte (furgón, cambios de ruta)
   - Cualquier dato que un apoderado consideraría útil saber

   Todo esto se agrega al **calendario persistente** como eventos, permitiendo que el resumen diario y el bot tengan visibilidad completa de lo que pasa alrededor del colegio — no solo lo oficial.

   **Merge de tópicos:**
   Si 2 fuentes encuentran el mismo tópico (ej: calendario en SchoolNet Y en web del colegio), se fusionan sin duplicar. Prioridad: plataforma académica > web del colegio > Gmail > WhatsApp.

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
