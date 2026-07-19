import json
users = json.load(open('/opt/monitor-colegio/config/users.json'))
p = next(x for x in users if x['id'] == 'pablo_ardiles')
p['whatsapp']['grupo_monitor'] = '120363424120926627@g.us'
p['whatsapp']['destinatarios_monitor'] = ['56968983699']
json.dump(users, open('/opt/monitor-colegio/config/users.json', 'w'), indent=2, ensure_ascii=False)
print("FIXED - grupo_monitor set to new group, solo Pablo")
