/**
 * WhatsApp Listener Multi-Sesión.
 * Lee config/users.json y abre una sesión Baileys por cada usuario
 * que tenga auth guardada (baileys_auth/{user_id}/).
 * 
 * Mensajes se guardan en data/whatsapp_messages.json (compartido)
 * y data/monitor_inputs_{user_id}.json (instrucciones por usuario).
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } = require('@whiskeysockets/baileys');
const fs = require('fs');
const path = require('path');

const BASE_DIR = '/opt/monitor-colegio';
const DATA_DIR = path.join(BASE_DIR, 'data');
const ATTACHMENTS_DIR = path.join(DATA_DIR, 'attachments');
const USERS_FILE = path.join(BASE_DIR, 'config', 'users.json');
const WA_MESSAGES_FILE = path.join(DATA_DIR, 'whatsapp_messages.json');

function loadJSON(file, fallback) {
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')); }
    catch { return fallback !== undefined ? fallback : {}; }
}

function saveJSON(file, data) {
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf-8');
}

function cleanOld(arr) {
    const weekAgo = Math.floor(Date.now() / 1000) - 7 * 24 * 60 * 60;
    return arr.filter(m => (m.timestamp || 0) > weekAgo);
}

/**
 * Inicia una sesión Baileys para un usuario.
 * Retorna el socket para uso en outbox.
 */
async function startSession(userCfg) {
    const userId = userCfg.id;
    const waCfg = userCfg.whatsapp || {};
    const authFolder = path.join(BASE_DIR, waCfg.auth_folder || `baileys_auth/${userId}`);
    const groups = waCfg.grupos_lectura || {};
    const monitorGroup = waCfg.grupo_monitor || null;

    // Solo iniciar si tiene auth guardada
    if (!fs.existsSync(authFolder)) {
        console.log(`[${userId}] Sin auth en ${authFolder}, saltando`);
        return null;
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const sock = makeWASocket({ auth: state, printQRInTerminal: false });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', (m) => {
        for (const msg of m.messages) {
            const groupId = msg.key.remoteJid;
            const label = groups[groupId];
            const isMonitor = monitorGroup && groupId === monitorGroup;

            if (!label && !isMonitor) continue;

            const body = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
            const docMsg = msg.message?.documentMessage || msg.message?.documentWithCaptionMessage?.message?.documentMessage;

            if (!body && !docMsg) continue;

            const ts = msg.messageTimestamp ? Number(msg.messageTimestamp) : Math.floor(Date.now() / 1000);
            const entry = {
                from: msg.pushName || 'desconocido',
                time: new Date(ts * 1000).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' }),
                date: new Date(ts * 1000).toISOString().split('T')[0],
                body: body,
                timestamp: ts,
            };

            // PDF adjunto
            if (docMsg && docMsg.mimetype === 'application/pdf') {
                const fileName = docMsg.fileName || `doc_${ts}.pdf`;
                entry.attachment = { type: 'pdf', filename: fileName, mimetype: docMsg.mimetype };
                (async () => {
                    try {
                        const buffer = await downloadMediaMessage(msg, 'buffer', {});
                        fs.mkdirSync(ATTACHMENTS_DIR, { recursive: true });
                        const savePath = path.join(ATTACHMENTS_DIR, `${userId}_${label || 'monitor'}_${ts}_${fileName}`);
                        fs.writeFileSync(savePath, buffer);
                        console.log(`[${userId}][PDF] ${savePath} (${buffer.length} bytes)`);
                    } catch (e) {
                        console.log(`[${userId}][PDF] Error: ${e.message}`);
                    }
                })();
            }

            // Monitor group (instrucciones de los padres)
            if (isMonitor) {
                // Ignorar mensajes del bot (emojis de resumen)
                if (body.startsWith('\u{1F4CB}') || body.startsWith('\u{1F4EC}') || body.startsWith('\u{1F680}') || body.startsWith('\u{1F9EA}')) return;
                const monitorFile = path.join(DATA_DIR, `monitor_inputs_${userId}.json`);
                const monitor = loadJSON(monitorFile, []);
                monitor.push(entry);
                saveJSON(monitorFile, cleanOld(monitor));
                console.log(`[${userId}][MONITOR] ${entry.from}: ${body.substring(0, 50)}`);
            } else if (label) {
                // Grupo del colegio
                const messages = loadJSON(WA_MESSAGES_FILE, {});
                if (!messages[label]) messages[label] = [];
                messages[label].push(entry);
                messages[label] = cleanOld(messages[label]);
                saveJSON(WA_MESSAGES_FILE, messages);
                console.log(`[${userId}][${label}] ${entry.from}: ${(body || entry.attachment?.filename || '').substring(0, 50)}`);
            }
        }
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'open') {
            console.log(`[${userId}] WhatsApp ONLINE (${waCfg.phone})`);
            sock._isOnline = true;
            // Guardar lista de grupos localmente para list_groups.js
            (async () => {
                try {
                    const groups = await sock.groupFetchAllParticipating();
                    const groupList = Object.values(groups).map(g => ({
                        id: g.id, name: g.subject, participants: g.participants?.length || 0,
                    }));
                    const groupsFile = path.join(DATA_DIR, `groups_${userId}.json`);
                    fs.writeFileSync(groupsFile, JSON.stringify(groupList, null, 2));
                    console.log(`[${userId}] ${groupList.length} grupos guardados localmente`);
                } catch (e) {
                    console.log(`[${userId}] Error guardando grupos: ${e.message}`);
                }
            })();
        }
        if (connection === 'close') {
            sock._isOnline = false;
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log(`[${userId}] LOGGED OUT - necesita re-vincular QR`);
                return; // No reconectar si fue logout manual
            }
            console.log(`[${userId}] Desconectado, reconectando en 5s...`);
            setTimeout(async () => {
                const newSock = await startSession(userCfg);
                if (newSock && global._activeSessions) {
                    global._activeSessions[userId] = newSock;
                }
            }, 5000);
        }
    });

    return sock;
}

