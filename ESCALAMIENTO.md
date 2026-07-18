# Plan de Escalamiento - Monitor Colegio

## Arquitectura actual (1-10 usuarios)

- 1 EC2 Spot t3.small (us-east-2) corriendo 24/7
- wa_listener.js: conexión WA permanente para todos los users
- main.py: scraping + Claude + envío via outbox (cron 2x/día)
- S3: config de usuarios, landing
- Costo: **$7.92/mes** ($2.64/user con 3 users)

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

| Usuarios | Instancias | EC2 Spot | EBS | Claude Haiku | Total/mes | Por usuario |
|---|---|---|---|---|---|---|
| 10 | 1 | $5.62 | $1.28 | $1.00 | $7.90 | $0.79 |
| 50 | 5 | $28 | $6.40 | $5.00 | $39 | $0.78 |
| 100 | 10 | $56 | $12.80 | $10.00 | $79 | $0.79 |
| 500 | 50 | $281 | $64 | $50 | $395 | $0.79 |
| 1,000 | 100 | $562 | $128 | $100 | $790 | $0.79 |
| 10,000 | 1,000 | $5,620 | $1,280 | $1,000 | $7,900 | $0.79 |

Basado en: t3.small spot $0.0078/hr, EBS gp3 16GB $0.08/GB, Haiku ~$0.005/call × 2/día

## Riesgo de ban de Meta (WhatsApp)

### Nivel actual (3 users, 1 IP AWS): Riesgo BAJO
- 1 conexión estable, sin mensajería masiva

### A escala (10/IP de datacenter): Riesgo MEDIO
- 10 sesiones por IP es aceptable si son estables
- No hacer bulk messaging (2 msgs/día/user es nada)
- No conectar/desconectar frecuentemente

### Mitigación si Meta aprieta: Proxy residencial
- Agregar SOCKS5 proxy a Baileys (1 línea de config)
- Bright Data Static Residential: ~$2/IP/mes
- Esquema: 1 IP residencial por cada 5-10 users
- Costo adicional para 1000 users: ~$200-400/mes
- **Solo implementar si hay evidencia de ban, no antes**

## Pasos de implementación (cuando lleguemos a 10 users)

### Fase 1: Preparar AMI
- [ ] Crear AMI desde instancia actual
- [ ] Crear launch template con user-data script
- [ ] Script de boot: sync S3 → start services

### Fase 2: Fleet básico
- [ ] Crear Spot Fleet request (capacity=2)
- [ ] Implementar `fleet/assignments.json` en S3
- [ ] Modificar Lambda onboarding para asignar instancia
- [ ] Modificar SSM commands para target instancia correcta

### Fase 3: Auto-scaling
- [ ] CloudWatch alarm: si todas las instancias tienen ≥8 users → scale up
- [ ] Lambda que modifica target capacity del fleet
- [ ] Manejo de scale-down (mover users si instancia queda vacía)

### Fase 4: Proxy (solo si hay ban)
- [ ] Evaluar Bright Data / IPRoyal pricing
- [ ] Configurar proxy SOCKS5 en Baileys
- [ ] 1 proxy por instancia (10 users comparten 1 IP residencial)
