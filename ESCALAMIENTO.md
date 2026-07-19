# Plan de Escalamiento - Monitor Colegio

## Arquitectura target: Fleet + Proxy (1 IP/10 users)

### Decisión
- **100 users/instancia** (EC2 t3.medium, Baileys ~15MB/sesión en idle)
- **1 IP residencial estática por cada 10 users** (proxy SOCKS5)
- **Gemini Flash** para AI (migrar desde Haiku cuando haya 100+ users)
- **Costo target: $0.33/user/mes** (sin negociar bulk)
- **Costo con bulk (1000+ users): $0.21/user/mes**

### Cómo funciona el proxy
- Cada instancia EC2 tiene 10 proxies residenciales asignados (100 users / 10 = 10 IPs)
- Cada grupo de 10 usuarios comparte 1 IP residencial
- Baileys usa `SocksProxyAgent` para rutear tráfico WA por el proxy
- El scraping (SchoolNet, Gmail) sigue saliendo por la IP de AWS (no necesita proxy)

```javascript
// wa_listener.js - asignar proxy por grupo de users
const { SocksProxyAgent } = require('socks-proxy-agent');

const proxyUrl = userCfg.proxy; // asignado al onboarding
const agent = proxyUrl ? new SocksProxyAgent(proxyUrl) : undefined;

const sock = makeWASocket({
    auth: state,
    agent: agent,
});
```

## Escalamiento: EC2 Spot Fleet (10 users/instancia)

### Concepto
- Cada EC2 es autónoma: listener + scraping + resumen + envío
- Máximo 10 sesiones WA por instancia (1 IP pública por instancia)
- Spot Fleet maneja interrupciones y rebalanceo automático
- No se necesita DynamoDB — cada instancia tiene sus JSONs locales

### Flujo de alta de usuario nuevo
1. Landing → API Gateway → Lambda guarda config en S3 (`config/users/{user_id}.json`)
2. Lambda asigna usuario a una instancia (la que tenga <10 users)
3. La instancia baja la config de S3 y agrega al wa_listener
4. Vinculación WA (QR) se hace via SSM a la instancia asignada

### Asignación de instancias
- Tabla simple en S3: `fleet/assignments.json`
  ```json
  {
    "i-abc123": ["pablo_ardiles", "oscar_ardiles", "kevin_moir"],
    "i-def456": ["ramon_lillo", "jose_walker", ...]
  }
  ```
- Lambda de onboarding busca instancia con <10 users y asigna
- Si todas están llenas → Spot Fleet request +1 instancia

### AMI base
- Crear AMI desde la instancia actual (incluye node_modules, Python deps, Playwright, xvfb)
- Launch template del fleet usa esa AMI
- User-data script al boot:
  1. Descargar assignments desde S3
  2. Descargar configs de sus usuarios asignados
  3. Iniciar wa_listener (systemd)
  4. Iniciar cron para main.py

### Manejo de interrupciones Spot
- Spot Fleet reemplaza automáticamente instancias terminadas
- Al boot, la nueva instancia descarga sus usuarios de S3
- Las sesiones WA se reconectan automáticamente (auth guardado en S3)
- Tiempo de recuperación: ~30 segundos

## Costos proyectados

### Sin proxy (riesgo medio de ban a escala)

| Usuarios | Instancias | EC2 Spot | EBS | Claude Haiku | Total/mes | Por usuario |
|---|---|---|---|---|---|---|
| 10 | 1 | $5.62 | $1.28 | $1.00 | $7.90 | $0.79 |
| 50 | 5 | $28 | $6.40 | $5.00 | $39 | $0.78 |
| 100 | 10 | $56 | $12.80 | $10.00 | $79 | $0.79 |
| 1,000 | 100 | $562 | $128 | $100 | $790 | $0.79 |

### Con 1 IP residencial por usuario (optimizado)

Arquitectura optimizada: 100 users/instancia + proxy individual + Gemini Flash

| Componente | Decisión | Costo/user/mes |
|---|---|---|
| EC2 Spot | t3.medium, 100 users/instancia | $0.11 |
| EBS | 16GB compartido entre 100 users | $0.01 |
| Proxy residencial | 1 IP estática/user, bulk ~$0.60 | $0.60 |
| AI (Gemini Flash) | 2 calls/día × 30 | $0.02 |
| S3 + API Gateway | negligible | $0.01 |
| **TOTAL** | | **$0.75/user/mes** |

