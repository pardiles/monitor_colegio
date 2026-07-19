import json
users = json.load(open('/opt/monitor-colegio/config/users.json'))
p = next(x for x in users if x['id'] == 'pablo_ardiles')
p['whatsapp']['grupo_monitor'] = '120363428832881039@g.us'
json.dump(users, open('/opt/monitor-colegio/config/users.json', 'w'), indent=2, ensure_ascii=False)
print("FIXED - grupo_monitor set to new group")
