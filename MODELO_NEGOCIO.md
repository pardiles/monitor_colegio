# Modelo de Negocio - Monitor Colegio

## Propuesta de valor
Resúmenes diarios automáticos por WhatsApp con toda la información escolar relevante: comunicaciones, horarios, evaluaciones, entrevistas, extraprogramáticas. El apoderado no tiene que revisar emails, apps del colegio ni grupos de WhatsApp — recibe todo resumido 2 veces al día.

## Cliente
El colegio (B2B). El colegio ofrece el servicio a todos sus apoderados. El que quiere lo usa.

## Pricing (en UF)

| Concepto | Valor |
|---|---|
| Base mensual | 26 UF (~$1.000.000 CLP) — incluye hasta 500 alumnos |
| Alumno extra (sobre 500) | $1.000 CLP/alumno/mes |
| Setup | Incluido |
| Prueba | 1er mes gratis |
| Contrato mínimo | 12 meses (después del mes de prueba) |

### Ejemplos por tamaño de colegio

| Colegio | Alumnos | Cobro mensual | Cobro anual |
|---|---|---|---|
| Chico (300 alumnos) | 300 | $1.000.000 | $12.000.000 |
| Mediano (800 alumnos) | 800 | $1.300.000 | $15.600.000 |
| Grande (1500 alumnos) | 1500 | $2.000.000 | $24.000.000 |

### Costo de infraestructura

| Familias registradas | Costo real/mes (CLP) |
|---|---|
| 50 | ~$10.000 |
| 200 | ~$40.000 |
| 500 | ~$100.000 |
| 1000 | ~$200.000 |

Basado en $0.21 USD/usuario/mes (arquitectura escalable con Gemini Flash + proxy bulk).

### Márgenes

| Colegio | Cobro/mes | Costo/mes (60% adopción) | Margen |
|---|---|---|---|
| Chico (300 al, 120 familias) | $1.000.000 | ~$25.000 | 97% |
| Mediano (800 al, 300 familias) | $1.300.000 | ~$64.000 | 95% |
| Grande (1500 al, 600 familias) | $2.000.000 | ~$126.000 | 94% |

## Proyección primer año (solo, sin equipo, colegios medianos)

| Mes | Colegios pagando | Ingreso | Costo infra | Profit |
|---|---|---|---|---|
| 1 | 0 (1 en prueba) | $0 | $19.000 | -$19.000 |
| 2 | 1 | $1.300.000 | $38.000 | $1.262.000 |
| 3 | 2 | $2.600.000 | $57.000 | $2.543.000 |
| 4 | 3 | $3.900.000 | $76.000 | $3.824.000 |
| 5 | 4 | $5.200.000 | $95.000 | $5.105.000 |
| 6 | 5 | $6.500.000 | $114.000 | $6.386.000 |
| 7 | 6 | $7.800.000 | $133.000 | $7.667.000 |
| 8 | 7 | $9.100.000 | $152.000 | $8.948.000 |
| 9 | 8 | $10.400.000 | $171.000 | $10.229.000 |
| 10 | 9 | $11.700.000 | $190.000 | $11.510.000 |
| 11 | 10 | $13.000.000 | $209.000 | $12.791.000 |
| 12 | 10 | $13.000.000 | $209.000 | $12.791.000 |

**Total año 1: ~$84M ingreso / ~$1.5M costo / ~$82.5M profit**

**Sueldo objetivo: $6M líquidos/mes → cubierto en mes 7 (6 colegios).**

## Target de mercado (primer año)
- Colegios particulares pagados de Santiago
- Comunas: Las Condes, Vitacura, Lo Barnechea, La Dehesa, Providencia
- Perfil: mensualidad >$300K/alumno, usan SchoolNet/Colegium, apoderados activos en WhatsApp
- Caso de éxito: Colegio del Sagrado Corazón Apoquindo (piloto gratuito)

### Testers activos / próximos

| Nombre | Colegio | Plataforma probable | Estado |
|---|---|---|---|
| Pablo Ardiles | Sagrado Corazón Apoquindo | SchoolNet (Colegium) | ✅ Activo |
| Oscar Ardiles | Oxford School / Acuarela Montessori | Oxford RSS + Cuaderno Rojo | ✅ Activo |
| Kevin Moir | Sagrado Corazón Apoquindo | SchoolNet (Colegium) | ✅ Activo |
| Ramón Lillo | Sagrado Corazón Apoquindo | SchoolNet (Colegium) | 🟡 Pendiente |
| Jose Walker | Sagrado Corazón Apoquindo | SchoolNet (Colegium) | 🟡 Pendiente |
| Rafael Morales | Saint George's College | SchoolNet (Colegium) | 🟡 Pendiente |
| Jose Yutronic | Alianza Francesa | Pronote | 🟡 Pendiente |
| Daniel Fouilloux | Colegio Alemán | SchoolNet (Colegium) | 🟡 Pendiente |
| Javier Bosch | San Ignacio El Bosque | SchoolNet (Colegium) | 🟡 Pendiente |
| Francisco Guzmán | Colegio Manquehue | SchoolNet (Colegium) | 🟡 Pendiente |

## Notas pendientes
- **IMPORTANTE SchoolNet**: Las credenciales deben ser del apoderado titular/admin de la cuenta. El usuario secundario (ej: la mamá si el papá es titular) NO puede ver las cobranzas ni algunos datos. Siempre solicitar credenciales del titular.
- **Módulos opcionales de SchoolNet/Colegium**: No todos los colegios tienen todos los módulos. Módulos que pueden no existir:
  - Extracurriculares (módulo separado, requiere contrato adicional)
  - Pagos/Cobranza (algunos colegios usan pasarela externa)
  - Casino/Alimentación
  - Transporte
  - Salud escolar
  El scraper debe manejar gracefully cuando un módulo no existe (devolver vacío, no error). Detectar en el primer scrape qué módulos tiene cada colegio y guardarlo en la config para no reintentar los que no existen.
- **Almacenamiento incremental**: Revisar cómo se guarda la información para no duplicar datos entre ejecuciones. La ingesta debe ser incremental (solo agregar lo nuevo, no reescribir todo cada vez).
- **Múltiples emails por usuario**: Un apoderado puede tener más de un email a monitorear (ej: Rafael Morales tiene 2). La config de Gmail debe soportar múltiples cuentas/direcciones por usuario, filtrando por dominios del colegio en cada una.
- **Landing: pairing code desde celular**: El proceso de generar pairing code tarda ~30-50 segundos (Baileys conecta + genera código). La landing debe:
  1. Mostrar spinner con "Generando código de vinculación, puede demorar hasta 30 segundos..."
  2. Una vez mostrado el código, agregar un **timer visual countdown** (ej: "Tienes 45 segundos para ingresar este código") para que el usuario sepa que tiene que ser rápido
  3. Aumentar el timeout del proceso
  4. Actualmente se queda pegado en "Iniciando sesión" y no termina
  5. Si expira, mostrar botón "Reintentar" en vez de quedarse pegado
- **Automatizar alta de usuarios (Gmail/landing)**: Implementado flujo de lista autorizada en S3. El admin carga emails autorizados y la landing valida contra esa lista. Para escalar a colegios: el colegio entrega lista de emails → se carga masivamente.
- **Google OAuth verification**: Mientras la app esté en "modo test", máximo 100 usuarios pueden vincular Gmail. Para escalar a un colegio completo (500+ familias) necesitamos pasar la **verificación de Google** (formulario + review, ~2-4 semanas). Iniciar este trámite ANTES de cerrar el primer colegio pagante. Requisitos: política de privacidad, dominio verificado, descripción del uso de datos.
- **Gmail unauthorized_client**: Revisar por qué el token OAuth de la landing genera error `unauthorized_client` en algunos casos. Posibles causas: app en modo test (solo 100 usuarios), token expirado sin refresh, o client_id no autorizado para el scope. Definir flujo robusto que no falle al refrescar tokens.
- **Alta masiva de usuarios**: Definir cómo dar de alta 500 usuarios de un colegio nuevo de forma rápida:
  - Opción A: el colegio entrega CSV con emails → script los carga a S3 como autorizados → se les manda email de invitación con link a la landing
  - Opción B: link de registro genérico por colegio (ej: `landing?colegio=sagrado_corazon`) que cualquier apoderado del colegio puede usar
  - Opción C: integración con el sistema del colegio (SchoolNet exporta lista de apoderados con email)
  - Considerar: cómo vincular WA de 500 personas (cada una tiene que escanear QR/pairing code individualmente — no se puede automatizar)
