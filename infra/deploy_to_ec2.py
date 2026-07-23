"""Deploy completo del proyecto a la EC2 y ejecutar test."""
import boto3
import subprocess
import os
import time

REGION = 'us-east-2'
KEY_PATH = os.path.expanduser('~/.ssh/id_rsa')
PUB_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa.pub')

# Leer info de la EC2
with open('infra/ec2_info.txt') as f:
    lines = f.read().strip().split('\n')
    info = dict(l.split('=', 1) for l in lines)
INSTANCE_ID = info['INSTANCE_ID']
IP = info['IP']

ec2ic = boto3.client('ec2-instance-connect', region_name=REGION)
pub_key = open(PUB_KEY_PATH).read()

def ssh_cmd(cmd, timeout=30):
    ec2ic.send_ssh_public_key(InstanceId=INSTANCE_ID, InstanceOSUser='ec2-user', SSHPublicKey=pub_key)
    result = subprocess.run(
        ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
         '-i', KEY_PATH, f'ec2-user@{IP}', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout + result.stderr

def scp_files(local_files, remote_dir):
    ec2ic.send_ssh_public_key(InstanceId=INSTANCE_ID, InstanceOSUser='ec2-user', SSHPublicKey=pub_key)
    cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-i', KEY_PATH] + local_files + [f'ec2-user@{IP}:{remote_dir}']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0

def scp_recursive(local_dir, remote_dir):
    ec2ic.send_ssh_public_key(InstanceId=INSTANCE_ID, InstanceOSUser='ec2-user', SSHPublicKey=pub_key)
    cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-r', '-i', KEY_PATH, local_dir, f'ec2-user@{IP}:{remote_dir}']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode == 0

print(f"Deploying to {IP} ({INSTANCE_ID})")

# 1. Copiar código fuente
print("\n1. Copiando código fuente...")
scp_recursive('src', '/opt/monitor-colegio/')
scp_files(['main.py', '.env', 'credentials.json', 'token.json'], '/opt/monitor-colegio/')
scp_files(['ec2/wa_handler.js', 'ec2/send_whatsapp.js', 'ec2/run.sh'], '/opt/monitor-colegio/')
scp_recursive('data', '/opt/monitor-colegio/')
print("   OK")

# 2. Instalar dependencias Python
print("\n2. Instalando deps Python...")
out = ssh_cmd("cd /opt/monitor-colegio && pip3.11 install --user anthropic playwright google-auth google-auth-oauthlib google-api-python-client python-dotenv requests 2>&1 | tail -2", timeout=120)
print(f"   {out.strip()[-80:]}")

# 3. Instalar Playwright browser
print("\n3. Instalando Playwright Chromium...")
out = ssh_cmd("python3.11 -m playwright install chromium 2>&1 | tail -2", timeout=120)
print(f"   {out.strip()[-80:]}")

# 4. Instalar deps Node (WAHA handles WhatsApp, no Baileys needed)
print("\n4. Node deps (mínimo)...")
out = ssh_cmd("cd /opt/monitor-colegio && npm init -y 2>/dev/null", timeout=120)
print(f"   {out.strip()[-80:]}")

# 5. Configurar run.sh
print("\n5. Configurando run.sh...")
out = ssh_cmd("chmod +x /opt/monitor-colegio/run.sh && cat /opt/monitor-colegio/run.sh | head -3")
print(f"   {out.strip()}")

# 6. Verificar archivos
print("\n6. Verificando archivos...")
out = ssh_cmd("ls /opt/monitor-colegio/main.py /opt/monitor-colegio/.env /opt/monitor-colegio/src/processor/summarizer.py /opt/monitor-colegio/wa_handler.js /opt/monitor-colegio/send_whatsapp.js 2>&1")
print(f"   {out.strip()}")

print(f"\n✅ Deploy completo! EC2: {IP}")
print("WAHA (Docker) maneja WhatsApp. wa_handler.js recibe webhooks + envía outbox.")
