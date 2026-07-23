#!/bin/bash
# Setup completo de la EC2 para Monitor Colegio (WAHA + wa_handler)
set -e

echo "=== 1. Instalar dependencias del sistema ==="
sudo apt-get update
sudo apt-get install -y python3 python3-pip nodejs npm docker.io xvfb

echo "=== 2. Crear directorio del proyecto ==="
sudo mkdir -p /opt/monitor-colegio
sudo chown ubuntu:ubuntu /opt/monitor-colegio

echo "=== 3. Instalar dependencias Python ==="
cd /opt/monitor-colegio
pip3 install --user anthropic playwright google-auth google-auth-oauthlib google-api-python-client python-dotenv requests python-dateutil google-genai

echo "=== 4. Instalar Playwright browsers ==="
python3 -m playwright install chromium

echo "=== 5. Instalar WAHA (Docker) ==="
sudo docker pull devlikeapro/waha:latest
sudo docker run -d \
  --name waha \
  --network=host \
  -e WHATSAPP_DEFAULT_ENGINE=NOWEB \
  -e WAHA_DASHBOARD_ENABLED=true \
  -e WHATSAPP_API_KEY=monitor2026 \
  -v /opt/monitor-colegio/waha_data:/app/.sessions \
  devlikeapro/waha:latest

echo "=== 6. Configurar servicios systemd ==="

# Servicio oneshot: run.sh (scraping + resumen, ejecuta al boot via cron/EventBridge)
sudo tee /etc/systemd/system/monitor-colegio.service << 'EOF'
[Unit]
Description=Monitor Colegio - Ingesta y Resumen
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
ExecStartPre=/bin/sleep 15
ExecStart=/opt/monitor-colegio/run.sh
WorkingDirectory=/opt/monitor-colegio
Environment=HOME=/home/ubuntu
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF

# Servicio persistente: wa_handler.js (webhook receiver + outbox sender via WAHA)
sudo tee /etc/systemd/system/wa-handler.service << 'EOF'
[Unit]
Description=Monitor Colegio - WA Handler (WAHA webhook + outbox)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/bin/node /opt/monitor-colegio/wa_handler.js
WorkingDirectory=/opt/monitor-colegio
Environment=HOME=/home/ubuntu
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable monitor-colegio.service
sudo systemctl enable wa-handler.service
sudo systemctl start wa-handler.service

echo "=== 7. Configurar webhook en WAHA ==="
# Wait for WAHA to start
sleep 5
curl -X PUT http://localhost:3000/api/default/webhook \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: monitor2026" \
  -d '{"url": "http://localhost:8080/webhook", "events": ["message", "message.any"]}'

echo ""
echo "=== SETUP COMPLETO ==="
echo "  - WAHA: localhost:3000 (Docker, NOWEB engine)"
echo "  - wa_handler: localhost:8080 (webhook receiver + outbox)"
echo "  - monitor-colegio.service: oneshot (scraping + resumen)"
echo "  - wa-handler.service: persistent (webhook + envío)"
