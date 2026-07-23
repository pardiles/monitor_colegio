# Microservicios - Monitor Colegio

Cada servicio es independiente, con su propia API REST HTTP.
Comunicación entre servicios es via HTTP localhost (misma EC2) o red Docker.

## Servicios

| Servicio | Puerto | Stack | Descripción |
|---|---|---|---|
| `waha` | 3000 | Docker (externo) | WhatsApp sessions (NOWEB engine) |
| `wa-handler` | 8080 | Node.js | Webhooks WA + bot AI + outbox envío |
| `scraper` | 8081 | Python (Flask) | Scraping fuentes (SchoolNet, Gmail, Web, Casino) |
| `summarizer` | 8082 | Python (Flask) | Generación de resúmenes con LLM |
| `orchestrator` | 8083 | Python (Flask) | Cron, scheduling, coordinación de flujos |
| `storage` | 8084 | Python (Flask) | API de datos: CRUD contexto, calendario, cache |
| `onboarding` | 8085 | Python (Flask) | Registro, vinculación WA, detección hijos |
| `rag` | 8086 | Python (Flask) | Embeddings + similarity search (ChromaDB) |
| `admin` | 8087 | Python (Flask) | Dashboard: usuarios, logs, métricas, acciones |

## Flujos principales

### Resumen diario (AM/PM)
```
orchestrator (cron) 
  → scraper /scrape/{user_id}
  → storage /context/{user_id} (guardar datos)
  → summarizer /generate (leer contexto + generar resumen)
  → wa-handler /outbox (escribir mensaje para envío)
  → waha /api/sendText (envío real)
```

### Pregunta del bot (WhatsApp)
```
waha (webhook) → wa-handler /webhook
  → rag /query (buscar chunks relevantes)
  → summarizer /answer (generar respuesta con contexto)
  → waha /api/sendText (enviar respuesta)
```

### Onboarding usuario nuevo
```
Landing → onboarding /register
  → wa-handler /api/session/start (vincular WA)
  → scraper /scrape/{user_id}?fast=true (detección hijos)
  → storage /users/{user_id} (guardar config)
  → summarizer /generate (primer resumen bienvenida)
  → wa-handler /outbox (enviar bienvenida)
```

### Admin
```
admin /dashboard → storage /users (listar)
admin /rescrape/{user_id} → orchestrator /run/{user_id}
admin /logs → storage /logs
```

## Cómo correr

```bash
# Desarrollo (todos en la misma EC2)
cd /opt/monitor-colegio
python services/orchestrator/app.py &
python services/scraper/app.py &
python services/summarizer/app.py &
python services/storage/app.py &
python services/onboarding/app.py &
python services/rag/app.py &
python services/admin/app.py &
node services/wa-handler/app.js &

# Producción (systemd por servicio)
sudo systemctl start mc-orchestrator mc-scraper mc-summarizer mc-storage mc-onboarding mc-rag mc-admin wa-handler
```

## Variables de entorno compartidas (.env)
```
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
AI_ENGINE=haiku
WAHA_URL=http://localhost:3000
WAHA_API_KEY=monitor2026
STORAGE_URL=http://localhost:8084
DATA_DIR=/opt/monitor-colegio/data
CONFIG_DIR=/opt/monitor-colegio/config
```
