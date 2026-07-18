/**
 * WhatsApp Listener multi-usuario.
 * Lee config/users.json y crea una conexión Baileys por cada usuario.
 */
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const fs = require('fs');
const path = require('path');

const CONFIG_FILE = path.join(__dirname, 'config', 'users.json');
const BASE_DIR = __dirname;

function loadUsers() {
    return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
}

function loadJSON(file) {
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')); } catch { return []; }
}

function saveJSON(file, data) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf-8');
}

function cleanOld(arr) {
    const weekAgo = Math.floor(Date.now() / 1000) - 7 * 24 * 60 * 60;
    return arr.filter(m => (m.timestamp || 0) > weekAgo);
}

async function startUserListener(user) {
    const authFolder = path.join(BASE_DIR, user.whatsapp.auth_folder);
    const dataDir = path.join(BASE_DIR, 'data', user.id);
    const msgFile = path.join(dataDir, 'whatsapp_messages.json');
    const monitorFile = path.join(dataDir, 'monitor_inputs.json');

    fs.mkdirSync(dataDir, { recursive: true });
    fs.mkdirSync(authFolder, { recursive: true });

    const allGroups = { ...user.whatsapp.grupos_lectura };
    if (user.whatsapp.grupo_monitor) {
        allGroups[user.whatsapp.grupo_monitor] = 'monitor_colegio';
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const sock = makeWASocket({ auth: state });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', (m) => {
        for (const msg of m.messages) {
            const groupId = msg.key.remoteJid;
            const label = allGroups[groupId];
            if (!label) continue;

            const body = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
            if (!body) continue;

            const ts = msg.messageTimestamp ? Number(msg.messageTimestamp) : Math.floor(Date.now() / 1000);
            const entry = {
                from: msg.pushName || 'desconocido',
                time: new Date(ts * 1000).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' }),
                date: new Date(ts * 1000).toISOString().split('T')[0],
                body: body,
                timestamp: ts,
            };

            if (label === 'monitor_colegio') {
                if (body.startsWith('\u{1F4CB}') || body.startsWith('\u{1F4EC}') || body.startsWith('\u{1F680}') || body.startsWith('\u{1F9EA}')) return;
                const monitor = loadJSON(monitorFile);
                monitor.push(entry);
                saveJSON(monitorFile, cleanOld(monitor));
                console.log(`[${user.id}][MONITOR] ${entry.from}: ${body.substring(0, 50)}`);
            } else {
                const messages = loadJSON(msgFile);
                if (!Array.isArray(messages)) {
                    const obj = messages;
                    // Convert old format to new
                }
                let msgObj = {};
                try { msgObj = JSON.parse(fs.readFileSync(msgFile, 'utf-8')); } catch { msgObj = {}; }
                if (!msgObj[label]) msgObj[label] = [];
                msgObj[label].push(entry);
                msgObj[label] = cleanOld(msgObj[label]);
                saveJSON(msgFile, msgObj);
                console.log(`[${user.id}][${label}] ${entry.from}: ${body.substring(0, 50)}`);
            }
        }
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'open') console.log(`[${user.id}] WhatsApp ONLINE`);
        if (connection === 'close') {
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log(`[${user.id}] LOGGED OUT - need new QR`);
                return;
            }
            console.log(`[${user.id}] Reconnecting...`);
            setTimeout(() => startUserListener(user), 5000);
        }
    });
}

// Main
console.log('Loading users...');
const users = loadUsers();
console.log(`Found ${users.length} users`);

for (const user of users) {
    if (user.whatsapp && user.whatsapp.auth_folder) {
        console.log(`Starting listener for ${user.id}...`);
        startUserListener(user).catch(e => console.error(`[${user.id}] Error:`, e.message));
    }
}
