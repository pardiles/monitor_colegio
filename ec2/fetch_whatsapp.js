/**
 * Lee mensajes de los grupos del colegio usando Baileys.
 * Uso: node fetch_whatsapp.js [week|daily]
 */
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const fs = require('fs');

const MODE = process.argv[2] || 'week';
const SECONDS_FILTER = 604800; // Siempre última semana para no perder contexto
console.log(`Modo: siempre semana (ultimos 168 horas)`);

const GROUPS = {
    '120363022899821958@g.us': '5A_franco',
    '120363407876876956@g.us': '1C_blanca',
    '120363024586413625@g.us': '5to_sharks_franco',
};

// Grupo Monitor Colegio - mensajes manuales de los padres
const MONITOR_GROUP_ID = '120363409985436264@g.us';

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState('./baileys_auth');
    const sock = makeWASocket({ auth: state });
    sock.ev.on('creds.update', saveCreds);

    return new Promise((resolve, reject) => {
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect } = update;

            if (connection === 'open') {
                console.log('Conectado! Leyendo mensajes...');
                const result = {};

                for (const [groupId, label] of Object.entries(GROUPS)) {
                    try {
                        // Obtener mensajes recientes del grupo
                        const messages = await sock.fetchMessagesFromWA(groupId, 50);
                        const now = Date.now() / 1000;
                        const recent = messages
                            .filter(m => m.messageTimestamp && (now - m.messageTimestamp) < SECONDS_FILTER)
                            .map(m => ({
                                from: m.pushName || m.key.participant || 'desconocido',
                                time: new Date(m.messageTimestamp * 1000).toLocaleTimeString('es-CL', {hour:'2-digit',minute:'2-digit'}),
                                body: m.message?.conversation || m.message?.extendedTextMessage?.text || '[multimedia]',
                            }));
                        result[label] = recent;
                        console.log(`${label}: ${recent.length} mensajes`);
                    } catch (e) {
                        console.error(`Error ${label}: ${e.message}`);
                        result[label] = [];
                    }
                }

                fs.mkdirSync('data', { recursive: true });
                fs.writeFileSync('data/whatsapp_messages.json', JSON.stringify(result, null, 2), 'utf-8');
                console.log('Guardado en data/whatsapp_messages.json');

                // Leer grupo Monitor Colegio (mensajes manuales de los padres)
                try {
                    const monitorMessages = await sock.fetchMessagesFromWA(MONITOR_GROUP_ID, 30);
                    const now2 = Date.now() / 1000;
                    const manualInputs = monitorMessages
                        .filter(m => {
                            if (!m.messageTimestamp || (now2 - m.messageTimestamp) > SECONDS_FILTER) return false;
                            const body = m.message?.conversation || m.message?.extendedTextMessage?.text || '';
                            // Filtrar mensajes del bot (resúmenes que empiezan con emoji de resumen)
                            if (body.startsWith('📋') || body.startsWith('📬') || body.startsWith('🚀') || body.startsWith('🧪')) return false;
                            // Solo mensajes con texto
                            if (!body || body === '[multimedia]') return false;
                            return true;
                        })
                        .map(m => ({
                            from: m.pushName || 'desconocido',
                            time: new Date(m.messageTimestamp * 1000).toLocaleTimeString('es-CL', {hour:'2-digit', minute:'2-digit'}),
                            date: new Date(m.messageTimestamp * 1000).toLocaleDateString('es-CL'),
                            body: m.message?.conversation || m.message?.extendedTextMessage?.text || '',
                        }));
                    
                    fs.writeFileSync('data/monitor_inputs.json', JSON.stringify(manualInputs, null, 2), 'utf-8');
                    console.log(`monitor_colegio: ${manualInputs.length} mensajes manuales`);
                } catch (e) {
                    console.error(`Error monitor group: ${e.message}`);
                    fs.writeFileSync('data/monitor_inputs.json', '[]', 'utf-8');
                }

                resolve();
                process.exit(0);
            }

            if (connection === 'close') {
                const code = lastDisconnect?.error?.output?.statusCode;
                if (code === DisconnectReason.loggedOut) {
                    console.error('Sesion cerrada. Re-escanear QR.');
                    reject(new Error('logged out'));
                    process.exit(1);
                }
                console.log('Reconectando...');
                setTimeout(() => start().then(resolve).catch(reject), 3000);
            }
        });
    });
}

start().catch(e => { console.error(e); process.exit(1); });
setTimeout(() => { console.log('TIMEOUT'); process.exit(1); }, 120000);
