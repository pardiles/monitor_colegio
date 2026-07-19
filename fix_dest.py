import json
users = json.load(open('/opt/monitor-colegio/config/users.json'))
p = next(x for x in users if x['id'] == 'pablo_ardiles')
p['whatsapp']['destinatarios_monitor'] = ['56968983699']
p['whatsapp']['grupo_monitor'] = None
json.dump(users, open('/opt/monitor-colegio/config/users.json', 'w'), indent=2, ensure_ascii=False)
print("FIXED - destinatarios = solo Pablo, grupo_monitor = None")