- **Espacio en disco EC2**: Revisar periódicamente el espacio en disco. Eliminar archivos temporales (/tmp/qr_*, /tmp/pairing.log, /tmp/vincular_*), logs antiguos (/var/log/wa_listener.log, /var/log/monitor-colegio.log), data de outbox procesada, PDFs de attachments viejos (>30 días), bot_context antiguos. Implementar cron de limpieza o script de mantenimiento semanal.
- **Frecuencia de scrapers por fuente**: Revisar cada cuánto se ejecuta cada scraper dependiendo de la fuente. No todas las fuentes cambian con la misma frecuencia:
  - SchoolNet (notas, asistencia, conducta): 2x/día (morning + evening) — cambian durante la jornada escolar
  - Extraprogramáticas: 1x/semestre (solo cambian al inicio de cada semestre cuando se inscriben)
  - Calendario evaluaciones (API JSON): 1x/día (se publican con días de anticipación)
  - Gmail: 2x/día (llegan comunicaciones durante el día)
  - Casino/menú: 1x/día en el morning (el menú se publica la noche anterior o temprano AM)
  - SC Info: 1x/semana (se publica los lunes)
  - Compañeros: 1x/mes (rara vez cambia)
  - Web colegio (noticias): 1x/día
  - Varios scrapers se comparten entre usuarios del mismo colegio (ej: calendario evaluaciones, casino, SC Info, noticias) — implementar cache compartido para no golpear la misma fuente N veces si hay N usuarios del mismo colegio
- **Organización del almacenamiento**: Revisar cómo se guarda la información obtenida. Debe quedar siempre ordenada por tópicos y fechas:
  - Estructura: `data/{user_id}/{topico}/{fecha}.json` o `data/{topico}/{colegio}/{fecha}.json` para datos compartidos
  - Histórico: mantener últimas 4 semanas de datos por tópico (para contexto y comparaciones)
  - Índice: archivo de metadatos que indique última actualización por tópico/usuario
  - Deduplicación: no volver a guardar lo que ya se obtuvo (usar hash o timestamp de última modificación)
- **Escalabilidad con múltiples usuarios**: Planificar qué pasa con 50-500 usuarios simultáneos:
  - SchoolNet: máximo 1 login concurrente por cuenta. Si hay 20 usuarios del mismo colegio, hacer 1 login con credenciales del colegio (no del apoderado) o serializar logins con delay de 30s entre cada uno
  - API calendario: es pública, pero limitar a 1 request por colegio por ciclo (no 1 por usuario)
  - Web del colegio: cachear respuesta por colegio (noticias, casino, SC Info son iguales para todos los apoderados del mismo colegio)
  - Implementar cola de scraping: agrupar usuarios por colegio, scrappear una vez por colegio y distribuir a todos los usuarios
  - Rate limit propio: máximo 1 request/segundo a cada dominio, backoff exponencial si hay error
- **Refactoring estructura de almacenamiento**: La estructura actual es plana (todo en `data/` sin separación por usuario/tópico). Propuesta de migración:
  ```
  data/
  ├── {user_id}/
  │   ├── bot_context.json          ← snapshot completo para el bot (se sobreescribe cada corrida)
  │   ├── calendario.json           ← eventos persistentes acumulativos (pruebas, reuniones, feriados)
  │   ├── whatsapp/
  │   │   ├── messages.json         ← mensajes recientes últimos 7 días
  │   │   └── history/              ← archivo semanal (whatsapp_2026_w29.json)
  │   ├── emails/
  │   │   └── latest.json           ← últimos 10 emails procesados
  │   ├── instrucciones.json        ← inputs manuales del apoderado
  │   └── meta.json                 ← {last_update: {gmail: "2026-07-21", schoolnet: "2026-07-21", ...}}
  ├── shared/
  │   └── {colegio_id}/
  │       ├── evaluaciones.json     ← calendario (compartido, 1 request por colegio)
  │       ├── casino.json           ← menú casino (compartido)
  │       ├── scinfo.json           ← SC Info (compartido)
  │       └── noticias.json         ← noticias web (compartido)
  └── outbox/
      └── {user_id}_{timestamp}.json
  ```
  Beneficios: separación por usuario (privacidad), datos compartidos no se re-scrappean, historial por tópico, fácil de limpiar (borrar carpeta de usuario = borrar todo su data).
  Estado actual: `bot_context` es 663K monolítico, `whatsapp_messages.json` mezcla todos los usuarios, no hay historial.


## Arquitectura a escala (100K usuarios)

### Supuestos
- 100K familias registradas, ~60% activas (60K con WA conectado)
- ~200 colegios (500 familias promedio)
- 2 resúmenes/día + semanal domingo
- ~10% preguntan al bot/día (6K preguntas/día)

### Componentes y costos

| Componente | Tecnología | Sizing | Costo/mes |
|---|---|---|---|
| WA Sessions | EC2 Spot Fleet (t3.xlarge, 16GB) | 60K ÷ 120/instancia = 500 instancias | $18,000 |
| Proxy residencial | IPRoyal static residential Chile (10 sesiones/IP) | 6,000 IPs | $12,000 |
| LLM Resúmenes | Gemini 2.0 Flash (batch) | 60K × 2/día × ~2K tokens | $600 |
| LLM Bot (preguntas) | Gemini Flash | 6K preguntas/día | $30 |
| DB (RAG + metadata + índices) | Aurora Serverless v2 (PostgreSQL + pgvector) | Única DB para todo | $200 |
| Storage | S3 (configs, tokens, PDFs, contextos) | ~50GB | $30 |
| Scraping | Lambda + SQS FIFO + EC2 Spot workers (Playwright) | 200 colegios + 60K users, serializado por colegio | $230 |
| Coordinación | EventBridge (cron) + CloudWatch | Scheduling + logs | $20 |
| **Total** | | | **~$31,100/mes** |

**Desglose scraping ($230/mes):**
- SQS FIFO: 3.6M requests/mes → $2
- Lambda dispatch_jobs + scrape_college + build_context: $48
- EC2 Spot workers (5× t3.medium, Playwright, ~3hr/día): $180
- EventBridge: $1

**Costo por usuario: ~$0.31/mes**
**Revenue (200 colegios × $1.3M): $260M CLP (~$260K USD/mes)**
**Margen infra: 88%**

### Costo por usuario a distintas escalas

| Usuarios activos | EC2 Fleet | IPRoyal | LLM | Aurora | Lambda+SQS | S3 | Total/mes | Por usuario/mes |
|---|---|---|---|---|---|---|---|---|
| 60 (1 colegio) | $36 | $15 | $5 | $25 | $1 | $1 | $83 | $1.38 |
| 300 (5 colegios) | $108 | $75 | $20 | $30 | $5 | $2 | $240 | $0.80 |
| 3,000 (50 colegios) | $900 | $750 | $60 | $50 | $20 | $5 | $1,785 | $0.60 |
| 15,000 (100 colegios) | $4,500 | $3,750 | $200 | $100 | $80 | $15 | $8,645 | $0.58 |
| 60,000 (200 colegios) | $18,000 | $12,000 | $630 | $200 | $230 | $30 | $31,090 | $0.52 |
| 100,000 (330 colegios) | $30,000 | $20,000 | $1,050 | $300 | $350 | $50 | $51,750 | $0.52 |

**El costo converge a ~$0.52/usuario/mes a escala.** Componentes dominantes: EC2 (58%) + IPRoyal (39%). LLM, DB y scraping son <3% combinados.

**Optimización futura:** A partir de 3,000+ IPs, negociar pricing bulk con IPRoyal o alternativas (SmartProxy, Bright Data, Oxylabs). Con volumen de 6,000-10,000 IPs residential Chile se puede bajar de $2.5/IP a $1-1.5/IP, reduciendo el costo total un 15-20%.

| Escala | Costo/usuario | Revenue/usuario | Margen |
|---|---|---|---|
| 60 usuarios (1 colegio) | $1.38 | $4.60 | 70% |
| 300 usuarios (5 colegios) | $0.80 | $4.60 | 83% |
| 3,000+ usuarios | $0.52-0.60 | $4.60 | 87-89% |

### Optimización EC2: Savings Plans

Con fleet estable 24/7 (WA sessions siempre activas), conviene comprometer uso a largo plazo:

