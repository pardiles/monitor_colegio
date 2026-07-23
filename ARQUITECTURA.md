# Arquitectura - Monitor Colegio

## Stack actual (julio 2026)

| Aspecto | Tecnología |
|---|---|
| Infra | EC2 t3.small (us-east-2) + Lambda + S3 + EventBridge |
| Lenguaje | Python (ingesta, resumen) + Node.js (wa_handler) |
| IA resúmenes | Claude Haiku 4.5 (Anthropic API) |
| IA bot | Haiku (fallback Gemini Flash cuando tenga billing) |
| WhatsApp | WAHA (Docker, engine NOWEB) + wa_handler.js |
| Scraping | Playwright (SchoolNet), requests (APIs), Scrapling (web) |
| Storage | Archivos JSON en EC2 + S3 (configs, tokens) |
| Landing | S3 static site + API Gateway + Lambda |

## Flujo principal

```
EventBridge (6:50 AM / 19:50 PM Chile)
    → Arranca EC2
    → run.sh ejecuta:
        1. Sync configs desde S3
        2. python3 main.py {morning|evening}
            → Para cada usuario:
                a) ingest_for_user() — scraping de fuentes
                b) generate_and_send() — LLM genera resumen → outbox
        3. EC2 se auto-apaga
    
wa_handler.js (servicio 24/7 en misma EC2):
    → Recibe webhooks de WAHA (mensajes entrantes)
    → Guarda mensajes en whatsapp_messages.json
    → Responde preguntas con "?" usando LLM + bot_context
    → Procesa outbox cada 3s → envía via WAHA API
```

## Estructura de archivos EC2 (/opt/monitor-colegio/)

```
/opt/monitor-colegio/
├── main.py                    ← orquestador principal
├── wa_handler.js              ← webhook receiver + outbox + bot
├── send_whatsapp.js           ← escribe outbox (llamado por main.py)
├── run.sh                     ← entry point para cron
├── scrape_for_user.py         ← scraping on-demand (landing)
├── .env                       ← API keys
├── config/
│   ├── users/                 ← {user_id}.json (sync desde S3)
│   ├── users.json             ← legacy (merge con individuales)
│   └── tokens/                ← Gmail tokens (sync desde S3)
├── data/
│   ├── shared/                ← CACHE COMPARTIDO POR COLEGIO (nuevo)
│   │   └── {colegio_id}/
│   │       ├── evaluaciones.json
│   │       ├── casino.json
│   │       ├── casino_hoy.json
│   │       ├── scinfo.json
│   │       ├── companeros_{curso}.json
│   │       └── _meta.json     ← timestamps última actualización
│   ├── outbox/                ← mensajes pendientes de envío
│   ├── whatsapp_messages.json ← mensajes de grupos WA
│   ├── monitor_inputs_{user}.json ← instrucciones de padres
│   ├── bot_context_{user}.json    ← snapshot para el bot (646K)
│   ├── calendario_{user}.json     ← eventos persistentes
│   └── mensaje_enviar_{user}.json ← último resumen generado
├── src/
│   ├── sources/               ← scrapers por plataforma
│   ├── processor/             ← summarizer.py
│   ├── shared_cache.py        ← cache compartido por colegio
│   └── calendar_store.py      ← calendario persistente
└── waha_data/                 ← sesiones WAHA (Docker volume)
```

## Cache compartido por colegio

Fuentes que son IGUALES para todos los usuarios del mismo colegio:

| Fuente | Frecuencia real | Cache (horas) | Razón |
|---|---|---|---|
| Calendario evaluaciones | 1x/día | 12h | API pública, no cambia intra-día |
| Casino/menú | 1x/día AM | 12h | PDF mensual, se publica la noche anterior |
| SC Info | 1x/semana | 168h (7 días) | Se publica los lunes |
| Noticias web | 1x/día | 12h | Cambios infrecuentes |
| Compañeros | 1x/mes | 720h (30 días) | Solo cambia con altas/bajas |

Fuentes PER-USER (NO se cachean entre usuarios):

| Fuente | Razón |
|---|---|
| SchoolNet notas/asistencia | Cada apoderado ve solo sus hijos |
| SchoolNet pagos | Cada familia tiene deuda distinta |
| Gmail | Emails son privados |
| WhatsApp grupos | Distintos grupos por familia |
| Extraprogramáticas | Cada hijo tiene inscritas distintas |

Beneficio: Si Pablo, Kevin y Ramón son del mismo colegio, el calendario y casino se scrappean 1 vez (no 3). Reduce requests a SchoolNet y evita rate limits.

