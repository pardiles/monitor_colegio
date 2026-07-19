/**
 * Vinculación de WhatsApp para un usuario nuevo.
 * Genera QR, lo sube a S3, y espera a que el usuario escanee.
 * 
 * Uso: node vincular_usuario.js <user_id>
 * 
 * Flujo:
 * 1. Inicia sesión Baileys para el usuario
 * 2. Genera QR → lo convierte a PNG → lo sube a S3
 * 3. Cuando el usuario escanea, guarda la sesión en baileys_auth/{user_id}/
 * 4. Lista los grupos del usuario y los sube a S3
 * 5. Sale
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const { S3Client, PutObjectCommand, DeleteObjectCommand } = require('@aws-sdk/client-s3');
const fs = require('fs');
const path = require('path');

const BASE_DIR = '/opt/monitor-colegio';
const S3_BUCKET = 'monitor-colegio-config-669294688330';
const REGION = 'us-east-2';

const s3 = new S3Client({ region: REGION });

const userId = process.argv[2];
if (!userId) {
    console.error('Uso: node vincular_usuario.js <user_id> [method] [phone]');
    process.exit(1);
}
const method = process.argv[3] || 'qr'; // 'qr' o 'code'
const phone = process.argv[4] || '';

// Leer auth_folder desde config del usuario (si existe)
const USERS_FILE = path.join(BASE_DIR, 'config', 'users.json');
let userCfg = {};
try {
    const users = JSON.parse(fs.readFileSync(USERS_FILE, 'utf-8'));
    userCfg = users.find(u => u.id === userId) || {};
} catch {}
const authFolder = path.join(BASE_DIR, userCfg?.whatsapp?.auth_folder || `baileys_auth/${userId}`);
const qrFile = path.join('/tmp', `qr_${userId}.png`);

console.log(`[${userId}] Iniciando vinculación WhatsApp...`);
fs.mkdirSync(authFolder, { recursive: true });

let qrTimeout = null;
let connected = false;

// Safety: matar proceso anterior del mismo usuario si existe
const pidFile = path.join('/tmp', `vincular_${userId}.pid`);
try {
    const oldPid = fs.readFileSync(pidFile, 'utf-8').trim();
    if (oldPid) {
        try { process.kill(parseInt(oldPid)); console.log(`[${userId}] Proceso anterior (PID ${oldPid}) terminado`); } catch {}
    }
} catch {}
fs.writeFileSync(pidFile, String(process.pid));

// Hard timeout: salir a los 3 minutos pase lo que pase
setTimeout(() => {
    if (!connected) {
        console.log(`[${userId}] Hard timeout 3 min - saliendo`);
        process.exit(1);
    }
}, 180000);

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
    });

    sock.ev.on('creds.update', saveCreds);

    // Si es pairing code, solicitarlo apenas conecte al WS (antes de QR)
    if (method === 'code' && phone) {
        // Esperar a que el socket esté listo para solicitar pairing code
        setTimeout(async () => {
            try {
                const cleanPhone = phone.replace(/[^0-9]/g, '');
                console.log(`[${userId}] Solicitando pairing code para ${cleanPhone}...`);
                const code = await sock.requestPairingCode(cleanPhone);
                console.log(`[${userId}] Pairing code: ${code}`);
                // Guardar code en S3 para que la landing lo muestre
                await s3.send(new PutObjectCommand({
                    Bucket: S3_BUCKET,
                    Key: `whatsapp/pairing_code/${userId}.json`,
                    Body: JSON.stringify({ code, timestamp: new Date().toISOString() }),
                    ContentType: 'application/json',
                }));
                console.log(`[${userId}] Code subido a S3`);
            } catch (e) {
                console.error(`[${userId}] Error pairing code: ${e.message}`);
            }
        }, 3000);
    }

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr && method !== 'code') {
            console.log(`[${userId}] QR generado, subiendo a S3...`);
            try {
                const QRCode = require('qrcode');
                await QRCode.toFile(qrFile, qr, { width: 300, margin: 2 });
                // Subir a S3
                const fileData = fs.readFileSync(qrFile);
                await s3.send(new PutObjectCommand({
                    Bucket: S3_BUCKET,
                    Key: `whatsapp/qr/${userId}.png`,
                    Body: fileData,
                    ContentType: 'image/png',
                }));
                console.log(`[${userId}] QR subido a S3`);
            } catch (e) {
                console.error(`[${userId}] Error subiendo QR: ${e.message}`);
            }

            // Timeout: si no escanea en 2 minutos, salir
            if (qrTimeout) clearTimeout(qrTimeout);
            qrTimeout = setTimeout(() => {
                if (!connected) {
                    console.log(`[${userId}] Timeout - QR no escaneado en 2 min`);
                    process.exit(1);
                }
            }, 120000);
        }

        if (connection === 'open') {
            connected = true;
            console.log(`[${userId}] ¡WhatsApp VINCULADO!`);

            // Limpiar QR de S3
            try {
                await s3.send(new DeleteObjectCommand({ Bucket: S3_BUCKET, Key: `whatsapp/qr/${userId}.png` }));
            } catch (e) {}

            // Marcar como conectado en S3
            await s3.send(new PutObjectCommand({
                Bucket: S3_BUCKET,
                Key: `whatsapp/sessions/${userId}/creds.json`,
                Body: JSON.stringify({ status: 'connected', timestamp: new Date().toISOString() }),
                ContentType: 'application/json',
            }));

            // Esperar un momento para que carguen los grupos
            setTimeout(async () => {
                await listGroups(sock);
                await createMonitorGroup(sock);
                console.log(`[${userId}] Vinculación completada. Saliendo.`);
                process.exit(0);
            }, 5000);
        }

        if (connection === 'close') {
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log(`[${userId}] Sesión rechazada`);
                process.exit(1);
            }
            if (!connected) {
                console.log(`[${userId}] Reconectando...`);
                setTimeout(start, 3000);
            }
        }
    });
}

async function listGroups(sock) {
    try {
        const groups = await sock.groupFetchAllParticipating();
        const groupList = Object.values(groups).map(g => ({
            id: g.id,
            name: g.subject,
            participants: g.participants?.length || 0,
        }));

        console.log(`[${userId}] ${groupList.length} grupos encontrados:`);
        groupList.forEach(g => console.log(`   → ${g.name} (${g.participants} participantes)`));

        // Guardar en S3
        await s3.send(new PutObjectCommand({
            Bucket: S3_BUCKET,
            Key: `whatsapp/groups/${userId}.json`,
            Body: JSON.stringify(groupList, null, 2),
            ContentType: 'application/json',
        }));
        console.log(`[${userId}] Grupos guardados en S3`);
    } catch (e) {
        console.error(`[${userId}] Error listando grupos: ${e.message}`);
    }
}

async function createMonitorGroup(sock) {
    try {
        // Leer config del usuario para obtener destinatarios
        const usersFile = path.join(BASE_DIR, 'config', 'users.json');
        let users = [];
        try { users = JSON.parse(fs.readFileSync(usersFile, 'utf-8')); } catch {}

        // También buscar en config/users/{userId}.json (sync de S3)
        const userFile = path.join(BASE_DIR, 'config', 'users', `${userId}.json`);
        let userCfg = users.find(u => u.id === userId);
        if (!userCfg && fs.existsSync(userFile)) {
            userCfg = JSON.parse(fs.readFileSync(userFile, 'utf-8'));
        }

        if (!userCfg) {
            console.log(`[${userId}] Sin config, no se puede crear grupo monitor`);
            return;
        }

        // Obtener destinatarios
        const destinatarios = (userCfg.whatsapp?.destinatarios_monitor || [])
            .map(n => n.replace('+', '').replace(/\s/g, '') + '@s.whatsapp.net');

        if (destinatarios.length === 0) {
            console.log(`[${userId}] Sin destinatarios, saltando creación de grupo`);
            return;
        }

        // Nombre del grupo
        const apellido = userCfg.nombre?.split(' ').pop() || userId;
        const groupName = `Monitor Colegio ${apellido}`;

        console.log(`[${userId}] Creando grupo "${groupName}" con ${destinatarios.length} miembros...`);

        const group = await sock.groupCreate(groupName, destinatarios);
        const groupId = group.id;
        console.log(`[${userId}] ✅ Grupo creado: ${groupId}`);

        // Hacer admin a todos los participantes
        try {
            await sock.groupParticipantsUpdate(groupId, destinatarios, 'promote');
            console.log(`[${userId}] Todos los participantes son admin`);
        } catch (e) {
            console.log(`[${userId}] Error promoviendo admins: ${e.message}`);
        }

        // Poner imagen generada como foto del grupo (texto con nombre del colegio)
        try {
            const { createCanvas } = require('canvas');
            const colegioNombres = userCfg.colegios
                ? userCfg.colegios.map(c => c.nombre).join(' / ')
                : (userCfg.colegio?.nombre || 'Mi Colegio');

            // Generar imagen 500x500
            const canvas = createCanvas(500, 500);
            const ctx = canvas.getContext('2d');

            // Fondo gradiente azul oscuro
            const grad = ctx.createLinearGradient(0, 0, 0, 500);
            grad.addColorStop(0, '#0a0a2a');
            grad.addColorStop(1, '#1a1a4a');
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, 500, 500);

            // Emoji libro
            ctx.font = '80px serif';
            ctx.textAlign = 'center';
            ctx.fillText('📚', 250, 150);

            // "Monitor Colegio"
            ctx.font = 'bold 36px sans-serif';
            ctx.fillStyle = '#4fc3f7';
            ctx.fillText('Monitor Colegio', 250, 240);

            // Nombre del colegio (wrap si es largo)
            ctx.font = '24px sans-serif';
            ctx.fillStyle = '#e0e0e0';
            const words = colegioNombres.split(' ');
            let lines = [];
            let currentLine = '';
            for (const word of words) {
                const test = currentLine ? currentLine + ' ' + word : word;
                if (ctx.measureText(test).width > 420) {
                    lines.push(currentLine);
                    currentLine = word;
                } else {
                    currentLine = test;
                }
            }
            if (currentLine) lines.push(currentLine);
            lines.forEach((line, i) => {
                ctx.fillText(line, 250, 300 + i * 35);
            });

            // Guardar y setear
            const photoBuffer = canvas.toBuffer('image/png');
            await sock.updateProfilePicture(groupId, photoBuffer);
            console.log(`[${userId}] Foto del grupo generada y aplicada`);
        } catch (e) {
            console.log(`[${userId}] No se pudo generar/poner foto: ${e.message}`);
        }

        // Poner descripción del grupo (dinámica con nombres de hijos)
        try {
            const hijosNames = (userCfg.hijos || []).map(h => h.nombre || h.nombre_completo?.split(' ')[0] || '').filter(Boolean);
            const hijosStr = hijosNames.length > 0 ? hijosNames.join(' y ') : 'tus hijos';
            const desc = `📚 Monitor Colegio - Asistente escolar 24/7\n\n📋 Resúmenes automáticos:\n• 7:00 AM — Lo que pasa hoy\n• 20:00 PM — Novedades + preparación para mañana\n• Domingo PM — Panorama de la semana\n\n🤖 Pregúntame lo que quieras (con ?):\n• ¿A qué hora sale ${hijosNames[0] || 'mi hijo'}?\n• ¿Cuándo es la próxima prueba?\n• ¿Quién es la profesora jefe?\n\n💡 Escribe instrucciones y las anoto:\n• "${hijosNames[0] || 'Mi hijo'} no va mañana"\n• "${hijosNames[1] || hijosNames[0] || 'Mi hijo'} tiene cumpleaños viernes 17:00"`;
            await sock.groupUpdateDescription(groupId, desc);
        } catch (e) {
            console.log(`[${userId}] No se pudo setear descripción: ${e.message}`);
        }

        // Guardar el ID del grupo en S3
        await s3.send(new PutObjectCommand({
            Bucket: S3_BUCKET,
            Key: `whatsapp/monitor_group/${userId}.json`,
            Body: JSON.stringify({ group_id: groupId, name: groupName, created: new Date().toISOString() }),
            ContentType: 'application/json',
        }));

        // Enviar mensaje de bienvenida al grupo y pinearlo
        const hijosNombres = (userCfg.hijos || []).map(h => h.nombre || h.nombre_completo?.split(' ')[0] || '').filter(Boolean);
        const hijosStr = hijosNombres.length > 0 ? hijosNombres.join(' y ') : 'tus hijos';
        const ej1 = hijosNombres[0] || 'mi hijo';
        const ej2 = hijosNombres[1] || hijosNombres[0] || 'mi hijo';
        const welcomeMsg = `👋 ¡Bienvenido al Monitor Colegio!\n\nEste grupo te enviará resúmenes diarios sobre ${hijosStr}:\n• 📋 7:00 AM - Lo que pasa hoy\n• 📬 20:00 - Lo nuevo del día + mañana\n• 📅 Domingo PM - Panorama de la semana\n\n🤖 *Asistente 24/7:* Pregúntame lo que quieras (con ?):\n• "¿A qué hora sale ${ej1} mañana?"\n• "¿Cuándo es la próxima prueba?"\n• "¿Quién es la profesora jefe de ${ej2}?"\n\n💡 Escribe instrucciones y las anoto:\n• "${ej1} no va al colegio mañana"\n• "${ej2} tiene cumpleaños viernes 17:00"\n\n📌 Fija este mensaje para tenerlo siempre a mano.\n\n🚪 ¿Darte de baja? WhatsApp → Dispositivos vinculados → cierra "Google Chrome (Mac OS)". Luego: saca participantes del grupo → Salir → Eliminar grupo.`;
        const sentMsg = await sock.sendMessage(groupId, { text: welcomeMsg });
        console.log(`[${userId}] Mensaje de bienvenida enviado al grupo`);

        // Pinear el mensaje
        try {
            await sock.chatModify({ pin: true }, groupId, [sentMsg.key]);
            console.log(`[${userId}] Mensaje pineado`);
        } catch (e) {
            console.log(`[${userId}] No se pudo pinear: ${e.message}`);
        }

    } catch (e) {
        console.error(`[${userId}] Error creando grupo monitor: ${e.message}`);
    }
}

start().catch(e => {
    console.error(`[${userId}] Error fatal: ${e.message}`);
    process.exit(1);
});
