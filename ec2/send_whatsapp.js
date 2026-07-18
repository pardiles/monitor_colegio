/**
 * Envía resumen por WhatsApp usando la sesión del wa_listener.
 * Escribe un archivo "outbox" que wa_listener detecta y envía.
 * Sale inmediatamente después de escribir — no espera confirmación.
 * 
 * Uso:
 *   node send_whatsapp.js pablo_ardiles
 *   node send_whatsapp.js oscar_ardiles
 */

const fs = require('fs');
const path = require('path');

const BASE_DIR = '/opt/monitor-colegio';
const DATA_DIR = path.join(BASE_DIR, 'data');
const OUTBOX_DIR = path.join(DATA_DIR, 'outbox');
const USERS_FILE = path.join(BASE_DIR, 'config', 'users.json');

function loadJSON(file) {
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')); }
    catch { return null; }
}

const userId = process.argv[2];
if (!userId) {
    console.error('Uso: node send_whatsapp.js <user_id>');
    process.exit(1);
}

// Cargar config del usuario
const users = loadJSON(USERS_FILE) || [];
const userCfg = users.find(u => u.id === userId || u.id.includes(userId));

if (!userCfg) {
    console.error(`Usuario '${userId}' no encontrado en users.json`);
    process.exit(1);
}

const waCfg = userCfg.whatsapp || {};

// Determinar destinos
let targets = [];
if (waCfg.grupo_monitor) {
    targets = [waCfg.grupo_monitor];
} else if (waCfg.destinatarios_monitor && waCfg.destinatarios_monitor.length > 0) {
    targets = waCfg.destinatarios_monitor.map(n => n.replace('+', '') + '@s.whatsapp.net');
} else {
    console.error(`[${userId}] Sin destino configurado`);
    process.exit(1);
}

// Leer mensaje
const msgFile = path.join(DATA_DIR, `mensaje_enviar_${userId}.json`);
const msgFileFull = path.join(DATA_DIR, `mensaje_enviar_${userCfg.id}.json`);
const messageData = loadJSON(msgFile) || loadJSON(msgFileFull);

if (!messageData || !messageData.mensaje) {
    console.error(`[${userId}] Sin mensaje en ${msgFile}`);
    process.exit(1);
}

const mensaje = messageData.mensaje.replace(/\*\*/g, '*');
console.log(`[${userId}] Mensaje listo (${mensaje.length} chars), escribiendo outbox...`);

// Escribir en outbox para que wa_listener lo recoja
fs.mkdirSync(OUTBOX_DIR, { recursive: true, mode: 0o777 });
const outboxFile = path.join(OUTBOX_DIR, `${userId}_${Date.now()}.json`);
const outboxData = {
    user_id: userId,
    targets: targets,
    message: mensaje,
    created_at: new Date().toISOString(),
    status: 'pending',
};
fs.writeFileSync(outboxFile, JSON.stringify(outboxData, null, 2), { mode: 0o666 });
// Force permissions (umask may override mode)
try { fs.chmodSync(outboxFile, 0o666); } catch {}
console.log(`[${userId}] ✅ Outbox escrito: ${path.basename(outboxFile)}`);
console.log(`[${userId}] wa_listener lo enviará en ~3s`);

// Salir inmediatamente — wa_listener se encarga del envío
process.exit(0);
