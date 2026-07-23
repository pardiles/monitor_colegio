#!/bin/bash
# Configurar servicios systemd para Monitor Colegio

# 1. Servicio oneshot: run.sh (ejecuta scraping + resumen al boot/cron)
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

# 2. Servicio persistente: wa_handler.js (webhook receiver + outbox sender via WAHA)
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

echo "✅ Servicios configurados:"
echo "   - monitor-colegio.service (oneshot, scraping + resumen)"
echo "   - wa-handler.service (persistent, webhook + outbox via WAHA)"