| Capa | Tipo | Descuento vs On-Demand | Riesgo |
|---|---|---|---|
| Base estable (70% del fleet) | Compute Savings Plan 3 años | -72% | Pagas aunque no uses |
| Elasticidad (30% del fleet) | Spot (como hoy) | -65% | Interrupciones (mitigado con Fleet) |

**Ejemplo a 60K usuarios (500 instancias):**
| Estrategia | EC2/mes | Total infra/mes | Por usuario |
|---|---|---|---|
| Spot puro (hoy) | $18,000 | $31,090 | $0.52 |
| Savings Plan 70% + Spot 30% | $7,400 | $20,490 | $0.34 |

**Margen con Savings Plan: 93%** (vs 89% con Spot puro)

**Cuándo comprometer:**
| Etapa | Estrategia EC2 |
|---|---|
| Año 1 (creciendo, <50 colegios) | Spot puro — sin compromiso, flexibilidad total |
| Año 2 (estable, 50-100 colegios) | Savings Plan 1 año para 70% de la base |
| Año 3+ (fleet estabilizado) | Savings Plan 3 años — máximo descuento |

### Scraping: por colegio vs por usuario

| Fuente | Nivel | Frecuencia |
|---|---|---|
| Calendario evaluaciones (API JSON) | Por colegio (compartido) | 1x/día |
| Casino/menú | Por colegio (compartido) | 1x/día AM |
| SC Info / noticias web | Por colegio (compartido) | 1x/día |
| SchoolNet notas/asistencia/conducta | Por usuario | 2x/día |
| SchoolNet compañeros | Por curso (compartido) | 1x/mes |
| SchoolNet pagos/cobranza | Por usuario | 1x/día |
| SchoolNet extraprogramáticas | Por usuario | 1x/mes |
| Gmail | Por usuario | 2x/día |
| WhatsApp mensajes | Por grupo (tiempo real via wa_listener) | Continuo |

### Flujo de scraping

```
EventBridge (06:30 AM / 18:30 PM)
         │
         ▼
Lambda "dispatch_jobs"
├── Cola COLEGIO (SQS, 200 msgs) → Lambda scrape_college (HTTP/API, sin browser)
│   └── Resultado → S3 shared/{colegio_id}/
└── Cola USUARIO (SQS, 60K msgs) → EC2 Fleet workers (Playwright, serializado por colegio)
    └── Resultado → S3 users/{user_id}/
         │
         ▼ (S3 Event trigger)
Lambda "build_context"
├── Combina shared + user data → bot_context_{user_id}.json
└── Actualiza Aurora pgvector con chunks nuevos
```

### Timing de ejecución (resúmenes siempre a la hora)

El resumen debe llegar al apoderado a hora fija (7:00 AM / 20:00 PM). El scraping y procesamiento deben estar **listos antes** de esa hora.

**Flujo actual (secuencial, 1 EC2):**
```
06:50 → scrape SchoolNet (40s) → scrape Gmail (10s) → build context (5s) → generar resumen (3s) → enviar WA
Total: ~60s → resumen llega ~06:51 ✅ (funciona con pocos usuarios)
```

**Flujo a escala (100K usuarios, paralelo):**
```
05:00  EventBridge trigger "morning_scrape"
       └── dispatch_jobs → SQS FIFO por colegio
       
05:00-06:30  EC2 workers procesan cola (60K scrapes, serializado por colegio)
             └── Cada scrape: login + datos → S3 → trigger build_context
             
06:30  Deadline: todos los scrapes deben estar listos
       └── Si alguno falló, usar datos del día anterior (fallback)
       
06:45  EventBridge trigger "generate_summaries"
       └── Lambda batch: lee contextos de S3 → Gemini Flash batch → outbox
       
07:00  wa_listener envía desde outbox (ya tiene mensajes listos)
       └── 60K mensajes en ~15 minutos (throttled para no parecer spam)
```

**Tiempos por etapa a escala:**
| Etapa | Duración | Por qué |
|---|---|---|
| Scraping 60K usuarios | ~150 min (ventana distribuida) | Jitter aleatorio para no generar peak |
| Build context | ~10 min | Lambda triggered por S3, 60K invocaciones en paralelo |
| Generar resúmenes (Gemini batch) | ~15 min | 60K prompts batch API |
| Enviar WA | ~15 min | Throttled, 60K mensajes |

**Anti-detección: scraping distribuido con jitter variable**

NO arrancar todos los scrapes a la misma hora. Distribuir con offset aleatorio por usuario dentro de una ventana:
- **AM:** ventana de scraping 04:00-06:30 (2.5 horas)
- **PM:** ventana de scraping 16:00-19:30

Formula: `scrape_time = base_hour + (hash(user_id + day_of_year) % window_minutes)`

El `day_of_year` hace que el mismo usuario se scrapee a hora distinta cada día (lunes 04:37, martes 05:12, miércoles 04:55). Desde SchoolNet se ve como un humano real que abre la app a distintas horas. Imposible distinguir de tráfico orgánico.

**Aplica a:** Toda plataforma con login de usuario (SchoolNet/Colegium, Lirmi, Cuaderno Rojo, Pronote, LaFase). NO aplica a APIs públicas (calendario JSON, casino, noticias, Gmail API) ni a WA (sesión persistente 24/7).

### Onboarding: usuario nuevo (prioridad alta)

Cuando un usuario se registra por primera vez en la landing, necesita datos INMEDIATOS (hijos detectados, extraprogramáticas, primer resumen). No puede esperar al próximo ciclo diario (podría ser 12+ horas).

**Onboarding en 2 fases:**

| Fase | Qué hace | Duración | El usuario espera? |
|---|---|---|---|
| **Fase 1: Detección rápida** | Login + detectar hijos (nombre, curso, profe) | ~30s | Sí (landing muestra spinner) |
| **Fase 2: Scrape completo** | Extraprogramáticas, notas, asistencia, pagos, Gmail, build context, primer resumen | ~3 min | No (background) |

**Flujo:**
```
Landing paso 4 (scraping) — usuario ESPERANDO
         │
         ▼
API Lambda → SSM directo a EC2: "scrape_for_user.py --fast"
         │
         ├── Login SchoolNet (15s)
         ├── Detectar hijos desde asistencia/index (10s)
         ├── Guardar resultado en S3 (hijos + cursos + profesores)
         └── LISTO → landing muestra "Datos detectados" (30s total)

Usuario avanza (paso 5, 6, 7 — elige grupos WA, vincula, régimen)
         │
         ▼ (cuando completa landing)
API Lambda → encola en priority-queue: scrape completo
         │
         ▼ (background, usuario ya no espera)
Worker procesa:
  1. Login SchoolNet → extraprogramáticas (forzado) (60s)
  2. Notas + asistencia + pagos + conducta (30s)
  3. Gmail: últimos 7 días (10s)
  4. Build context + generar primer resumen (10s)
  5. Enviar por WA + crear grupo monitor (30s)
  Total: ~3 minutos → usuario recibe primer mensaje WA
```

**Fase 1 NO pasa por cola** — es comando SSM directo (como hoy). Solo 1 login rápido de 30s. No causa rate limit incluso con 500 simultáneos (cada uno usa credenciales distintas).

**Corrección: Fase 1 también pasa por cola (`fast-queue`)** — por si 500 apoderados se registran al mismo momento en el evento de lanzamiento del colegio. Sin cola, serían 500 comandos SSM simultáneos a la misma EC2 (colapsa).

**3 colas:**
| Cola | Propósito | Concurrencia | Latencia esperada |
|---|---|---|---|
| `fast-queue` | Fase 1: detectar hijos (landing esperando) | 10 concurrentes por colegio | <60s por usuario |
| `priority-queue` | Fase 2: scrape completo de onboarding | 5 concurrentes por colegio | ~3 min por usuario |
| `daily-queue` | Ciclo diario AM/PM | 3 concurrentes por colegio, jitter | Ventana 2.5 horas |

**Workers leen en orden:** `fast-queue` → `priority-queue` → `daily-queue`

Fase 1 con cola: usuario espera máximo ~60s (su posición ÷ 10 concurrentes × 30s cada uno). Con 500 simultáneos del mismo colegio: usuario #500 espera ~25 min. Pero en la práctica, 500 simultáneos no pasan — se registran en oleadas de 10-20 por hora.

