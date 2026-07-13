#!/bin/bash
# Deploy de la infraestructura Monitor Colegio

STACK_NAME="monitor-colegio"
REGION="us-east-2"
KEY_NAME="monitor-colegio-key"

echo "1. Creando key pair..."
aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --query 'KeyMaterial' \
  --output text \
  --region $REGION > monitor-colegio-key.pem 2>/dev/null || echo "Key ya existe"

echo "2. Desplegando CloudFormation stack..."
aws cloudformation deploy \
  --template-file infra/cloudformation.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides KeyPairName=$KEY_NAME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

echo "3. Obteniendo outputs..."
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs' \
  --output table \
  --region $REGION

echo "Done!"