// --- MAIN ---
async function main() {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.mkdirSync(path.join(DATA_DIR, 'outbox'), { recursive: true });

    // Cargar usuarios
    const users = loadJSON(USERS_FILE, []);
    if (users.length === 0) {
        console.log('No hay usuarios en config/users.json');
        return;
    }

    console.log(`Starting WhatsApp listener for ${users.length} usuarios...`);

    // Map de sesiones activas para envío via outbox
    const activeSessions = {};
    global._activeSessions = activeSessions;

    // Iniciar sesión para cada usuario que tenga auth
    for (const userCfg of users) {
        const authFolder = path.join(BASE_DIR, userCfg.whatsapp?.auth_folder || `baileys_auth/${userCfg.id}`);
        if (fs.existsSync(authFolder)) {
            try {
                const sock = await startSession(userCfg);
                if (sock) activeSessions[userCfg.id] = sock;
                console.log(`[${userCfg.id}] Sesión iniciada`);
            } catch (e) {
                console.log(`[${userCfg.id}] Error: ${e.message}`);
            }
            // Pequeña pausa entre conexiones para no parecer sospechoso
            await new Promise(r => setTimeout(r, 2000));
        }
    }

    console.log('Todas las sesiones iniciadas. Escuchando mensajes...');

    // --- OUTBOX WATCHER: Revisar mensajes pendientes cada 3s ---
    const OUTBOX_DIR = path.join(DATA_DIR, 'outbox');
    setInterval(() => {
        try {
            const files = fs.readdirSync(OUTBOX_DIR).filter(f => f.endsWith('.json'));
            for (const file of files) {
                const filePath = path.join(OUTBOX_DIR, file);
                const data = loadJSON(filePath, null);
                if (!data || data.status !== 'pending') continue;

                const userId = data.user_id;
                const sock = activeSessions[userId];
                if (!sock || !sock._isOnline) {
                    // Socket not connected yet, skip for now
                    continue;
                }

                // Mark as processing to avoid re-entry
                data.status = 'processing';
                saveJSON(filePath, data);

                (async () => {
                    try {
                        for (const target of data.targets) {
                            await sock.sendMessage(target, { text: data.message });
                            console.log(`[${userId}][OUTBOX] Enviado a ${target}`);
                        }
                        data.status = 'sent';
                        data.sent_at = new Date().toISOString();
                        saveJSON(filePath, data);
                        console.log(`[${userId}][OUTBOX] ✅ Completado`);

                        // Limpiar archivo después de 5 min
                        setTimeout(() => {
                            try { fs.unlinkSync(filePath); } catch {}
                        }, 300000);
                    } catch (e) {
                        console.log(`[${userId}][OUTBOX] Error: ${e.message}`);
                        data.status = 'error';
                        data.error = e.message;
                        saveJSON(filePath, data);
                    }
                })();
            }
        } catch (e) {
            // Silently ignore outbox errors
        }
    }, 3000);
}

// Exportar (outbox es el método preferido de envío)
module.exports = { };

// Si se ejecuta directamente (no require'd)
if (require.main === module) {
    main().catch(e => { console.error('Fatal:', e); process.exit(1); });
}