**UX de espera:** La landing consulta `/api/scrape-status` que devuelve posición en la cola + tiempo estimado:
```json
{"status": "queued", "position": 12, "estimated_seconds": 60}
{"status": "processing", "position": 0, "estimated_seconds": 20}
{"status": "done", "result": {hijos: [...]}}
```
La landing muestra: "Conectando con SchoolNet... se demorará aproximadamente 1 minuto" (actualiza en tiempo real). Si la espera supera 2 minutos, ofrecer "Puedes continuar y te avisamos por WhatsApp cuando esté listo" con opción de agregar hijos manualmente mientras tanto.

**Fase 2 SÍ pasa por priority-queue** — se serializa por colegio, respeta rate limit, pero tiene prioridad sobre la cola diaria.

**Asignación de IP residencial:** Al momento de encolar en fast-queue, se asigna una IP del pool de IPRoyal (la que tenga menos de 10 usuarios). Desde ese instante, TODO el tráfico del usuario (fase 1, fase 2 y daily) sale por esa IP. Así SchoolNet ve siempre el mismo "hogar" desde el primer login.

**Auto-scaling: cuándo levantar nueva instancia**

Cada EC2 soporta ~120 sesiones WA. Cuando se registra el usuario #121 (o el que supere el threshold de la instancia actual):

```
Onboarding usuario nuevo
         │
         ▼
Lambda "assign_user" consulta Aurora:
  - ¿Hay instancia con capacidad libre? (< 120 usuarios)
    → SÍ: asignar usuario a esa instancia
    → NO: solicitar nueva instancia al Fleet
         │
         ▼
EC2 Fleet "modify-fleet" (target_capacity += 1)
         │
         ▼
Nueva instancia Spot levanta (AMI pre-baked):
  ┌─────────────────────────────────────────────┐
  │ AMI ya tiene: Node, Playwright, código,      │
  │ dependencias pre-instaladas                  │
  │                                              │
  │ User Data (solo configs, ~10s):              │
  │ 1. Registrar en Aurora como "booting"        │
  │ 2. Sync configs desde S3 (users, tokens)     │
  │ 3. Asignar bloque de IPs IPRoyal del pool    │
  │ 4. Start wa-listener + spot-handler + worker │
  │ 5. Marcar como "ready" en Aurora             │
  └─────────────────────────────────────────────┘
         │
         ▼ (30-40 segundos con AMI pre-baked)
         
Lambda "assign_user" detecta instancia ready → asigna usuario
```

**Tiempos de boot:**
| Approach | Tiempo |
|---|---|
| User Data instala todo desde cero | 60-90s |
| **AMI pre-baked** (producción) | **30-40s** |
| AMI pre-baked + EBS snapshot con data | 20-30s |

AMI se rebuild automáticamente con CI/CD en cada deploy.

**Triggers de scaling:**
| Evento | Acción | Latencia |
|---|---|---|
| Scale UP: `assign_user` no encuentra instancia con espacio | `modify-fleet +1` | Instantáneo (30-40s boot) |
| Scale DOWN + Rebalanceo: check 1x/día (3:00 AM) | Migrar, consolidar, equilibrar | Madrugada (nadie nota 30s reconexión) |
| Spot interruption: AWS reclama instancia | Fleet auto-replace + redistribuir usuarios | Automático (~60s) |

### Estados de usuario

| Estado | Qué significa | WA activo? | Scraping? | Resúmenes? | Ocupa slot EC2? |
|---|---|---|---|---|---|
| **active** | Funcionando normal | ✅ | ✅ | ✅ | ✅ |
| **paused** | Usuario pidió pausar (vacaciones, etc.) | ✅ (bot responde) | ❌ | ❌ | ✅ |
| **disconnected** | WA desconectado (logout, cambió teléfono) | ❌ | ❌ | ❌ | ❌ (liberar slot) |
| **cancelled** | Colegio canceló o usuario pidió baja | ❌ | ❌ | ❌ | ❌ (liberar slot) |

**Triggers de cambio de estado:**
| De → A | Trigger |
|---|---|
| active → paused | Usuario manda "pausar" al bot / admin |
| active → disconnected | Baileys detecta `loggedOut` automáticamente |
| active → cancelled | Admin marca baja / colegio cancela contrato |
| paused → active | Usuario manda "activar" / admin reactiva |
| disconnected → active | Usuario re-vincula QR desde landing |

**En Aurora:**
```sql
users: {
  user_id, status, instance_id, ip_residential, colegio_id,
  cancelled_at, disconnect_reason, last_active_at
}
```

Solo `status = 'active' OR 'paused'` ocupan slot en EC2.

### Post-Spot interruption: redistribución

```
Instancia A muere (120 usuarios huérfanos)
         │
         ▼
Fleet auto-replace → nueva instancia C levanta (vacía, 30-40s)
         │
         ▼
Lambda "redistribute":
  1. Buscar usuarios con instance_id = instancia_A (huérfanos)
  2. Distribuir uniformemente entre instancias con espacio (máximo 110 por instancia)
  3. Sync baileys_auth de cada usuario a su nueva instancia
  4. Actualizar user_assignments en Aurora
  5. wa_listener reconecta sesiones automáticamente
```

### Check nocturno (3:00 AM) — scale down + rebalanceo

```sql
-- 1. Scale down: instancias subutilizadas
SELECT instance_id FROM instances 
WHERE current_users < 30 AND status = 'ready'
→ Migrar usuarios a instancias con espacio, apagar instancia

-- 2. Rebalanceo: detectar distribución desigual
SELECT MAX(current_users) - MIN(current_users) as diff FROM instances WHERE status = 'ready'
→ Si diff > 40: mover usuarios de la más llena a la más vacía hasta equilibrar
```

**¿Por qué 1x/día?**
- Scale down ocurre raramente (churn 10%/año = ~1 usuario/mes por instancia)
- Caso más común: colegio completo cancela (500 usuarios = 4 instancias liberadas de golpe)
- Rebalanceo post-interruption ya se hace inmediato. El check nocturno es limpieza residual
- Madrugada = mínimo impacto (30s reconexión mientras duermen)

**Cola prioritaria de onboarding:**
```
Landing completa registro
         │
         ▼
API Lambda "welcome" → encola en SQS cola PRIORITY (no la cola normal)
         │
         ▼
Worker procesa INMEDIATAMENTE (cola priority tiene prioridad sobre la cola diaria):
  1. Login SchoolNet → detectar hijos (30s)
  2. Scrape extraprogramáticas (forzado, ignorar cache) (60s)
  3. Scrape notas + asistencia + pagos (30s)
  4. Gmail: leer últimos 7 días de emails (10s)
  5. Build context completo (5s)
  6. Generar primer resumen de bienvenida (3s)
  7. Enviar por WA + crear grupo monitor (30s)
  Total: ~3 minutos
```

**Diferencias con el ciclo diario:**
| Aspecto | Ciclo diario | Onboarding |
|---|---|---|
| Cola | `daily-queue` (SQS FIFO, jitter) | `priority-queue` (procesamiento inmediato) |
| Extraprogramáticas | Skip si ya hay cache | Forzar scrape (siempre) |
| Datos compartidos (casino, evaluaciones) | Cache por colegio | Usar cache si existe, sino scrappear |
| Resumen | AM o PM según hora | Siempre generar (bienvenida) |
| Timeout | Puede esperar horas | Máximo 5 minutos (landing muestra progreso) |

**Cómo conversan las dos colas:**

Los EC2 workers tienen un loop que lee de AMBAS colas, pero priority primero:

```python
while True:
    # 1. SIEMPRE revisar priority primero
    msg = sqs.receive_message(queue="priority-queue", wait_time=0)
    
    if not msg:
        # 2. Si no hay onboarding pendiente, procesar cola diaria
        msg = sqs.receive_message(queue="daily-queue", wait_time=20)
    
    if msg:
        process(msg)
```

Esto garantiza que:
- Un onboarding NUNCA espera detrás de la cola diaria
- La cola diaria se procesa normalmente cuando no hay onboardings
- Si llegan 50 onboardings mientras se procesan los diarios, los workers PAUSAN los diarios y atienden los priority
- Los mensajes de daily-queue no se pierden (SQS los retiene, se procesan después)

**Rate limit compartido:** Ambas colas respetan el mismo semáforo por colegio. Si `daily-queue` ya tiene 3 logins activos para "sagrado_corazon", un msg de `priority-queue` del mismo colegio espera a que se libere 1 slot (pero con más prioridad que el siguiente daily).

