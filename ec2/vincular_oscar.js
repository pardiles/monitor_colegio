/**
 * Genera QR para vincular el WhatsApp de Oscar.
 * Guarda el QR como archivo de texto para que se pueda ver remotamente.
 */
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const fs = require('fs');
const qrcode = require('qrcode-terminal');

const AUTH_FOLDER = '/opt/monitor-colegio/baileys_auth/oscar';
const QR_FILE = '/opt/monitor-colegio/data/oscar_qr.txt';

fs.mkdirSync(AUTH_FOLDER, { recursive: true });

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_FOLDER);
    const sock = makeWASocket({ auth: state });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('QR generado! Mostrando en terminal:');
            qrcode.generate(qr, { small: true });
            // Guardar QR string para acceso remoto
            fs.writeFileSync(QR_FILE, qr, 'utf-8');
            console.log(`QR guardado en ${QR_FILE}`);
        }

        if (connection === 'open') {
            console.log('OSCAR CONECTADO!');
            // Limpiar archivo QR
            try { fs.unlinkSync(QR_FILE); } catch {}
            process.exit(0);
        }

        if (connection === 'close') {
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log('Logged out');
                process.exit(1);
            }
            setTimeout(start, 3000);
        }
    });
}

console.log('Generando QR para Oscar...');
start();
setTimeout(() => { console.log('TIMEOUT 120s'); process.exit(1); }, 120000);
