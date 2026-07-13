/**
 * Envía el resumen al grupo Monitor Colegio usando Baileys.
 * Lee el mensaje desde data/mensaje_enviar.json
 */
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const fs = require('fs');

const MONITOR_GROUP_ID = '120363409985436264@g.us';
const MESSAGE_FILE = 'data/mensaje_enviar.json';

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState('./baileys_auth');
    const sock = makeWASocket({ auth: state });
    sock.ev.on('creds.update', saveCreds);

    return new Promise((resolve, reject) => {
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect } = update;

            if (connection === 'open') {
                console.log('Conectado!');

                if (!fs.existsSync(MESSAGE_FILE)) {
                    console.error(`No existe ${MESSAGE_FILE}`);
                    process.exit(1);
                }

                const data = JSON.parse(fs.readFileSync(MESSAGE_FILE, 'utf-8'));
                let msg = data.mensaje;
                // WhatsApp usa *bold* no **bold**
                msg = msg.replace(/\*\*/g, '*');

                console.log(`Enviando (${msg.length} chars)...`);
                await sock.sendMessage(MONITOR_GROUP_ID, { text: msg });
                console.log('Enviado al grupo Monitor Colegio!');
                resolve();
                process.exit(0);
            }

            if (connection === 'close') {
                const code = lastDisconnect?.error?.output?.statusCode;
                if (code === DisconnectReason.loggedOut) {
                    console.error('Sesion cerrada.');
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
setTimeout(() => { console.log('TIMEOUT'); process.exit(1); }, 60000);