| Usuarios | Instancias (100/inst) | EC2+EBS | Proxies ($0.60) | AI (Flash) | Total/mes | Por usuario |
|---|---|---|---|---|---|---|
| 100 | 1 | $12.50 | $60 | $2 | **$75** | **$0.75** |
| 1,000 | 10 | $125 | $600 | $20 | **$745** | **$0.75** |
| 10,000 | 100 | $1,250 | $6,000 | $200 | **$7,450** | **$0.75** |

### Con 1 IP residencial cada 10 usuarios

Escenario más realista: 10 sesiones WA comparten 1 IP residencial (parece una familia/oficina). Riesgo bajo de ban.

**Sin negociar bulk ($1.75/IP):**

| Componente | Decisión | Costo/user/mes |
|---|---|---|
| EC2 Spot | t3.medium, 100 users/instancia | $0.11 |
| EBS | 16GB compartido entre 100 users | $0.01 |
| Proxy residencial | 1 IP cada 10 users, $1.75/IP | $0.175 |
| AI (Gemini Flash) | 2 calls/día × 30 | $0.02 |
| S3 + API Gateway | negligible | $0.01 |
| **TOTAL** | | **$0.33/user/mes** |

| Usuarios | Total/mes |
|---|---|
| 100 | $33 |
| 1,000 | $330 |
| 10,000 | $3,300 |

**Con bulk negociado ($0.60/IP, a partir de 1000+ users):**

| Componente | Decisión | Costo/user/mes |
|---|---|---|
| EC2 Spot | t3.medium, 100 users/instancia | $0.11 |
| EBS | 16GB compartido entre 100 users | $0.01 |
| Proxy residencial | 1 IP cada 10 users, bulk $0.60/IP | $0.06 |
| AI (Gemini Flash) | 2 calls/día × 30 | $0.02 |
| S3 + API Gateway | negligible | $0.01 |
| **TOTAL** | | **$0.21/user/mes** |

| Usuarios | Total/mes |
|---|---|
| 1,000 | $210 |
| 10,000 | $2,100 |

## Riesgo de ban de Meta (WhatsApp)

### Con proxy individual: Riesgo BAJO a cualquier escala
- Cada usuario sale por una IP residencial distinta
- Meta ve 1 sesión por IP residencial = parece un celular normal
- No hay correlación entre usuarios

### Implementación del proxy
```javascript
// wa_listener.js - cada sesión usa su propio proxy SOCKS5
const { SocksProxyAgent } = require('socks-proxy-agent');

const proxyUrl = userCfg.proxy; // "socks5://user:pass@gate.provider.com:22225"
const agent = proxyUrl ? new SocksProxyAgent(proxyUrl) : undefined;

const sock = makeWASocket({
    auth: state,
    agent: agent,  // tráfico WA sale por proxy residencial
});
```

Config por usuario:
```json
{
  "id": "pablo_ardiles",
  "proxy": "socks5://usr_pablo:xyz@gate.brightdata.com:22225"
}
```

### Proveedores recomendados (IP estática residencial)
| Proveedor | Precio/IP (1 unidad) | Precio/IP (1000+) | Latam disponible |
|---|---|---|---|
| Bright Data | $2.00/mes | ~$0.80/mes | Sí (Chile) |
| IPRoyal | $1.75/mes | ~$0.70/mes | Sí |
| ProxyLine | $1.20/mes | ~$0.60/mes | Sí |
| 922proxy | $0.90/mes | ~$0.50/mes | Limitado |

### Sin proxy (plan actual, hasta ~50 users)
- 10 sesiones desde 1 IP de datacenter AWS = riesgo medio
- Mitigación: conexiones estables, sin spam, user-agent consistente
- Si hay ban → agregar proxy es 1 línea de config, no requiere rediseño

### A gran escala (500+ users): proxy + jitter obligatorio

