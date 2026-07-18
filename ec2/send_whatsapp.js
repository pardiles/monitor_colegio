/**
 * Envía resumen por WhatsApp usando Baileys (EC2).
 * Lee el mensaje desde data/mensaje_enviar_{user_id}.json
 * 
 * Uso:
 *   node send_whatsapp.js pablo
 *   node send_whatsapp.js oscar
 *   node send_whatsapp.js kevin
 */

const { default: makeWASocket, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const fs = require('fs');
const path = require('path');

const BASE_DIR = '/opt/monitor-colegio';
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
const authFolder = path.join(BASE_DIR, waCfg.auth_folder || `baileys_auth/${userId}`);

// Determinar destinos
let targets = [];
if (waCfg.grupo_monitor) {
    // Enviar al grupo monitor del usuario
    targets = [waCfg.grupo_monitor];
} else if (waCfg.destinatarios_monitor && waCfg.destinatarios_monitor.length > 0) {
    // Enviar directo a los números
    targets = waCfg.destinatarios_monitor.map(n => n.replace('+', '') + '@s.whatsapp.net');
} else {
    console.error(`[${userId}] Sin destino configurado`);
    process.exit(1);
}

// Leer mensaje
const msgFile = path.join(BASE_DIR, `data/mensaje_enviar_${userId}.json`);
// Fallback: buscar por id parcial (pablo_ardiles → pablo)
const msgFileFull = path.join(BASE_DIR, `data/mensaje_enviar_${userCfg.id}.json`);
const messageData = loadJSON(msgFile) || loadJSON(msgFileFull);

if (!messageData || !messageData.mensaje) {
    console.error(`[${userId}] Sin mensaje en ${msgFile}`);
    process.exit(1);
}

const mensaje = messageData.mensaje.replace(/\*\*/g, '*');
console.log(`[${userId}] Enviando (${mensaje.length} chars)...`);

async function send() {
    if (!fs.existsSync(authFolder)) {
        console.error(`[${userId}] Sin auth en ${authFolder}. Vincular primero.`);
        process.exit(1);
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const sock = makeWASocket({ auth: state, printQRInTerminal: false });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        if (update.connection === 'open') {
            console.log(`[${userId}] Conectado!`);
            try {
                for (const target of targets) {
                    await sock.sendMessage(target, { text: mensaje });
                    console.log(`[${userId}] Enviado a ${target}`);
                }
                // Marcar como enviado en S3
                try {
                    const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
                    const s3 = new S3Client({ region: 'us-east-2' });
                    await s3.send(new PutObjectCommand({
                        Bucket: 'monitor-colegio-config-669294688330',
                        Key: `whatsapp/sent/${userId}.json`,
                        Body: JSON.stringify({ sent: true, timestamp: new Date().toISOString() }),
                        ContentType: 'application/json',
                    }));
                    console.log(`[${userId}] Flag de envío guardado en S3`);
                } catch(s3err) {
                    console.log(`[${userId}] No se pudo guardar flag S3: ${s3err.message}`);
                }
            } catch (e) {
                console.error(`[${userId}] Error enviando: ${e.message}`);
            }
            setTimeout(() => process.exit(0), 2000);
        }
        if (update.connection === 'close') {
            console.error(`[${userId}] No se pudo conectar`);
            process.exit(1);
        }
    });
}

send();
