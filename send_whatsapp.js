/**
 * Envía el resumen diario por WhatsApp usando whatsapp-web.js.
 * Soporta multi-usuario: lee config de destino según user_id.
 * 
 * Uso:
 *   node send_whatsapp.js pablo    → envía al grupo Monitor Colegio de Pablo
 *   node send_whatsapp.js oscar    → envía a Oscar y Ale directamente
 *   node send_whatsapp.js          → default: pablo
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

// Configuración por usuario
const USERS = {
    pablo: {
        type: 'group',
        target: '120363409985436264@g.us',  // Grupo "Monitor Colegio"
        message_file: 'data/mensaje_enviar_pablo.json',
    },
    oscar: {
        type: 'direct',
        targets: ['56975195836@c.us', '56984222605@c.us'],  // Oscar + Ale
        message_file: 'data/mensaje_enviar_oscar.json',
    },
    kevin: {
        type: 'direct',
        targets: ['56992352602@c.us'],  // Kevin
        message_file: 'data/mensaje_enviar_kevin.json',
    },
};

const userId = process.argv[2] || 'pablo';
const userConfig = USERS[userId];

if (!userConfig) {
    console.error(`Usuario '${userId}' no configurado. Disponibles: ${Object.keys(USERS).join(', ')}`);
    process.exit(1);
}

const MESSAGE_FILE = userConfig.message_file;

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    }
});

client.on('ready', async () => {
    console.log('Conectado!');

    if (!fs.existsSync(MESSAGE_FILE)) {
        console.error(`No existe ${MESSAGE_FILE}`);
        process.exit(1);
    }

    const data = JSON.parse(fs.readFileSync(MESSAGE_FILE, 'utf-8'));
    const mensaje = data.mensaje;

    if (!mensaje) {
        console.error('Mensaje vacío.');
        process.exit(1);
    }

    // Convertir **bold** a *bold* para WhatsApp
    const mensajeLimpio = mensaje.replace(/\*\*/g, '*');
    console.log(`Enviando (${mensajeLimpio.length} chars)...`);

    try {
        if (userConfig.type === 'group') {
            await client.sendMessage(userConfig.target, mensajeLimpio);
            console.log('Enviado al grupo Monitor Colegio!');
        } else if (userConfig.type === 'direct') {
            for (const target of userConfig.targets) {
                await client.sendMessage(target, mensajeLimpio);
                console.log(`Enviado a ${target}`);
            }
        }
    } catch (err) {
        console.error(`Error: ${err.message}`);
    }

    process.exit(0);
});

client.on('qr', () => {
    console.log('Sesión expirada. Vincular de nuevo.');
    process.exit(1);
});

console.log(`[${userId}] Conectando a WhatsApp...`);
client.initialize();
