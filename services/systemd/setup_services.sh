#!/bin/bash
# Instalar todos los microservicios como systemd services.
# Ejecutar una vez en la EC2: sudo bash services/systemd/setup_services.sh

BASE_DIR="/opt/monitor-colegio"
ENV_FILE="$BASE_DIR/.env"

# Variables de entorno comunes
ENV_VARS="Environment=HOME=/home/ubuntu
Environment=PROJECT_DIR=$BASE_DIR
Environment=DATA_DIR=$BASE_DIR/data
Environment=CONFIG_DIR=$BASE_DIR/config
Environment=PYTHONPATH=$BASE_DIR
Environment=STORAGE_URL=http://localhost:8084
Environment=SCRAPER_URL=http://localhost:8081
Environment=SUMMARIZER_URL=http://localhost:8082
Environment=ORCHESTRATOR_URL=http://localhost:8083
Environment=WA_HANDLER_URL=http://localhost:8080
Environment=RAG_URL=http://localhost:8086
EnvironmentFile=$ENV_FILE"

# --- Storage (foundation) ---
cat > /etc/systemd/system/mc-storage.service << EOF
[Unit]
Description=Monitor Colegio - Storage Service
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/storage/app.py
$ENV_VARS
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- Scraper ---
cat > /etc/systemd/system/mc-scraper.service << EOF
[Unit]
Description=Monitor Colegio - Scraper Service
After=mc-storage.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/scraper/app.py
$ENV_VARS
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- Summarizer ---
cat > /etc/systemd/system/mc-summarizer.service << EOF
[Unit]
Description=Monitor Colegio - Summarizer Service
After=mc-storage.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/summarizer/app.py
$ENV_VARS
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- Orchestrator ---
cat > /etc/systemd/system/mc-orchestrator.service << EOF
[Unit]
Description=Monitor Colegio - Orchestrator Service
After=mc-storage.service mc-scraper.service mc-summarizer.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/orchestrator/app.py
$ENV_VARS
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- Onboarding ---
cat > /etc/systemd/system/mc-onboarding.service << EOF
[Unit]
Description=Monitor Colegio - Onboarding Service
After=mc-storage.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/onboarding/app.py
$ENV_VARS
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- RAG ---
cat > /etc/systemd/system/mc-rag.service << EOF
[Unit]
Description=Monitor Colegio - RAG Service (ChromaDB)
After=mc-storage.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/rag/app.py
$ENV_VARS
Environment=CHROMA_DIR=$BASE_DIR/data/chromadb
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# --- Admin ---
cat > /etc/systemd/system/mc-admin.service << EOF
[Unit]
Description=Monitor Colegio - Admin Service
After=mc-storage.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/services/admin/app.py
$ENV_VARS
Environment=LOG_FILE=/var/log/monitor-colegio.log
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable all
systemctl daemon-reload
systemctl enable mc-storage mc-scraper mc-summarizer mc-orchestrator mc-onboarding mc-rag mc-admin

echo "✅ Services installed. To start all:"
echo "   sudo systemctl start mc-storage mc-rag mc-scraper mc-summarizer mc-orchestrator mc-onboarding mc-admin"
echo ""
echo "To check status:"
echo "   systemctl status mc-storage mc-scraper mc-summarizer mc-orchestrator mc-onboarding mc-rag mc-admin --no-pager"
