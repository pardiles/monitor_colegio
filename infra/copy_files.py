"""Copia archivos actualizados a la EC2."""
import boto3, subprocess, os

ec2ic = boto3.client('ec2-instance-connect', region_name='us-east-2')
ID = 'i-0ad4f13769d8bea94'
KEY = os.path.expanduser('~/.ssh/id_rsa')
PUB = open(os.path.expanduser('~/.ssh/id_rsa.pub')).read()
ip = '18.220.188.119'

files = [
    ('main.py', '/opt/monitor-colegio/main.py'),
    ('src/processor/summarizer.py', '/opt/monitor-colegio/src/processor/summarizer.py'),
    ('src/calendar_store.py', '/opt/monitor-colegio/src/calendar_store.py'),
    ('ec2/fetch_whatsapp.js', '/opt/monitor-colegio/fetch_whatsapp.js'),
]

for local, remote in files:
    ec2ic.send_ssh_public_key(InstanceId=ID, InstanceOSUser='ubuntu', SSHPublicKey=PUB)
    r = subprocess.run(['scp', '-o', 'StrictHostKeyChecking=no', '-i', KEY, local, f'ubuntu@{ip}:{remote}'],
                       capture_output=True, text=True, timeout=10)
    status = "OK" if r.returncode == 0 else "FAIL"
    print(f"  {local}: {status}")

print("All copied!")
