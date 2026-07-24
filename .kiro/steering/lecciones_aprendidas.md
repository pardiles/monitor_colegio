---
inclusion: auto
---

# Lecciones Aprendidas — Monitor Colegio

## WhatsApp / WAHA
- **NO reiniciar WAHA múltiples veces** — WhatsApp puede banear el dispositivo
- WAHA sesión "pablo" usa el número del apoderado (56968983699). Los mensajes que él envía llegan como `fromMe=true`. El bot DEBE procesar `fromMe` en el grupo monitor (es donde el apoderado pregunta/instruye)
- Cuando se cambia la IP de salida de WAHA (ej: activar proxy), WhatsApp desconecta la sesión y requiere re-vincular QR/pairing code
- `NO_PROXY=localhost,127.0.0.1` es OBLIGATORIO en el Docker de WAHA cuando se usa proxy — sin esto los webhooks a localhost:8080 van por el proxy y fallan silenciosamente
- El grupo monitor de Pablo es `120363427626724523@g.us`
- Cada usuario tiene su propia sesión WAHA (no compartida)

## Proxy / Bright Data
- **Proveedor elegido: Bright Data ISP** — IP fija Chile, $2/IP/mes (shared unlimited)
- Host: `brd.superproxy.io:33335`
- User: `brd-customer-hl_439f135d-zone-monitor_colegio_cl`
- No poner allowlist de IPs (para soportar múltiples EC2 a futuro)
- El proxy aplica a: WAHA (WhatsApp) + SchoolNet (Playwright) + Extraprogramáticas
- APIs legítimas (Gmail API, calendario JSON) NO necesitan proxy
- IPRoyal y Webshare NO tienen Chile en Static Residential (solo rotating)

## Cloudflare / Extraprogramáticas
- Cloudflare bloquea POSTs a `extracurriculares.colegium.com/datos` sin importar si la IP es residencial o datacenter
- El GET inicial funciona (carga página con alumnos)
- La app React del sitio SÍ puede hacer el POST internamente (cuando se clickea "Inscritas" desde el browser)
- Pero eso funciona intermitentemente (~50%) — depende de la "calidez" de la cookie cf_clearance
- **Solución definitiva: extraprogramáticas se hardcodean en config del usuario** (cambian 1x/semestre)
- El proxy NO resolvió el problema de Cloudflare para POSTs

## EC2 / Deploy
- AWS CLI en la EC2 está en `/home/ubuntu/.local/bin/aws` — los scripts que corren como root (systemd, SSM) necesitan el path completo
- `proxy_config.py` necesita `load_dotenv()` explícito porque no siempre pasa por main.py
- Archivos creados via SSM (root) tienen permisos distintos a los de ubuntu — el outbox necesita `chmod 666`
- El bucket S3 deploy (`s3://monitor-colegio-config-669294688330/deploy/`) debe limpiarse después de cada deploy para no acumular basura

## Timezone
- La EC2 corre en UTC. Todo lo que muestra fechas/horas al usuario DEBE usar `America/Santiago` explícitamente
- `new Date().getDay()` en Node.js usa UTC. Para obtener el día correcto en Chile: `new Date(new Date().toLocaleString('en-US', {timeZone:'America/Santiago'})).getDay()`
- Python: siempre usar `datetime.now(ZoneInfo("America/Santiago"))`, nunca `datetime.now()`

## Bot / Respuestas
- El bot responde "📝 Anotado" cuando recibe instrucciones >10 chars (sin "?") en el grupo monitor
- El bot responde con 🤖 cuando la pregunta tiene "?"
- Sin RAG: el bot_context (646K) se trunca a 6K chars → pierde compañeros, notas antiguas, etc.
- Con RAG (ChromaDB): 99 chunks indexados, similarity search retorna chunks relevantes por pregunta

## RAG / ChromaDB
- ChromaDB instalado en EC2 (`pip install chromadb`)
- El RAG service (mc-rag, puerto 8086) debe tener chunks INDEXADOS para funcionar
- La indexación ocurre: 1) después de cada run de main.py 2) manualmente via POST /index/{user_id}
- **Los compañeros son ~80 chunks** (1 por compañero con nombre, cumple, tel, padres)
- El resumen diario ahora también usa RAG: queries focalizadas por modo (AM/PM/semanal)

## Microservicios
- 7 servicios corriendo (storage, scraper, summarizer, orchestrator, onboarding, rag, admin)
- El orchestrator importa main.py directamente (mismo PYTHONPATH) — no duplica lógica
- run.sh intenta orchestrator primero, fallback a main.py directo
- Todos los servicios usan HTTP simple (http.server) — sin Flask ni deps extra

## Costos
- Haiku: funciona bien, ~$0.001/resumen
- Gemini Flash free tier: AGOTADO (limit: 0), no usar hasta activar billing
- Bright Data ISP: $2/IP/mes (1 IP por cada 10 usuarios)
- EC2 t3.small: ~$36/mes (corre 24/7 para WAHA)

## Reglas de negocio
- Resumen AM = solo HOY
- Resumen PM = solo MAÑANA
- Resumen domingo PM = semana completa
- Extraprogramáticas cambian 1x/semestre — no re-scrappear diario
- Casino en PM dice "mañana" no "hoy"
- No enviar alertas de capacidad a usuarios (solo log admin)
- Cada usuario es una sesión WA separada
