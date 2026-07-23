#!/bin/bash
# =============================================================================
# Deploy Monitor Colegio - Cambios del 2025-07-19
# Ejecutar desde tu máquina local (requiere AWS CLI configurado)
# =============================================================================
set -e

INSTANCE_ID="i-00d2a56f9b8078a10"
REGION="us-east-2"
EC2_PATH="/opt/monitor-colegio"
S3_BUCKET="monitor-colegio-config-669294688330"

echo "========================================"
echo "  DEPLOY MONITOR COLEGIO"
echo "========================================"

# --- 1. LAMBDA: Rebuild y deploy ---
echo ""
echo "=== 1/4. Lambda (handler.py) ==="
echo "Rebuilding lambda.zip..."

cd "$(dirname "$0")/../monitor_colegio_multi/api"
zip -j lambda.zip handler.py
echo "Deploying Lambda..."
aws lambda update-function-code \
    --function-name monitor-colegio-onboarding \
    --zip-file fileb://lambda.zip \
    --region $REGION
echo "✅ Lambda deployed"

# --- 2. EC2: Subir archivos modificados via SSM ---
echo ""
echo "=== 2/4. EC2: Subiendo archivos ==="

cd "$(dirname "$0")"

# Subir archivos a S3 temporalmente y luego copiar a EC2
aws s3 cp main.py s3://$S3_BUCKET/deploy/main.py --region $REGION
aws s3 cp ec2/wa_handler.js s3://$S3_BUCKET/deploy/wa_handler.js --region $REGION
aws s3 cp ec2/send_whatsapp.js s3://$S3_BUCKET/deploy/send_whatsapp.js --region $REGION
aws s3 cp ec2/run.sh s3://$S3_BUCKET/deploy/run.sh --region $REGION
aws s3 cp src/sources/gmail_source.py s3://$S3_BUCKET/deploy/src/sources/gmail_source.py --region $REGION
aws s3 cp src/sources/wa_pdf_processor.py s3://$S3_BUCKET/deploy/src/sources/wa_pdf_processor.py --region $REGION
aws s3 cp src/sources/lirmi.py s3://$S3_BUCKET/deploy/src/sources/lirmi.py --region $REGION
aws s3 cp src/sources/lafase.py s3://$S3_BUCKET/deploy/src/sources/lafase.py --region $REGION
aws s3 cp scrape_for_user.py s3://$S3_BUCKET/deploy/scrape_for_user.py --region $REGION
echo "✅ Archivos subidos a S3"

# --- 3. EC2: Copiar de S3 a instancia via SSM ---
echo ""
echo "=== 3/4. EC2: Instalando en instancia ==="

aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters commands="[
        \"cd $EC2_PATH\",
        \"aws s3 sync s3://$S3_BUCKET/deploy/ $EC2_PATH/ --region $REGION\",
        \"chmod +x ec2/run.sh run.sh 2>/dev/null\",
        \"chown -R ubuntu:ubuntu $EC2_PATH\",
        \"echo '✅ Archivos desplegados'\",
        \"ls -la main.py wa_handler.js send_whatsapp.js run.sh src/sources/gmail_source.py src/sources/wa_pdf_processor.py\"
    ]" \
    --region $REGION \
    --output text \
    --query "Command.CommandId"

echo "✅ Comando SSM enviado"

# --- 4. ENV VARS: Agregar GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET ---
echo ""
echo "=== 4/4. Env vars ==="
echo ""
echo "⚠️  ACCIÓN MANUAL REQUERIDA:"
echo ""
echo "Agregar estas líneas al .env de la EC2 (/opt/monitor-colegio/.env):"
echo ""
echo "  GOOGLE_CLIENT_ID=<el client_id de la Lambda>"
echo "  GOOGLE_CLIENT_SECRET=<el client_secret de la Lambda>"
echo ""
echo "Puedes hacerlo con SSM:"
echo ""
echo "  aws ssm start-session --target $INSTANCE_ID --region $REGION"
echo "  # Luego en la instancia:"
echo "  echo 'GOOGLE_CLIENT_ID=xxx' >> /opt/monitor-colegio/.env"
echo "  echo 'GOOGLE_CLIENT_SECRET=xxx' >> /opt/monitor-colegio/.env"
echo ""
echo "========================================"
echo "  POST-DEPLOY"
echo "========================================"
echo ""
echo "1. Reiniciar wa_handler:"
echo "   aws ssm send-command --instance-ids $INSTANCE_ID --document-name AWS-RunShellScript \\"
echo "     --parameters commands=\"[\\\"sudo systemctl restart wa-handler\\\"]\" --region $REGION"
echo ""
echo "2. Re-autorizar Gmail desde la landing (para que el token incluya client_id/secret)"
echo "   → Ir a la landing → sección Gmail → 'Vincular Gmail' para cada usuario"
echo ""
echo "3. Limpiar archivos temporales de deploy:"
echo "   aws s3 rm s3://$S3_BUCKET/deploy/ --recursive --region $REGION"
echo ""
echo "✅ Deploy completo"
