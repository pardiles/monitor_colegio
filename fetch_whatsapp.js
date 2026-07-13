/**
 * Lee los últimos mensajes de los grupos del colegio y los guarda en JSON.
 */
const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const GROUPS = {
    '120363022899821958@g.us': '5A_franco',
    '120363407876876956@g.us': '1C_blanca',
    '120363024586413625@g.us': '5to_sharks_franco',
};

// Modo: "week" para primera vez / testing, "daily" para producción
const MODE = process.argv[2] || 'week';
const SECONDS_FILTER = MODE === 'daily' ? 86400 : 604800; // 1 día o 7 días
console.log(`Modo: ${MODE} (últimos ${SECONDS_FILTER / 3600} horas)`);

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    }
});

client.on('ready', async () => {
    console.log('Conectado, leyendo mensajes...');
    const result = {};

    for (const [groupId, label] of Object.entries(GROUPS)) {
        try {
            const chat = await client.getChatById(groupId);
            const messages = await chat.fetchMessages({ limit: 100 });
            
            // Filtrar según modo
            const now = Date.now() / 1000;
            const recent = messages.filter(m => (now - m.timestamp) < SECONDS_FILTER);
            
            result[label] = recent.map(m => ({
                from: m._data.notifyName || m.from,
                time: new Date(m.timestamp * 1000).toLocaleTimeString('es-CL', {hour: '2-digit', minute: '2-digit'}),
                body: m.body || '[multimedia]',
            }));
            
            console.log(`${label}: ${result[label].length} mensajes (últimas 24h)`);
        } catch (e) {
            console.error(`Error ${label}: ${e.message}`);
            result[label] = [];
        }
    }

    // Guardar en JSON
    fs.writeFileSync('data/whatsapp_messages.json', JSON.stringify(result, null, 2), 'utf-8');
    console.log('Guardado en data/whatsapp_messages.json');
    process.exit(0);
});

client.on('qr', () => {
    console.log('Sesion expirada. Corre: node test_whatsapp.js');
    process.exit(1);
});

client.initialize();
