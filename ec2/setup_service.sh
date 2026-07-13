#!/bin/bash
# Configurar el servicio systemd para que ejecute al boot

sudo tee /etc/systemd/system/monitor-colegio.service << 'EOF'
[Unit]
Description=Monitor Colegio - Ingesta y Resumen
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ec2-user
ExecStartPre=/bin/sleep 15
ExecStart=/opt/monitor-colegio/run.sh
WorkingDirectory=/opt/monitor-colegio
Environment=HOME=/home/ec2-user
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable monitor-colegio.service
echo "Servicio configurado OK"
