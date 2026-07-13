"""
Fix: Conectar a la EC2 apenas arranca y deshabilitar el service.
Corre este script, prende la EC2, y conecta rápido antes de que se apague.
"""
import boto3
import time
import subprocess
import os

EC2_ID = 'i-07385fb3d20c2749b'
REGION = 'us-east-2'
KEY_PATH = os.path.expanduser('~/.ssh/id_rsa')
PUB_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa.pub')

ec2 = boto3.client('ec2', region_name=REGION)
ec2ic = boto3.client('ec2-instance-connect', region_name=REGION)

# 1. Asegurar que está stopped
print("1. Verificando estado...")
resp = ec2.describe_instances(InstanceIds=[EC2_ID])
state = resp['Reservations'][0]['Instances'][0]['State']['Name']
print(f"   Estado: {state}")

if state != 'stopped':
    print("   Esperando que se detenga...")
    ec2.stop_instances(InstanceIds=[EC2_ID])
    waiter = ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=[EC2_ID])

# 2. Prender
print("2. Prendiendo EC2...")
ec2.start_instances(InstanceIds=[EC2_ID])
waiter = ec2.get_waiter('instance_running')
waiter.wait(InstanceIds=[EC2_ID])
print("   Running!")

# 3. Esperar que SSH esté listo e intentar conectar rápido
print("3. Intentando conectar (loop de 10 intentos)...")
resp = ec2.describe_instances(InstanceIds=[EC2_ID])
ip = resp['Reservations'][0]['Instances'][0].get('PublicIpAddress', '')
print(f"   IP: {ip}")

time.sleep(15)  # Esperar boot mínimo

pub_key = open(PUB_KEY_PATH).read()

for attempt in range(10):
    try:
        # Push SSH key
        ec2ic.send_ssh_public_key(
            InstanceId=EC2_ID,
            InstanceOSUser='ec2-user',
            SSHPublicKey=pub_key
        )
        
        # Intentar SSH inmediato
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
             '-i', KEY_PATH, f'ec2-user@{ip}',
             'sudo systemctl disable monitor-colegio.service; sudo systemctl stop monitor-colegio.service; echo FIXED'],
            capture_output=True, text=True, timeout=10
        )
        
        if 'FIXED' in result.stdout:
            print(f"   ✅ Service deshabilitado! (intento {attempt+1})")
            print("4. EC2 lista para recibir archivos.")
            print(f"   IP: {ip}")
            break
        else:
            print(f"   Intento {attempt+1}: {result.stderr.strip()[:50]}")
    except Exception as e:
        print(f"   Intento {attempt+1}: {str(e)[:50]}")
    
    time.sleep(3)
else:
    print("   ❌ No se pudo conectar. La EC2 se apagó.")