```
                    ┌──────────────────┐
Landing registro →  │ priority-queue   │ ──┐
                    └──────────────────┘   │
                                           ▼
                    ┌──────────────────┐  ┌─────────────────────┐
EventBridge cron →  │ daily-queue      │  │ EC2 Workers (pool)  │
                    └──────────────────┘  │                     │
                           │              │  1. Read priority    │
                           └──────────────│  2. If empty → daily│
                                          │  3. Rate limit check│
                                          │     por colegio     │
                                          └─────────┬───────────┘
                                                    │
                                                    ▼
                                              ┌───────────┐
                                              │ S3 + Aurora│
                                              └───────────┘
```

**Caso 500 onboardings simultáneos del mismo colegio:**
- priority-queue se llena con 500 msgs
- Workers leen de priority pero el rate limit por colegio (5 concurrentes × 3s delay) los serializa
- Cada usuario espera ~(posición ÷ 5) × 3 minutos
- Usuario #1: 3 min, Usuario #50: ~30 min, Usuario #500: ~5 horas
- La landing muestra: "Tu cuenta se está configurando. Te avisamos por WhatsApp cuando esté lista."
- NO bloquear la landing — el usuario completa registro, se va, y recibe el primer resumen cuando esté listo

**Conclusión:** El scraping debe empezar **2.5 horas antes** del envío:
- AM: scraping ventana 04:00-06:30, envío a las 07:00
- PM: scraping ventana 16:00-19:30, envío a las 20:00
- Máximo 3 logins SchoolNet concurrentes por colegio (serializar con SQS FIFO por colegio_id)
- Delay 5s entre logins del mismo colegio
- Backoff exponencial si SchoolNet devuelve error
- 1 IP residencial por cada 10 sesiones WA (IPRoyal Chile)
- **Scraping SchoolNet sale por la misma IP residencial del usuario** — los 10 usuarios que comparten 1 IP también scrappean por esa IP. Desde Colegium se ve como máximo 10 logins distintos desde la misma IP (simula un hogar). Zero riesgo de ban.

### Alta disponibilidad Spot (migración en 2 minutos)

Las EC2 Spot pueden ser reclamadas por AWS con 2 minutos de aviso. El servicio de WA debe estar ~100% online.

**Flujo de interrupción:**
```
Spot Interruption Notice (2 min aviso)
         │
         ▼
spot_handler detecta señal (polling metadata cada 5s)
         │
         ├── 1. Flush outbox (enviar mensajes pendientes, ~5s)
         ├── 2. Sync baileys_auth/ → S3 (~10-15s para 100MB)
         ├── 3. Sync data/ → S3 (bot_context, eventos, mensajes WA)
         ├── 4. Marcar instancia como "draining" en Aurora
         └── 5. Graceful shutdown wa_listener
         
EC2 Fleet Auto-Replace (automático)
         │
         ▼
Nueva instancia levanta (Launch Template + User Data)
         ├── 1. Sync baileys_auth/ ← S3 (~15s)
         ├── 2. Sync config/ ← S3
         ├── 3. Start wa_listener (Baileys reconecta sesiones automáticamente, sin QR)
         ├── 4. Start spot_handler (monitoreo de próxima interrupción)
         └── 5. Ready en ~30-60s
```

**Downtime real:** 30-60 segundos (tiempo de boot nueva instancia + sync + reconexión Baileys). Los mensajes que lleguen durante ese tiempo se entregan cuando Baileys reconecta (WhatsApp los buferea server-side).

**Implementación:**
- EC2 Fleet con `maintain` target capacity (AWS reemplaza automáticamente instancias reclamadas)
- Launch Template con User Data que hace sync desde S3 + start servicios
- `spot_handler.sh` como systemd service que polling `/latest/meta-data/spot/instance-action`
- Alternativa: EventBridge rule `EC2 Spot Instance Interruption Warning` → Lambda que trigguea sync

**Escala:**
- 1 instancia (hoy): Fleet de 1, auto-replace
- 500 instancias (100K users): Fleet distribuye sesiones entre instancias. Si 1 muere, sus 120 usuarios reconectan en otra instancia del fleet. Zero intervención manual.

### Bot context: modelo híbrido

```
Contexto FIJO (siempre en el prompt, ~5K tokens):
- Hijos + cursos + profesores
- Horario de hoy/mañana
- Extraprogramáticas de hoy/mañana
- Calendario próximos 5 días
- Régimen custodia

RAG via Aurora pgvector (se busca solo si la pregunta lo requiere):
- Compañeros (contacto, padres, dirección)
- Notas/calificaciones completas
- Historial de emails
- Mensajes WA
- Pagos/cobranza
- Conducta/anotaciones
```

### Migración progresiva

| Etapa | Usuarios | Infra | Costo/mes |
|---|---|---|---|
| Hoy | 1-10 | 1 EC2 Spot + S3 | $50 |
| Año 1 | 500-5K | 5 EC2 + Aurora Serverless + SQS | $500 |
| Año 2 | 5K-50K | EC2 Fleet (50) + Aurora + Lambda scrapers + IPRoyal | $5K |
| Año 2-3 | 50K-100K | EC2 Fleet (500) + Aurora + Lambda + IPRoyal (6K IPs) | $31K |


## Plan de contratación

### Costos de equipo

| Rol | Base/mes | Comisión | Total estimado/mes (con carga) |
|---|---|---|---|
| Fundador (Pablo) | - | - | $8.000.000 (sueldo objetivo) |
| Vendedor | $800.000-1.000.000 | 12% del primer año por colegio nuevo | ~$3.000.000 promedio |
| IT/Respaldo | $1.500.000-2.000.000 | - | ~$2.500.000 |

**Total equipo completo: $13.500.000/mes**

### Comisión del vendedor (detalle)
- Colegio mediano (800 alumnos): contrato $15.6M/año × 12% = $1.870.000 por colegio cerrado
- Si cierra 2 colegios/mes: base $1M + comisiones $3.7M = $4.7M (meses buenos)
- Promedio mensualizado: ~$3M/mes (incluye meses sin cierre)

### Cuándo contratar

| Hito | Colegios activos | Ingreso/mes | Acción |
|---|---|---|---|
| Solo | 1-4 | $1.3-5.2M | Vender + operar solo |
| +Vendedor | 5 | $6.5M | Contratar vendedor (se paga solo con 1 colegio nuevo) |
| +IT | 8 | $10.4M | Contratar respaldo IT (onboarding + soporte) |
| Equipo completo | 11+ | $14.3M+ | Cubiertos todos los costos con margen |

### Breakeven con equipo completo

| Colegios | Ingreso/mes | Gasto total/mes | Margen libre/mes |
|---|---|---|---|
| 11 | $14.300.000 | $13.500.000 | $800.000 |
| 13 | $16.900.000 | $13.500.000 | $3.400.000 |
| 15 | $19.500.000 | $13.500.000 | $6.000.000 |
| 20 | $26.000.000 | $13.500.000 | $12.500.000 |

### Proyección con equipo (año 2)

Asumiendo vendedor cierra 2-3 colegios/mes:

| Mes (año 2) | Colegios | Ingreso/mes | Profit después de costos |
|---|---|---|---|
| 1 | 12 | $15.600.000 | $2.100.000 |
| 3 | 16 | $20.800.000 | $7.300.000 |
| 6 | 22 | $28.600.000 | $15.100.000 |
| 12 | 34 | $44.200.000 | $30.700.000 |

**Año 2 con equipo: ~$250M ingreso / ~$180M profit**



## Expansión vertical

### Módulos premium (upsell a colegios existentes)

| Módulo | Cobro extra/mes | Descripción |
|---|---|---|
| Alertas de inasistencia | $300-500K | Aviso en tiempo real al apoderado si el hijo no llegó al colegio |
| Reportes de engagement | $200-300K | Dashboard para el colegio: qué apoderados leen, cuáles no responden |
| Canal bidireccional | $500-800K | Apoderado responde en el grupo WA y llega organizado al colegio |
| Recordatorio de pagos | $300-500K | "Tu cuota vence en 3 días" — reduce morosidad |

**Impacto:** con 10 colegios comprando 2 módulos extra → +$6-10M/mes adicionales.

### Otros segmentos educativos

| Segmento | Tamaño (Chile) | Pricing/mes | Adaptación necesaria |
|---|---|---|---|
| Jardines infantiles | 5.000+ | $500-800K | Simplificar (menos fuentes, foco en rutina diaria) |
| Colegios subvencionados | 6.000+ | $300-500K | Precio más bajo, más volumen. Muchos usan Alexia/Syscol |
| Universidades (padres de mechones) | 60+ | $2-5M | Fuentes distintas (portal alumno, emails, calendario académico) |
| Preuniversitarios | 200+ | $500-1M | Resultados de ensayos, horarios, simulacros |

