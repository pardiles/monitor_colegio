"""Ejecuta el monitor manualmente en la EC2 (sin auto-shutdown)."""
import boto3, subprocess, time, os

ec2 = boto3.client('ec2', region_name='us-east-2')
ec2ic = boto3.client('ec2-instance-connect', region_name='us-east-2')
events = boto3.client('events', region_name='us-east-2')
ID = 'i-0ad4f13769d8bea94'
KEY = os.path.expanduser('~/.ssh/id_rsa')
PUB = open(os.path.expanduser('~/.ssh/id_rsa.pub')).read()
MODE = 'morning'  # morning o evening

# Deshabilitar EventBridge
events.disable_rule(Name='monitor-colegio-morning')
events.disable_rule(Name='monitor-colegio-evening')

# Prender EC2
ec2.start_instances(InstanceIds=[ID])
print('Starting EC2...')
time.sleep(25)

# Conectar y deshabilitar service
ip = ''
for i in range(15):
    try:
        r = ec2.describe_instances(InstanceIds=[ID])
        ip = r['Reservations'][0]['Instances'][0].get('PublicIpAddress', '')
        state = r['Reservations'][0]['Instances'][0]['State']['Name']
        if state != 'running':
            time.sleep(5)
            continue
        ec2ic.send_ssh_public_key(InstanceId=ID, InstanceOSUser='ubuntu', SSHPublicKey=PUB)
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
             '-i', KEY, f'ubuntu@{ip}',
             'sudo systemctl stop monitor-colegio.service 2>/dev/null; sudo systemctl disable monitor-colegio.service 2>/dev/null; echo DISABLED'],
            capture_output=True, text=True, timeout=10)
        if 'DISABLED' in result.stdout:
            print(f'Service disabled on {ip}')
            break
    except:
        pass
    time.sleep(3)
else:
    print('FAILED')
    exit(1)

# Copiar summarizer
print('Copying summarizer...')
ec2ic.send_ssh_public_key(InstanceId=ID, InstanceOSUser='ubuntu', SSHPublicKey=PUB)
subprocess.run(['scp', '-o', 'StrictHostKeyChecking=no', '-i', KEY,
    'src/processor/summarizer.py', f'ubuntu@{ip}:/opt/monitor-colegio/src/processor/summarizer.py'],
    timeout=10)

# Ejecutar
print(f'Running {MODE}...')
ec2ic.send_ssh_public_key(InstanceId=ID, InstanceOSUser='ubuntu', SSHPublicKey=PUB)
result = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', KEY, f'ubuntu@{ip}',
     f'cd /opt/monitor-colegio && export PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH && export HOME=/home/ubuntu && python3 main.py {MODE} 2>&1 | tail -5'],
    capture_output=True, text=True, timeout=300)
print(result.stdout)

# Re-habilitar y apagar
ec2ic.send_ssh_public_key(InstanceId=ID, InstanceOSUser='ubuntu', SSHPublicKey=PUB)
subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', '-i', KEY, f'ubuntu@{ip}',
    'sudo systemctl enable monitor-colegio.service'], capture_output=True, text=True, timeout=10)
ec2.stop_instances(InstanceIds=[ID])
events.enable_rule(Name='monitor-colegio-morning')
events.enable_rule(Name='monitor-colegio-evening')
print('Done! EC2 stopped, EventBridge re-enabled')
