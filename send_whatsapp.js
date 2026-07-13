/**
 * Envía el resumen diario por WhatsApp usando whatsapp-web.js.
 * Lee el mensaje desde un archivo JSON generado por Python.
 * 
 * Uso:
 *   node send_whatsapp.js
 * 
 * Espera un archivo data/mensaje_enviar.json con:
 * { "mensaje": "texto del resumen" }
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

// Grupo "Monitor Colegio" donde están ambos padres
const MONITOR_GROUP_ID = '120363409985436264@g.us';

const MESSAGE_FILE = 'data/mensaje_enviar.json';

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    }
});

client.on('ready', async () => {
    console.log('WhatsApp conectado.');

    // Leer mensaje a enviar
    if (!fs.existsSync(MESSAGE_FILE)) {
        console.error(`No existe ${MESSAGE_FILE}. Genera el resumen primero.`);
        process.exit(1);
    }

    const data = JSON.parse(fs.readFileSync(MESSAGE_FILE, 'utf-8'));
    const mensaje = data.mensaje;

    if (!mensaje) {
        console.error('El mensaje está vacío.');
        process.exit(1);
    }

    console.log(`Mensaje a enviar (${mensaje.length} chars):\n${mensaje.substring(0, 100)}...\n`);

    // Enviar al grupo Monitor Colegio
    try {
        // WhatsApp usa *bold* no **bold**, convertir
        const mensajeLimpio = mensaje.replace(/\*\*/g, '*');
        await client.sendMessage(MONITOR_GROUP_ID, mensajeLimpio);
        console.log('✅ Enviado al grupo Monitor Colegio');
    } catch (err) {
        console.error(`❌ Error: ${err.message}`);
    }

    console.log('\nListo. Cerrando...');
    process.exit(0);
});

client.on('qr', () => {
    console.log('Sesión expirada. Corre: node test_whatsapp.js');
    process.exit(1);
});

console.log('Conectando a WhatsApp...');
client.initialize();
