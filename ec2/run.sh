#!/bin/bash
cd /opt/monitor-colegio
export PATH="/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME=/home/ubuntu
export DISPLAY=:99

HOUR=$(TZ='America/Santiago' date +%H)
if [ "$HOUR" -lt 12 ]; then
  MODE="morning"
else
  MODE="evening"
fi

STATE_FILE="/opt/monitor-colegio/data/.last_run"
if [ ! -f "$STATE_FILE" ]; then
  WA_MODE="week"
else
  WA_MODE="daily"
fi

echo "$(TZ='America/Santiago' date) - Modo: $MODE | WA: $WA_MODE" >> /var/log/monitor-colegio.log

# Sync usuarios desde S3 (nuevos registros de la landing)
aws s3 sync s3://monitor-colegio-config-669294688330/config/users/ /opt/monitor-colegio/config/users/ >> /var/log/monitor-colegio.log 2>&1

# Sync tokens Gmail desde S3 (generados por la landing OAuth)
aws s3 sync s3://monitor-colegio-config-669294688330/config/tokens/ /opt/monitor-colegio/config/tokens/ >> /var/log/monitor-colegio.log 2>&1

node fetch_whatsapp.js $WA_MODE >> /var/log/monitor-colegio.log 2>&1

# xvfb-run para Cuaderno Rojo (Cloudflare requiere browser headed)
xvfb-run -a python3 main.py $MODE >> /var/log/monitor-colegio.log 2>&1

mkdir -p data
date > "$STATE_FILE"
echo "$(TZ='America/Santiago' date) - Finalizado" >> /var/log/monitor-colegio.log

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
/home/ubuntu/.local/bin/aws ec2 stop-instances --instance-ids $INSTANCE_ID --region us-east-2
