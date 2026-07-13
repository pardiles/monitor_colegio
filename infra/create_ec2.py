"""Crear nueva EC2 SIN auto-shutdown. Setup manual después."""
import boto3
import time
import subprocess
import os
import base64

REGION = 'us-east-2'
KEY_PATH = os.path.expanduser('~/.ssh/id_rsa')
PUB_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa.pub')
SG_ID = 'sg-0956c7e5af16ed1a4'
AMI = 'ami-0933f4f9e0a0fc3a5'  # Ubuntu 24.04
INSTANCE_PROFILE = 'monitor-colegio-ec2-role'

# UserData que instala todo pero NO habilita el service
USERDATA = """#!/bin/bash
apt-get update -y
apt-get install -y python3-pip python3-venv nodejs npm fonts-liberation libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libcups2
mkdir -p /opt/monitor-colegio
chown ubuntu:ubuntu /opt/monitor-colegio
su - ubuntu -c "pip3 install --user --break-system-packages anthropic playwright google-auth google-auth-oauthlib google-api-python-client python-dotenv requests"
su - ubuntu -c "python3 -m playwright install chromium --with-deps"
su - ubuntu -c "cd /opt/monitor-colegio && npm init -y && npm install @whiskeysockets/baileys qrcode-terminal"
echo "SETUP DONE" > /tmp/setup-complete
"""

ec2 = boto3.client('ec2', region_name=REGION)
ec2ic = boto3.client('ec2-instance-connect', region_name=REGION)

# Esperar que la vieja termine
print("Esperando que termine la instancia vieja...")
time.sleep(30)

# Crear nueva instancia
print("Creando nueva EC2 t3.small...")
resp = ec2.run_instances(
    ImageId=AMI,
    InstanceType='t3.small',
    MinCount=1, MaxCount=1,
    SecurityGroupIds=[SG_ID],
    UserData=USERDATA,
    TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': [{'Key': 'Name', 'Value': 'monitor-colegio'}]
    }],
    IamInstanceProfile={'Name': 'monitor-colegio-MonitorInstanceProfile-XyoAUKJWz6RE'},
)
instance_id = resp['Instances'][0]['InstanceId']
print(f"Instance: {instance_id}")

# Esperar running
print("Esperando running...")
waiter = ec2.get_waiter('instance_running')
waiter.wait(InstanceIds=[instance_id])

resp = ec2.describe_instances(InstanceIds=[instance_id])
ip = resp['Reservations'][0]['Instances'][0]['PublicIpAddress']
print(f"IP: {ip}")

# Esperar setup (cloud-init)
print("Esperando setup (90s)...")
time.sleep(90)

# Conectar
print("Conectando via SSH...")
pub_key = open(PUB_KEY_PATH).read()

for attempt in range(5):
    try:
        ec2ic.send_ssh_public_key(
            InstanceId=instance_id,
            InstanceOSUser='ec2-user',
            SSHPublicKey=pub_key
        )
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
             '-i', KEY_PATH, f'ec2-user@{ip}', 'cat /tmp/setup-complete'],
            capture_output=True, text=True, timeout=15
        )
        if 'SETUP DONE' in result.stdout:
            print(f"✅ EC2 lista! ID: {instance_id} IP: {ip}")
            break
        print(f"  Intento {attempt+1}: esperando cloud-init...")
    except Exception as e:
        print(f"  Intento {attempt+1}: {e}")
    time.sleep(15)
else:
    print(f"EC2 creada pero cloud-init aún corriendo. ID: {instance_id} IP: {ip}")

# Guardar info
with open('infra/ec2_info.txt', 'w') as f:
    f.write(f"INSTANCE_ID={instance_id}\nIP={ip}\n")
print(f"\nGuardado en infra/ec2_info.txt")
print(f"Siguiente: copiar proyecto y configurar")