### Expansión geográfica (Latam)

Mismo producto, misma infra. Seguir la base de Colegium/Alexia en cada país.

| País | Colegios particulares | Pricing estimado (USD/mes) | Plataformas dominantes |
|---|---|---|---|
| Colombia | 5.000+ | $500-1.000 | Colegium, Phidias, CiberColegio |
| Perú | 3.000+ | $400-800 | Colegium, Sieweb |
| México | 15.000+ | $600-1.200 | Colegium, Educamos |
| Argentina | 4.000+ | $300-600 | Colegium, Aulica |
| Chile (liceos franceses) | 10+ | $500-1.000 | Pronote (Index Éducation) |

**Requisitos para Latam:**
- Adaptar scraping a plataformas locales (Phidias, Sieweb, etc.)
- WhatsApp funciona igual en toda Latam (misma infra)
- Proxy residencial por país (~mismos proveedores)
- Gemini/Claude funciona igual (español neutro)

### Roadmap de expansión

| Fase | Timing | Foco | Ingreso adicional esperado |
|---|---|---|---|
| 1. Módulos premium | Mes 8-12 (año 1) | Alertas + reportes a colegios existentes | +$3-5M/mes |
| 2. Jardines infantiles | Año 2 Q1 | Nuevo segmento Chile, pricing más bajo | +$3-5M/mes |
| 3. Colombia | Año 2 Q2 | Primer país Latam, 5-10 colegios | +$5-10M/mes |
| 4. Subvencionados | Año 2 Q3 | Volumen Chile (requiere precio bajo) | +$5-10M/mes |
| 5. México + Perú | Año 3 | Escala Latam | +$20-50M/mes |


## Data como producto

### Activo principal: canal directo con el apoderado por WhatsApp

Con miles de apoderados conectados vía WhatsApp, el canal es el activo más valioso del negocio — más que la tecnología o los resúmenes. Permite comunicación push directa, personalizada, con tasa de lectura >95%.

### Data extraíble de grupos WA (agregada, anonimizada)

| Data | Ejemplo | Cliente potencial |
|---|---|---|
| Temas más discutidos/mes | "Oct: 40% uniformes, 30% transporte, 20% evaluaciones" | El colegio (anticipar problemas) |
| Sentimiento de apoderados | "Semana 15-jul: sentimiento negativo por cambio horario" | Dirección del colegio |
| Preguntas frecuentes no resueltas | "35% pregunta lo mismo: ¿hora de salida?" | Colegio (mejorar comunicación) |
| Detección de conflictos | "Grupo 3°B: tensión alta, tema bullying" | Convivencia escolar |
| Influenciadores de opinión | "3 apoderados generan 60% de conversaciones" | Dirección (gestión de stakeholders) |
| Necesidades no cubiertas | "Se menciona 'furgón' 50 veces/mes" | Empresas de transporte escolar |
| Efectividad de comunicaciones del colegio | "70% leyó la circular, 30% sigue preguntando" | Comunicaciones del colegio |

### Cierre del loop de comunicación (upsell al colegio)

El colegio hoy manda circulares sin saber si se leyeron ni qué efecto tuvieron. Con nuestra data:
- "El 70% de los apoderados leyó la circular del lunes"
- "En el grupo de 5°A siguen preguntando por la fecha del paseo — la comunicación no fue clara"
- "El cambio de horario generó 45 mensajes negativos en 2 horas — intervenir"

Esto se puede empaquetar como módulo "Analytics de Comunicación Escolar" — $500K-1M extra/mes por colegio.

### Monetización del canal (con cautela)

| Producto | Descripción | Quién paga | Pricing |
|---|---|---|---|
| Ofertas segmentadas | "Feria uniformes sábado" a apoderados de 1°-4° | Empresas de uniforme | $200-500K/campaña |
| Encuestas rápidas | "¿Inscribirías a tu hijo en robótica?" | Empresas de talleres | $300-800K/encuesta |
| Promoción de eventos | "Obra infantil, 20% dcto familias SC" | Productoras | $100-300K/envío |

**⚠️ Riesgo:** si el apoderado siente spam, pierde confianza. Solo con consentimiento explícito y contenido de valor real para la familia.

### Timing
- Módulo Analytics: viable con 10+ colegios (año 1)
- Monetización del canal: viable con 50+ colegios y opt-in del apoderado (año 2-3)
- Venta de data agregada: viable con 100+ colegios (año 3+)


## Módulos premium detallados

### Módulo 1: Canal de comunicación directa + Read Receipts ($1M extra/mes)

**Qué incluye:**
- El colegio envía comunicados urgentes vía nuestro canal WA (95% lectura vs 25% email)
- Reporte de lectura: quién leyó, quién no, por curso
- Alerta: "estos 15 apoderados no leyeron la comunicación del viernes"

**Implementación técnica (pendiente):**
- Agregar listener de `messages.update` en wa_listener.js para detectar read receipts (doble check azul)
- Guardar log por mensaje: {msg_id, destinatario, enviado_at, leido_at}
- Endpoint API para que el colegio vea reportes

**Valor para el colegio:** elimina el problema #1 ("no me avisaron") con evidencia objetiva.

### Módulo 2: Inteligencia de grupos WA ($700K extra/mes)

**Qué incluye:**
- Reporte semanal de clima escolar por curso (sentimiento, temas top, alertas)
- Alertas en tiempo real de conflictos ("12 mensajes negativos sobre tema X en última hora")
- Detección de desinformación ("se dice en grupo que mañana no hay clases — es falso")
- Identificación de preguntas frecuentes no resueltas

**Para quién:**
- Director: visión general, anticipar conflictos
- Convivencia escolar: detección temprana bullying/tensión
- Comunicaciones: qué se entendió mal, qué reforzar
- Profesores jefe: qué se dice de su curso

**Implementación técnica:**
- Análisis semanal con AI (Gemini/Claude) de mensajes agregados por grupo
- Clasificación de sentimiento (positivo/negativo/neutro)
- Extracción de temas recurrentes
- Alertas si sentimiento negativo supera umbral

### Pricing full stack

| Módulo | Cobro/mes |
|---|---|
| Base (resúmenes a apoderados, hasta 500 alumnos) | $1.000.000 |
| Canal de comunicación directa + read receipts | $1.000.000 |
| Inteligencia de grupos WA | $700.000 |
| Alumno extra (sobre 500) | $1.000/alumno |
| **Total colegio mediano (800 alumnos, full)** | **$3.000.000/mes** |

### Proyección con módulos premium

| Colegios (full stack $3M) | Ingreso/mes | Para tu sueldo ($8M) |
|---|---|---|
| 3 | $9.000.000 | ✅ Cubierto |
| 5 | $15.000.000 | + 1 persona |
| 7 | $21.000.000 | + equipo de 3 |
| 10 | $30.000.000 | Escala Latam |


## Plan Comercial

### Producto: Monitor Colegio
Servicio B2B para colegios particulares. Resúmenes diarios automáticos por WhatsApp para apoderados + inteligencia de comunicación para la dirección.

### Paquetes

| Paquete | Incluye | Precio/mes |
|---|---|---|
| **Básico** | Resúmenes AM/PM por WA, calendario, fuentes del colegio. Hasta 500 alumnos. | $1.000.000 + $1.000/alumno extra |
| **Full** | Básico + canal directo del colegio por WA + read receipts + reportes de lectura + inteligencia de grupos WA (sentimiento, alertas, insights semanales) | $2.700.000 + $1.000/alumno extra |

### Condiciones
- Primer mes gratis (prueba)
- Contrato mínimo 12 meses
- Setup incluido
- Precios en UF (ajuste IPC automático)

### Target
- Colegios particulares pagados de Santiago
- Comunas: Las Condes, Vitacura, Lo Barnechea, La Dehesa, Providencia, Ñuñoa
- Mensualidad alumno >$300K
- Usan SchoolNet/Colegium u otra plataforma digital
- **Plataformas soportadas/planificadas:** SchoolNet (Colegium), Lirmi, LaFase, Pronote, Cuaderno Rojo, Oxford School
- 300-1500 alumnos

### Propuesta de valor por audiencia

