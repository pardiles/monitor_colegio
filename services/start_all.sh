#!/bin/bash
# Start all microservices for Monitor Colegio
# Usage: ./services/start_all.sh

cd /opt/monitor-colegio
export HOME=/home/ubuntu
export PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH
export PROJECT_DIR=/opt/monitor-colegio
export DATA_DIR=/opt/monitor-colegio/data
export CONFIG_DIR=/opt/monitor-colegio/config
export PYTHONPATH=/opt/monitor-colegio

# Load .env
set -a
source .env 2>/dev/null
set +a

echo "Starting Monitor Colegio services..."

# Storage (foundation — start first)
python3 services/storage/app.py &
sleep 1

# RAG
python3 services/rag/app.py &

# Scraper
python3 services/scraper/app.py &

# Summarizer
python3 services/summarizer/app.py &

# Orchestrator
python3 services/orchestrator/app.py &

# Onboarding
python3 services/onboarding/app.py &

# Admin
python3 services/admin/app.py &

# wa-handler (Node.js — already managed by systemd usually)
# node wa_handler.js &

echo ""
echo "All services started:"
echo "  storage:      http://localhost:8084"
echo "  scraper:      http://localhost:8081"
echo "  summarizer:   http://localhost:8082"
echo "  orchestrator: http://localhost:8083"
echo "  onboarding:   http://localhost:8085"
echo "  rag:          http://localhost:8086"
echo "  admin:        http://localhost:8087"
echo "  wa-handler:   http://localhost:8080 (systemd)"
echo "  waha:         http://localhost:3000 (docker)"
echo ""
echo "Dashboard: http://localhost:8087/dashboard"
echo ""

wait
