const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const fs = require('fs');

const GROUPS = {
    '120363022899821958@g.us': '5A_franco',
    '120363407876876956@g.us': '1C_blanca',
    '120363024586413625@g.us': '5to_sharks_franco',
    '120363409985436264@g.us': 'monitor_colegio',
};

const DATA_FILE = '/opt/monitor-colegio/data/whatsapp_messages.json';
const MONITOR_FILE = '/opt/monitor-colegio/data/monitor_inputs.json';

function loadJSON(file) {
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')); } catch { return file === MONITOR_FILE ? [] : {}; }
}

function saveJSON(file, data) {
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf-8');
}

// Limpiar mensajes con más de 7 días (por timestamp)
function cleanOld(arr) {
    const weekAgo = Math.floor(Date.now() / 1000) - 7 * 24 * 60 * 60;
    return arr.filter(m => (m.timestamp || 0) > weekAgo);
}

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState('/opt/monitor-colegio/baileys_auth');
    const sock = makeWASocket({ auth: state });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', (m) => {
        for (const msg of m.messages) {
            const groupId = msg.key.remoteJid;
            const label = GROUPS[groupId];
            if (!label) continue;

            const body = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
            if (!body) continue;

            const ts = msg.messageTimestamp ? Number(msg.messageTimestamp) : Math.floor(Date.now()/1000);
            const entry = {
                from: msg.pushName || 'desconocido',
                time: new Date(ts * 1000).toLocaleTimeString('es-CL', {hour:'2-digit',minute:'2-digit'}),
                date: new Date(ts * 1000).toISOString().split('T')[0],
                body: body,
                timestamp: ts,
            };

            if (label === 'monitor_colegio') {
                if (body.startsWith('\u{1F4CB}') || body.startsWith('\u{1F4EC}') || body.startsWith('\u{1F680}') || body.startsWith('\u{1F9EA}')) return;
                const monitor = loadJSON(MONITOR_FILE);
                monitor.push(entry);
                saveJSON(MONITOR_FILE, cleanOld(monitor));
                console.log(`[MONITOR] ${entry.from}: ${body.substring(0,50)}`);
            } else {
                const messages = loadJSON(DATA_FILE);
                if (!messages[label]) messages[label] = [];
                messages[label].push(entry);
                messages[label] = cleanOld(messages[label]);
                saveJSON(DATA_FILE, messages);
                console.log(`[${label}] ${entry.from}: ${body.substring(0,50)}`);
            }
        }
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'open') console.log('WhatsApp listener ONLINE');
        if (connection === 'close') {
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log('LOGGED OUT');
                process.exit(1);
            }
            console.log('Reconnecting...');
            setTimeout(start, 5000);
        }
    });
}

console.log('Starting WhatsApp listener...');
fs.mkdirSync('/opt/monitor-colegio/data', { recursive: true });
start();
