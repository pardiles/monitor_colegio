#!/bin/bash
# Setup completo de la EC2 para Monitor Colegio
set -e

echo "=== 1. Instalar dependencias del sistema ==="
sudo dnf install -y python3.11 python3.11-pip nodejs20 git nss atk cups-libs libdrm libXcomposite libXdamage libXrandr mesa-libgbm pango alsa-lib

echo "=== 2. Crear directorio del proyecto ==="
sudo mkdir -p /opt/monitor-colegio
sudo chown ec2-user:ec2-user /opt/monitor-colegio

echo "=== 3. Instalar dependencias Python ==="
cd /opt/monitor-colegio
pip3.11 install --user anthropic playwright google-auth google-auth-oauthlib google-api-python-client python-dotenv requests python-dateutil scrapling

echo "=== 4. Instalar Playwright browsers ==="
python3.11 -m playwright install chromium

echo "=== 5. Instalar dependencias Node ==="
cd /opt/monitor-colegio
npm init -y 2>/dev/null
npm install whatsapp-web.js

echo "=== 6. Instalar Puppeteer Chrome para whatsapp-web.js ==="
npx puppeteer browsers install chrome

echo "=== 7. Crear script de ejecución ==="
cat > /opt/monitor-colegio/run.sh << 'RUNEOF'
#!/bin/bash
cd /opt/monitor-colegio
export PATH="/home/ec2-user/.local/bin:$PATH"
export PUPPETEER_EXECUTABLE_PATH="/home/ec2-user/.cache/puppeteer/chrome/linux-*/chrome-linux64/chrome"

# Determinar modo AM o PM (Chile/Santiago = UTC-4 en invierno)
HOUR=$(TZ='America/Santiago' date +%H)
if [ "$HOUR" -lt 12 ]; then
  MODE="morning"
else
  MODE="evening"
fi

# Determinar si es primera ejecución
STATE_FILE="/opt/monitor-colegio/data/.last_run"
if [ ! -f "$STATE_FILE" ]; then
  WA_MODE="week"
  echo "Primera ejecución - leyendo última semana"
else
  WA_MODE="daily"
fi

echo "$(TZ='America/Santiago' date) - Modo: $MODE | WhatsApp: $WA_MODE"

# 1. Leer WhatsApp
node fetch_whatsapp.js $WA_MODE 2>&1 | tee -a /var/log/monitor-colegio.log

# 2. Ejecutar ingesta + resumen + envio
python3.11 main.py $MODE 2>&1 | tee -a /var/log/monitor-colegio.log

# 3. Marcar ejecución exitosa
mkdir -p data
date > "$STATE_FILE"

echo "$(TZ='America/Santiago' date) - Finalizado. Apagando..."

# 4. Apagar la instancia
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 stop-instances --instance-ids $INSTANCE_ID --region us-east-2
RUNEOF

chmod +x /opt/monitor-colegio/run.sh

echo "=== 8. Configurar servicio systemd ==="
sudo tee /etc/systemd/system/monitor-colegio.service << 'SVCEOF'
[Unit]
Description=Monitor Colegio
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ec2-user
ExecStartPre=/bin/sleep 10
ExecStart=/opt/monitor-colegio/run.sh
WorkingDirectory=/opt/monitor-colegio
Environment=HOME=/home/ec2-user
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable monitor-colegio.service

echo "=== SETUP COMPLETO ==="
