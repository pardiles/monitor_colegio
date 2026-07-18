/**
 * Envía resumen por WhatsApp usando la sesión del wa_listener.
 * NO abre su propia conexión (causaría conflicto "replaced").
 * 
 * Método: Escribe un archivo "outbox" que wa_listener detecta y envía.
 * Si wa_listener no envía en 30s, intenta envío directo como fallback.
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
const msgFile = path.join(BASE_DIR, `data/mensaje_enviar_${userId}.json`);
const msgFileFull = path.join(BASE_DIR, `data/mensaje_enviar_${userCfg.id}.json`);
const messageData = loadJSON(msgFile) || loadJSON(msgFileFull);

if (!messageData || !messageData.mensaje) {
    console.error(`[${userId}] Sin mensaje en ${msgFile}`);
    process.exit(1);
}

const mensaje = messageData.mensaje.replace(/\*\*/g, '*');
console.log(`[${userId}] Mensaje listo (${mensaje.length} chars), enviando via outbox...`);

// Escribir en outbox para que wa_listener lo recoja
fs.mkdirSync(OUTBOX_DIR, { recursive: true });
const outboxFile = path.join(OUTBOX_DIR, `${userId}_${Date.now()}.json`);
const outboxData = {
    user_id: userId,
    targets: targets,
    message: mensaje,
    created_at: new Date().toISOString(),
    status: 'pending',
};
fs.writeFileSync(outboxFile, JSON.stringify(outboxData, null, 2));
console.log(`[${userId}] Outbox escrito: ${outboxFile}`);

// Esperar a que wa_listener lo procese (máx 60s)
let waited = 0;
const pollInterval = setInterval(() => {
    waited += 2;
    try {
        const data = loadJSON(outboxFile);
        if (data && data.status === 'sent') {
            console.log(`[${userId}] ✅ Mensaje enviado por wa_listener`);
            clearInterval(pollInterval);
            // Marcar en S3
            markSentInS3().then(() => process.exit(0)).catch(() => process.exit(0));
            return;
        }
        if (data && data.status === 'error') {
            console.error(`[${userId}] ❌ Error: ${data.error}`);
            clearInterval(pollInterval);
            process.exit(1);
            return;
        }
    } catch {}

    if (waited >= 60) {
        console.error(`[${userId}] Timeout esperando wa_listener. Intentando envío directo...`);
        clearInterval(pollInterval);
        sendDirect();
    }
}, 2000);

async function sendDirect() {
    // Fallback: conectar directamente (puede causar conflicto breve)
    const { default: makeWASocket, useMultiFileAuthState } = require('@whiskeysockets/baileys');
    const authFolder = path.join(BASE_DIR, waCfg.auth_folder || `baileys_auth/${userId}`);

    if (!fs.existsSync(authFolder)) {
        console.error(`[${userId}] Sin auth en ${authFolder}`);
        process.exit(1);
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const sock = makeWASocket({ auth: state, printQRInTerminal: false });
    sock.ev.on('creds.update', saveCreds);

    const timeout = setTimeout(() => {
        console.error(`[${userId}] Timeout en envío directo`);
        process.exit(1);
    }, 30000);

    sock.ev.on('connection.update', async (update) => {
        if (update.connection === 'open') {
            try {
                for (const target of targets) {
                    await sock.sendMessage(target, { text: mensaje });
                    console.log(`[${userId}] Enviado directo a ${target}`);
                }
                // Marcar outbox como enviado
                try {
                    const d = loadJSON(outboxFile) || outboxData;
                    d.status = 'sent';
                    fs.writeFileSync(outboxFile, JSON.stringify(d, null, 2));
                } catch {}
                await markSentInS3();
            } catch (e) {
                console.error(`[${userId}] Error envío directo: ${e.message}`);
            }
            clearTimeout(timeout);
            setTimeout(() => process.exit(0), 2000);
        }
        if (update.connection === 'close') {
            console.error(`[${userId}] No se pudo conectar directamente`);
            clearTimeout(timeout);
            process.exit(1);
        }
    });
}

async function markSentInS3() {
    try {
        const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
        const s3 = new S3Client({ region: 'us-east-2' });
        await s3.send(new PutObjectCommand({
            Bucket: 'monitor-colegio-config-669294688330',
            Key: `whatsapp/sent/${userId}.json`,
            Body: JSON.stringify({ sent: true, timestamp: new Date().toISOString() }),
            ContentType: 'application/json',
        }));
        console.log(`[${userId}] Flag S3 guardado`);
    } catch (e) {
        console.log(`[${userId}] Error flag S3: ${e.message}`);
    }
}