**Para el Director:**
- "Visibilidad total de lo que pasa en los grupos de apoderados"
- "Reducción de conflictos por desinformación"
- "Diferenciación vs otros colegios (innovación)"
- "Benchmark anónimo de notas: cómo se compara tu colegio vs otros en promedio por asignatura y nivel (dato agregado, sin identificar alumnos)"

**Para Administración / Finanzas:**
- "Recordatorio de pago directo por WhatsApp (95% lectura) → reduce morosidad"
- "El apoderado recibe su aviso de cobranza con monto, fecha y un recordatorio amable — no tiene que abrir la app del colegio"
- "Benchmark de morosidad: ¿tu colegio cobra más rápido o más lento que el promedio? Datos agregados de colegios similares"
- "Acelera el ciclo de pago: el aviso llega por el canal que el apoderado SÍ lee (WA), no por email que ignora 3 semanas"

**Para Comunicaciones:**
- "95% de lectura por WA vs 25% por email"
- "Saber exactamente quién no leyó una comunicación"
- "Canal directo al apoderado sin depender de email ni app"

**Para los Apoderados (el usuario final):**
- "Nunca más te pierdes una prueba, reunión o actividad"
- "Todo resumido en 1 mensaje de WhatsApp, 2 veces al día"
- "5 minutos de setup, 0 esfuerzo después"

### Benchmark como herramienta de venta

Con datos de múltiples colegios (a partir de 5+), podemos ofrecer reportes comparativos anonimizados:

| Benchmark | Qué mide | Valor para el colegio |
|---|---|---|
| **Morosidad comparada** | Días promedio de atraso en pago vs otros colegios del mismo segmento | "Tu colegio cobra en 18 días promedio, el benchmark es 12. Con nuestros recordatorios WA bajamos a 10." |
| **Velocidad de pago post-aviso** | Cuántas horas/días después del aviso WA se paga vs email | "Con email el apoderado paga en 8 días. Con nuestro aviso WA paga en 2.5 días." |
| **Promedios por asignatura** | Notas promedio por curso/asignatura vs otros colegios similares | "Tu 5° básico tiene 5.8 en Matemáticas, el benchmark de colegios similares es 6.1" |
| **Engagement de apoderados** | % que lee comunicaciones, pregunta al bot, responde encuestas | "85% de tus apoderados leen el resumen diario. En otros colegios sin WA es 25%." |

**Pitch para el colegio:** "No solo mejoramos la comunicación — te mostramos cómo te comparas con otros colegios y te ayudamos a cobrar más rápido."

**Dato clave:** Un colegio de 800 alumnos con mensualidad de $400K y morosidad de 15% pierde $48M/mes en flujo de caja. Si reducimos morosidad de 15% a 8% con recordatorios WA, el colegio recupera $22M/mes adicionales. **Nuestro servicio de $1.3M/mes se paga solo 17 veces con la reducción de morosidad.**

### Plan de ventas primer año

| Etapa | Mes | Acción | Meta |
|---|---|---|---|
| Piloto | 1 | Sagrado Corazón como caso de éxito (gratis) | Testimonial + métricas |
| Lanzamiento | 2-3 | Contactar 10 colegios similares. Ofrecer mes gratis. | 2-3 colegios en prueba |
| Tracción | 4-6 | Referidos + networking directo. Cerrar contratos anuales. | 5 colegios pagando |
| Crecimiento | 7-9 | Contratar vendedor. Módulos premium. | 8-10 colegios |
| Escala | 10-12 | Equipo completo. Segundo segmento (jardines/subvencionados). | 12+ colegios |

### Proyección financiera primer año (paquete Básico $1.3M/colegio mediano)

| Mes | Colegios | Ingreso | Costos (infra + equipo) | Profit |
|---|---|---|---|---|
| 1-3 | 0→2 | $3.900.000 acum | $57.000 | $3.843.000 |
| 4-6 | 3→5 | $15.600.000 acum | $285.000 | $15.315.000 |
| 7-9 (+ vendedor) | 6→8 | $27.300.000 acum | $9.500.000 | $17.800.000 |
| 10-12 (+ IT) | 9→10 | $38.350.000 acum | $17.000.000 | $21.350.000 |
| **Total año 1** | **10** | **$85.150.000** | **$26.842.000** | **$58.308.000** |

### Proyección año 2 (con equipo, módulos premium, 2-3 colegios/mes nuevos)

| Trimestre | Colegios | Ingreso acumulado trimestre | 
|---|---|---|
| Q1 | 13-16 | $50-60M |
| Q2 | 17-22 | $70-85M |
| Q3 | 23-28 | $90-110M |
| Q4 | 29-34 | $110-135M |
| **Total año 2** | **34** | **$320-390M** |

### Métricas clave (KPIs)

| Métrica | Meta año 1 | Meta año 2 |
|---|---|---|
| Colegios activos | 10 | 34 |
| Tasa de adopción (familias registradas/total) | >50% | >65% |
| Churn anual | <10% | <10% |
| NPS apoderados | >60 | >70 |
| Ingreso mensual recurrente (MRR) | $13M | $45M |

### Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Colegium copia la feature | Media | Velocidad de ejecución + módulos que ellos no pueden hacer (WA bidireccional) |
| Meta banea cuentas WA | Baja | Proxy residencial + sesiones estables |
| Baja adopción de apoderados | Media | Onboarding ultra simple (5 min) + valor inmediato desde día 1 |
| Colegio no renueva | Baja | Contrato anual + demostrar ROI con métricas de lectura |
| Privacidad/datos personales | Media | Solo lectura de grupos que el apoderado elige. Sin acceso a privados. Cumplimiento RGPD/ley chilena. |

### Por qué Colegium no nos va a copiar (o al menos no rápido ni bien)

1. **Su modelo es "pull", no "push".** Colegium/SchoolNet es una plataforma donde el apoderado tiene que *abrir la app* para ver algo. Cambiar a un modelo push por WhatsApp requiere repensar todo su producto. Es como pedirle a un banco que mande los extractos por WhatsApp en vez de su app — van a resistirlo porque canibaliza el engagement de su propia plataforma.

2. **Conflicto de intereses.** Ellos le venden al colegio la *plataforma completa*. Si agregan resúmenes por WA que reemplazan la necesidad de abrir SchoolNet, están matando su propio producto. ¿Por qué el colegio pagaría la licencia completa si todo llega resumido por WA?

3. **No pueden leer grupos de WA.** Nuestra ventaja de leer los grupos de apoderados y extraer inteligencia es algo que ellos no pueden hacer sin Baileys/WhatsApp Web — y Meta no les va a dar acceso oficial para eso. Es un hack técnico que una empresa grande no se atreve a hacer por compliance.

4. **No agregan fuentes externas.** SchoolNet solo muestra *sus propios datos*. Nosotros resumimos WA + email + web del colegio + SchoolNet mismo. Ellos nunca van a integrar los emails de Gmail del colegio ni los mensajes de los grupos de apoderados — no es su negocio.

5. **Velocidad vs burocracia.** Colegium es una empresa establecida con ciclos de desarrollo largos. Nosotros podemos iterar semanalmente. Para cuando ellos lancen algo parecido (si lo hacen), ya tenemos 10+ colegios con contratos anuales y data acumulada.

6. **El moat real es comercial, no técnico.** "El que llega primero a un colegio y funciona bien, se queda." El costo de re-vincular 500 WhatsApps es altísimo. Los contratos anuales + la relación con el director son la barrera real.

**En resumen:** no es que no *puedan* copiarlo, es que no les *conviene*. Y si lo intentan, será una versión limitada (solo sus datos, solo su app, sin WA bidireccional) que no compite con la experiencia completa.


## Análisis de Competencia

### Competidores directos (comunicación escolar Chile)

| Competidor | Qué hace | Precio | Limitación vs nosotros |
|---|---|---|---|
| **Colegium/SchoolNet** | Plataforma completa: notas, asistencia, pagos, comunicaciones | $500K-1.5M/mes | Pull (apoderado tiene que abrir la app). No tiene AI ni WA. No resume. |
| **Napsis/SND** | Gestión escolar (2000+ colegios en Chile). 200 funcionalidades. | Similar a Colegium | Misma limitación: pull, no push. Sin WhatsApp. |
| **Alexia (Educaria)** | Plataforma escolar para subvencionados | $200-500K/mes | No tiene comunicación directa a apoderados por WA |
| **Radar Escolar** (adquirido por Colegium 2022) | Sincronizaba datos entre plataformas | Integrado en Colegium | Ya no existe como producto independiente |
| **Lirmi** | Plataforma escolar: notas, asistencia, comunicaciones | $300K-800K/mes | Pull (app propia). Sin WA, sin AI, sin resúmenes. |
| **LaFase** | Gestión escolar chilena | Similar | Pull. Sin comunicación directa WA. |
| **Pronote** (Index Éducation) | Plataforma de gestión escolar (liceos franceses) | Incluido en matrícula | Pull (webapp/app). Sin WA, sin AI. Usada en Alliance Française, Lycée Antoine de Saint-Exupéry, etc. |