**Riesgos de detección por Meta a escala:**
- 1000 cuentas que reconectan al mismo segundo después de un restart
- Todas con el mismo user-agent ("Chrome Mac OS 14.4.1")
- Todas envían mensajes exactamente a las 7:00AM y 20:00PM
- Cero interacción humana (no abren media, no leen, no escriben)

**Mitigaciones obligatorias a partir de 500 users:**

| Mitigación | Implementación | Impacto |
|---|---|---|
| Jitter en envío | Randomizar ±10 min la hora de envío por usuario | Evita patrón detectable de "todos a las 7:00" |
| Jitter en reconexión | Al reconectar, esperar random 5-60s entre cada sesión | No reconectar 100 cuentas al mismo segundo |
| Variar user-agent | Rotar entre 3-5 versiones de Chrome/Safari | No todos idénticos |
| Proxy residencial | 1 IP cada 10 users (ya documentado) | Cada grupo parece una casa distinta |
| Simular actividad mínima | Marcar mensajes como "leídos" ocasionalmente | Parecer más humano |

**Código de jitter (agregar a main.py y wa_listener.js):**
```python
# main.py - jitter antes de enviar
import random
jitter = random.randint(0, 600)  # 0-10 minutos
time.sleep(jitter)
```

```javascript
// wa_listener.js - jitter al reconectar
const jitter = Math.floor(Math.random() * 30000); // 0-30 segundos
setTimeout(() => startSession(userCfg), jitter);
```

**Peor escenario si Meta detecta:**
- Desvincula sesiones (usuario tiene que re-escanear QR)
- NO demandan (no somos spammers)
- NO banean el número del usuario (solo desvinculan el dispositivo web)
- Solución: re-vincular + cambiar proxy

**Nota:** empresas como Respond.io, Wati operan a mayor escala con enfoque similar sin problemas. Meta persigue spammers masivos (miles de mensajes/hora), no servicios legítimos de bajo volumen (2 msgs/día/user).

## Pasos de implementación

### Fase 1: Preparar AMI (cuando lleguemos a 10 users)
- [ ] Crear AMI desde instancia actual
- [ ] Crear launch template con user-data script
- [ ] Script de boot: sync S3 → start services

### Fase 2: Fleet básico + Proxy
- [ ] Crear Spot Fleet request (capacity=2)
- [ ] Implementar `fleet/assignments.json` en S3
- [ ] Contratar IPs residenciales estáticas (1 por cada 10 users)
- [ ] Configurar SOCKS5 proxy en Baileys (SocksProxyAgent)
- [ ] Asignar proxy al crear usuario (Lambda onboarding)
- [ ] Modificar SSM commands para target instancia correcta
- [ ] Dependencia: `npm install socks-proxy-agent`

### Fase 3: Auto-scaling
- [ ] CloudWatch alarm: si todas las instancias tienen ≥80 users → scale up
- [ ] Lambda que modifica target capacity del fleet
- [ ] Al scale up: comprar nueva IP de proxy para la nueva instancia
- [ ] Manejo de scale-down (mover users si instancia queda vacía)

### Fase 4: Optimización AI (cuando haya 100+ users)
- [ ] Implementar client Gemini Flash (ya está el código, falta API key)
- [ ] Validar calidad de resúmenes vs Haiku
- [ ] Switchear (feature flag por usuario para A/B test)
- [ ] Si se queda con Haiku, implementar optimizaciones:

#### Optimización de costos Claude Haiku (sin cambiar de modelo)

| Optimización | Ahorro | Implementación |
|---|---|---|
| Reducir tokens input (pre-filtrar datos, solo próximos 3 días) | ~40% | Modificar `_format_data()` para enviar menos contexto |
| Prompt caching (system prompt reutilizable) | ~25% | Activar cache en API Anthropic (tokens cacheados cuestan 90% menos) |
| Batch API (envío masivo, respuesta en minutos) | 50% | Cambiar endpoint a `/v1/messages/batches`. Enviar a las 6:50AM, recibir antes de 7:00AM |
| Skip days sin novedades (ya implementado) | ~25% | Ya funciona: viernes PM, sábado, domingo AM no se envían si no hay eventos |

**Progresión de costo/user/mes con Haiku:**