## WhatsApp (WAHA)

```
Docker WAHA (localhost:3000)
  ├── Engine: NOWEB (no requiere Chrome)
  ├── Sesión: "pablo" (1 por usuario)
  ├── Webhook → http://localhost:8080/webhook
  └── API: POST /api/sendText, GET /api/sessions/...

wa_handler.js (localhost:8080)
  ├── POST /webhook        ← recibe mensajes entrantes
  ├── POST /api/session/start  ← crear sesión WAHA
  ├── GET  /api/session/qr     ← obtener QR
  ├── GET  /api/session/status ← estado sesión
  ├── POST /api/session/stop   ← detener sesión
  ├── GET  /api/groups         ← listar grupos
  └── GET  /health             ← health check
```

## Resumen AI (Summarizer)

- **AM**: Solo HOY (ramos, pruebas, extraprogramáticas, casino, pendientes)
- **PM**: Novedades del día + preparación para MAÑANA
- **Domingo PM**: Resumen semanal completo (lunes a viernes)
- **Bot**: Responde preguntas con contexto completo (646K → truncado a 6K para LLM)

Deduplicación: si un evento aparece en WA + calendario, se fusiona en 1 línea.

---

## Roadmap: Storage por usuario (próximo refactoring)

Migrar de estructura plana a:
```
data/
├── {user_id}/
│   ├── bot_context.json       ← se sobreescribe cada corrida
│   ├── calendario.json        ← eventos persistentes
│   ├── whatsapp/
│   │   ├── messages.json      ← últimos 7 días
│   │   └── history/           ← archivo semanal
│   ├── emails/latest.json     ← últimos 10 procesados
│   ├── instrucciones.json     ← inputs padres
│   └── meta.json              ← {last_update: {source: timestamp}}
├── shared/{colegio_id}/       ← YA IMPLEMENTADO
└── outbox/
```

Beneficios:
- Privacidad: borrar carpeta = borrar todo un usuario
- Historial: comparar semana a semana
- Menor bot_context: solo cargar lo necesario por pregunta

---

## Roadmap: RAG (base vectorial)

**Problema actual**: El `bot_context` es un JSON de 646K chars. Para responder una pregunta, se trunca a 6K chars. Esto significa que muchas veces el bot NO tiene la respuesta porque se truncó.

**Solución: RAG con pgvector o ChromaDB**

```
Ingesta → Chunking → Embeddings → pgvector/ChromaDB
                                        ↓
Pregunta del usuario → Embedding → Similarity search → Top 5 chunks
                                        ↓
                              LLM genera respuesta con chunks relevantes
```

**Implementación propuesta (orden de esfuerzo):**

1. **ChromaDB local (más fácil, piloto)**
   - Instalar ChromaDB en la EC2 (pip install chromadb)
   - En cada corrida de main.py: generar chunks del bot_context y actualizar la colección
   - En wa_handler.js: cuando llega pregunta, llamar a un endpoint Python que hace similarity search
   - Resultado: bot responde con chunks relevantes en vez de contexto truncado

2. **pgvector en Aurora Serverless (producción, escalable)**
   - Aurora PostgreSQL con extensión pgvector
   - Chunks almacenados con embedding (OpenAI ada-002 o Gemini embeddings)
   - Cada usuario tiene sus chunks indexados por user_id + source + date
   - Query: `SELECT content FROM chunks WHERE user_id = $1 ORDER BY embedding <-> $2 LIMIT 5`
   - Costo: ~$25/mes (Aurora Serverless mínimo)

**Chunks sugeridos:**
| Fuente | Granularidad del chunk |
|---|---|
| Calendario | 1 evento = 1 chunk |
| Comunicaciones | 1 comunicado = 1 chunk |
| Emails | 1 email = 1 chunk |
| Notas | 1 asignatura/semestre = 1 chunk |
| WA mensajes | 1 mensaje o grupo de 5 msgs = 1 chunk |
| Casino | 1 día = 1 chunk |
| Extraprogramáticas | 1 actividad = 1 chunk |

**Métricas objetivo:**
- Bot responde correctamente >90% de preguntas (hoy: ~60% por truncamiento)
- Latencia: <3s desde pregunta hasta respuesta
- Costo por pregunta: <$0.001 (embedding query + LLM con 5 chunks)

**Cuándo implementar:**
- Con <10 usuarios: bot_context truncado funciona OK (pocas preguntas/día)
- Con >50 usuarios: RAG se vuelve necesario (contexto crece, más preguntas)
- Trigger: si usuarios reportan "el bot no sabe" más de 2x/semana → implementar RAG