### Competidores internacionales (comunicación escolar)

| Competidor | Qué hace | Mercado | Diferencia vs nosotros |
|---|---|---|---|
| **ParentSquare** | Comunicación escolar: alertas, mensajes, formularios, pagos | USA (premio EdTech 2025) | No usa WA, no tiene AI para resumir. Solo en inglés. |
| **TalkingPoints** | Comunicación familia-escuela con traducción AI | USA (9M+ usuarios) | Foco en traducción multiidioma. No resume fuentes múltiples. |
| **ClassDojo** | Red social colegio-familia (comportamiento, fotos, mensajes) | Global (gratis) | No tiene AI, no resume, no integra WA. Es una app más que el papá tiene que abrir. |
| **Remind** | Mensajería para colegios (SMS/app) | USA | Solo envía, no lee ni resume. Sin inteligencia. |
| **Bloomz** | Comunicación + voluntariado + pagos | USA | App propia (no WA). Pull, no push. |

### Competidores AI + Educación

| Competidor | Qué hace | Diferencia vs nosotros |
|---|---|---|
| **MagicSchool AI** | Genera newsletters y comunicaciones para profesores | Ayuda al PROFESOR a escribir, no resume para el APODERADO |
| **Brisk Teaching** | AI para crear contenido educativo | Para profesores, no para familias |
| **TeacherMatic** | Templates de comunicación con AI | Generación de contenido, no consumo/resumen |

### Nuestra diferenciación

**Nadie en el mercado hace exactamente esto:**

| Característica | Nosotros | Competencia |
|---|---|---|
| Canal: WhatsApp (95% lectura) | ✅ | ❌ (todos usan app propia o email) |
| Resume MÚLTIPLES fuentes (WA + email + plataforma + web) | ✅ | ❌ (cada uno solo muestra su propia data) |
| AI genera resumen personalizado por familia | ✅ | ❌ |
| Push 2x/día sin esfuerzo del apoderado | ✅ | ❌ (todos son pull: "abre la app") |
| Lee grupos WA del colegio | ✅ | ❌ (ninguno puede hacer esto) |
| Inteligencia de grupos (sentimiento, alertas) | ✅ | ❌ |
| Read receipts por apoderado | ✅ | Parcial (email open rate solamente) |

### Moat (barrera de entrada)

| Barrera | Fortaleza | Duración |
|---|---|---|
| Integración con WhatsApp (Baileys) | Media | Replicable en 2-3 meses por equipo técnico |
| Prompt engineering + calendar extraction | Baja | Cualquiera con Claude/GPT puede hacerlo |
| Red de colegios + contratos anuales | **Alta** | Lock-in real: cuesta cambiar una vez implementado |
| Data acumulada de grupos WA | **Alta** | Años de histórico = ventaja irreplicable |
| Relación con directores | **Alta** | Confianza se construye con tiempo |

**Conclusión:** la barrera técnica es baja pero la barrera comercial es alta. El que llega primero a un colegio y funciona bien, se queda. El costo de cambio para el colegio es alto (re-vincular 500 WhatsApps).


## Roadmap técnico (próximas sesiones)

| # | Qué | Impacto | Esfuerzo |
|---|---|---|---|
| 1 | **Migrar a Gemini Flash** | -80% costo LLM, bot más rápido | Bajo (cambiar modelo en wa_listener + summarizer) |
| 2 | **Base vectorial (pgvector o ChromaDB)** | Bot no manda 663K tokens por pregunta, respuestas más precisas | Medio (chunking + indexación + query layer) |
| 3 | **Arquitectura nueva (Fleet + SQS + Aurora)** | Escala a 100K usuarios, alta disponibilidad | Alto (refactoring completo de infra) |

### 1. Gemini Flash
- Reemplazar Claude Haiku por Gemini 2.0 Flash en `wa_listener.js` (bot) y `summarizer.py` (resúmenes)
- Configurar API key de Google AI / Vertex
- Ajustar prompts si es necesario (Gemini tiene estilo ligeramente distinto)
- Testear calidad de respuestas vs Haiku

### 2. Base vectorial
- Separar bot_context (663K) en chunks por tópico (~110 chunks por usuario)
- Indexar en pgvector (Aurora Serverless) o ChromaDB (local para empezar)
- Contexto fijo mínimo (5K tokens: horario hoy, calendario, extraprogramáticas)
- RAG: buscar chunks relevantes a la pregunta antes de llamar al LLM
- Resultado: de 663K tokens/pregunta a ~10K tokens/pregunta

### 3. Arquitectura nueva
- EC2 Fleet con auto-scaling (120 usuarios/instancia)
- SQS FIFO para scraping (serializado por colegio, jitter variable)
- Aurora Serverless (pgvector + metadata + user state)
- IPRoyal integrado (10 sesiones/IP)
- Spot interruption handling + redistribución automática
- 3 colas (fast + priority + daily)
- AMI pre-baked (30-40s boot)


## Features futuros (backlog)

### Bot conversacional (responde preguntas del apoderado)
- El apoderado pregunta en el grupo Monitor: "¿a qué hora sale Franco mañana?"
- El bot responde automáticamente con la info que ya tiene del calendario/horarios
- **Costo adicional:** +$0.08/user/mes (Gemini Flash) — negligible
- **Valor:** convierte al bot de "resumen pasivo" a asistente activo. Más sticky. Reduce llamadas a secretaría.
- **Riesgo:** si responde mal, genera desconfianza. Requiere disclaimer + fallback "no estoy seguro, confirma con el colegio."

### Alertas proactivas de conflictos en grupos WA
- Si se detectan 10+ mensajes negativos en 1 hora sobre un tema → alerta inmediata al director
- Análisis de sentimiento en tiempo real con AI
- **Valor para el colegio:** se entera antes de que llegue el reclamo formal

### Análisis de preguntas frecuentes del bot conversacional
- Guardar todas las preguntas que los apoderados hacen al bot (con categoría y frecuencia)
- Reportar al colegio: "las 10 preguntas más comunes esta semana"
- Detectar patrones: si muchos preguntan lo mismo → la comunicación del colegio fue insuficiente
- Ejemplos: "¿a qué hora sale mañana?" (40%), "¿hay clases el viernes?" (25%), "¿cuándo es la reunión?" (15%)
- **Valor para el colegio:** evidencia objetiva de qué info falta o no llega clara
- **Implementación:** log de preguntas en `data/bot_questions_{user_id}.json` con timestamp, pregunta, categoría (horario/evaluación/evento/pago/compañero/otro), si el bot pudo responder o no

### Personalización de horarios/frecuencia por apoderado
- Solo AM / Solo PM / Ambos
- Hora preferida del resumen
- Solo alertas urgentes (sin resumen diario)
- Solo días de semana

### Pendientes legales
- Disclaimer de AI: "resúmenes pueden contener errores, confirmar info crítica con el colegio"
- Términos de servicio (contrato con colegio)
- Política de privacidad (qué datos leemos, cómo los usamos)
- Checkbox de aceptación en landing de registro

### Suscripción a tópicos (personalización del resumen)
- El apoderado puede elegir qué tópicos recibir en su resumen diario
- Tópicos base (siempre incluidos): evaluaciones, asistencia, comunicaciones del colegio
- Tópicos opcionales (el apoderado elige): pagos/cobranza, menú casino, extraprogramáticas, noticias web, conducta detallada
- **Tópicos custom (máximo 2-3 por usuario):** el apoderado puede crear tópicos propios que el bot monitorea
  - Ejemplo: "Avísame si mencionan furgón en el grupo de WA"
  - Ejemplo: "Quiero saber cuándo hay actividades de robótica"
  - Ejemplo: "Monitorear si hay cambios de horario para los viernes"
- Implementación: filtro por tópico al generar el resumen + keywords custom que se buscan en mensajes WA/emails
- Valor: cada familia recibe exactamente lo que le importa, sin ruido. Aumenta engagement y reduce la posibilidad de que desactiven el servicio por "mucha info"