| Nivel | Costo/user/mes | Qué se hace |
|---|---|---|
| Sin optimizar (actual) | $0.10 | 2 calls/día, ~3K tokens input |
| + Reducir input | $0.06 | Pre-filtrar datos relevantes |
| + Batch API | $0.03 | 50% descuento por batch |
| + Skip days + cache | $0.025 | Máxima optimización |

**Conclusión:** Haiku optimizado ($0.025/user) es comparable a Gemini Flash ($0.02/user). La decisión es de calidad, no de costo.


## Alta disponibilidad (Spot interruption handling)

### Concepto: 100% disponibilidad con EC2 Spot

AWS avisa 2 minutos antes de interrumpir una instancia Spot. En ese tiempo:
1. Script detecta señal de interrupción (polling a metadata endpoint cada 5s)
2. Guarda estado mínimo en S3 (lista de outbox pendientes si hay)
3. Fleet ya lanzó instancia de reemplazo en paralelo (capacity `maintain`)
4. Nueva instancia arranca, baja config de S3, reconecta Baileys (~10 segundos)

**Resultado: 0-10 segundos de downtime. WhatsApp no desvincula. 100% disponibilidad efectiva.**

### Implementación: spot-interruption-handler.sh

```bash
#!/bin/bash
# Corre en cron cada 5 segundos o como daemon
# Detecta señal de interrupción Spot y prepara migración

while true; do
    # Consultar metadata de interrupción
    HTTP_CODE=$(curl -s -o /tmp/spot-action.json -w "%{http_code}" \
        http://169.254.169.254/latest/meta-data/spot/instance-action 2>/dev/null)
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo "⚠️ SPOT INTERRUPTION DETECTED - Preparando migración..."
        
        # 1. Notificar (opcional: SNS)
        # aws sns publish --topic-arn ... --message "Spot interruption on $(hostname)"
        
        # 2. Sync estado a S3 (outbox pendientes, datos parciales)
        aws s3 sync /opt/monitor-colegio/data/outbox/ s3://monitor-colegio-config-669294688330/state/$(hostname)/outbox/ --region us-east-2
        
        # 3. Flush logs
        journalctl -u wa-listener --no-pager > /tmp/last_logs.txt
        aws s3 cp /tmp/last_logs.txt s3://monitor-colegio-config-669294688330/state/$(hostname)/last_logs.txt --region us-east-2
        
        echo "✅ Estado guardado. Fleet reemplazará esta instancia automáticamente."
        exit 0
    fi
    
    sleep 5
done
```

### User-data de nueva instancia (boot script)

```bash
#!/bin/bash
# Al arrancar una nueva instancia del fleet:

# 1. Descargar assignments (qué usuarios van en esta instancia)
aws s3 cp s3://monitor-colegio-config-669294688330/fleet/assignments/$(curl -s http://169.254.169.254/latest/meta-data/instance-id).json /opt/monitor-colegio/config/my_users.json --region us-east-2

# 2. Descargar config de cada usuario asignado
# (el script de boot itera y baja config/users/{user_id}.json)

# 3. Recuperar outbox pendientes (si venimos de una interrupción)
aws s3 sync s3://monitor-colegio-config-669294688330/state/*/outbox/ /opt/monitor-colegio/data/outbox/ --region us-east-2

# 4. Iniciar servicios
systemctl start wa-listener
# Cron ya está configurado en la AMI

# 5. Iniciar handler de interrupciones
nohup /opt/monitor-colegio/spot-interruption-handler.sh &
```

### Estadísticas de interrupciones Spot

| Tipo instancia | Región | Tasa interrupción mensual | Con diversificación (multi-AZ + multi-type) |
|---|---|---|---|
| t3.medium | us-east-2 | ~5% | <2% |
| t3.small | us-east-2 | ~5% | <2% |
| t3a.medium | us-east-2 | ~3% | <1% |

Con fleet configurado con múltiples tipos (t3.medium + t3a.medium + t3.small) y múltiples AZs, la probabilidad de interrupción sin reemplazo inmediato es prácticamente 0.

### Pendientes de implementación
- [ ] Crear `spot-interruption-handler.sh` 
- [ ] Agregar al systemd como servicio
- [ ] User-data script para boot de nuevas instancias
- [ ] Probar failover end-to-end
