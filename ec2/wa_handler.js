/**
 * WhatsApp Handler via WAHA.
 * Recibe webhooks de WAHA (mensajes entrantes) y responde via API REST.
 * Reemplaza wa_listener.js + Baileys.
 * 
 * WAHA corre en localhost:3000 (Docker).
 * Este handler corre en localhost:8080 (recibe webhooks).
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const BASE_DIR = '/opt/monitor-colegio';
const DATA_DIR = path.join(BASE_DIR, 'data');
const USERS_DIR = path.join(BASE_DIR, 'config', 'users');
const USERS_FILE = path.join(BASE_DIR, 'config', 'users.json');
const WA_MESSAGES_FILE = path.join(DATA_DIR, 'whatsapp_messages.json');
const ATTACHMENTS_DIR = path.join(DATA_DIR, 'attachments');

const WAHA_URL = 'http://localhost:3000';
const WAHA_API_KEY = 'monitor2026';
const WAHA_SESSION = 'pablo'; // TODO: multi-session por usuario

// Cargar env vars
let GEMINI_API_KEY = '';
let ANTHROPIC_API_KEY = '';
let AI_ENGINE = 'gemini';
try {
    const envFile = fs.readFileSync(path.join(BASE_DIR, '.env'), 'utf-8');
    for (const line of envFile.split('\n')) {
        if (line.startsWith('GEMINI_API_KEY=')) GEMINI_API_KEY = line.split('=')[1].trim().replace(/['"]/g, '');
        if (line.startsWith('ANTHROPIC_API_KEY=')) ANTHROPIC_API_KEY = line.split('=')[1].trim().replace(/['"]/g, '');
        if (line.startsWith('AI_ENGINE=')) AI_ENGINE = line.split('=')[1].trim().replace(/['"]/g, '');
    }
} catch {}

function loadJSON(file, fallback) {
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')); }
    catch { return fallback !== undefined ? fallback : {}; }
}
function saveJSON(file, data) {
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf-8');
}

// --- WAHA API helpers ---
function wahaPost(endpoint, body) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(body);
        const req = http.request({
            hostname: 'localhost', port: 3000,
            path: endpoint, method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Api-Key': WAHA_API_KEY },
        }, (res) => {
            let buf = '';
            res.on('data', c => buf += c);
            res.on('end', () => { try { resolve(JSON.parse(buf)); } catch { resolve(buf); } });
        });
        req.on('error', reject);
        req.write(data);
        req.end();
    });
}

async function sendMessage(chatId, text, session = WAHA_SESSION) {
    return wahaPost(`/api/sendText`, { session, chatId, text });
}

// --- Load users ---
function loadUsers() {
    let users = [];
    if (fs.existsSync(USERS_DIR)) {
        const files = fs.readdirSync(USERS_DIR).filter(f => f.endsWith('.json') && f !== 'admin.json');
        for (const file of files) {
            try { const u = JSON.parse(fs.readFileSync(path.join(USERS_DIR, file), 'utf-8')); if (u.id) users.push(u); } catch {}
        }
    }
    // Merge legacy
    const legacy = loadJSON(USERS_FILE, []);
    for (const lu of legacy) {
        const existing = users.find(u => u.id === lu.id);
        if (existing) { for (const [k, v] of Object.entries(lu)) { if (v && !existing[k]) existing[k] = v; } }
        else users.push(lu);
    }
    return users;
}

// --- Bot respond (Gemini/Haiku) ---
// TODO: copiar la lógica de botRespond del wa_listener original
// Por ahora placeholder
async function botRespond(chatId, question, userCfg) {
    if (!GEMINI_API_KEY && !ANTHROPIC_API_KEY) return;
    if (!question.includes('?')) return;
    if (question.startsWith('🤖') || question.startsWith('📋') || question.startsWith('📬')) return;

    // Construir contexto (simplificado — TODO: copiar contexto completo)
    const hijos = (userCfg.hijos || []).map(h => `${h.nombre} (${h.curso})`).join(', ');
    const extras = (userCfg.extraprogramaticas || []).map(e => `${e.nombre}: ${e.dia} ${e.horario} (${e.hijo})`).join('\n');
    const botContext = loadJSON(path.join(DATA_DIR, `bot_context_${userCfg.id}.json`), {});
    
    const context = `Hijos: ${hijos}\nExtraprogramáticas: ${extras || 'No configuradas'}\nFecha: ${new Date().toLocaleDateString('sv-SE', {timeZone:'America/Santiago'})}`;
    const systemPrompt = `Eres un bot de WhatsApp que responde preguntas de un apoderado sobre el colegio de sus hijos. Responde breve (1-3 líneas máximo), amigable. Si no tienes la info, di "No tengo esa info, confirma con el colegio 📞". Contexto:\n${context}`;

    // Gemini (o Haiku si Gemini no tiene key o falla)
    const useGemini = AI_ENGINE === 'gemini' && GEMINI_API_KEY;
    
    if (useGemini) {
        const body = JSON.stringify({
            contents: [{ parts: [{ text: `${systemPrompt}\n\nPregunta: ${question}` }] }],
            generationConfig: { maxOutputTokens: 200, temperature: 0.3 }
        });
        return new Promise((resolve) => {
            const req = https.request({
                hostname: 'generativelanguage.googleapis.com',
                path: `/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
                method: 'POST', headers: { 'Content-Type': 'application/json' },
            }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', async () => {
                    try {
                        const json = JSON.parse(data);
                        const answer = json.candidates?.[0]?.content?.parts?.[0]?.text;
                        if (answer) {
                            await sendMessage(chatId, `🤖 ${answer}`);
                            console.log(`[BOT] ${userCfg.id}: ${answer.substring(0, 50)}`);
                        } else {
                            console.log(`[BOT] No answer from Gemini: ${data.substring(0, 200)}`);
                            // Fallback a Haiku si Gemini falla
                            if (ANTHROPIC_API_KEY) {
                                const hBody = JSON.stringify({
                                    model: 'claude-haiku-4-5-20251001', max_tokens: 200,
                                    system: systemPrompt, messages: [{ role: 'user', content: question }],
                                });
                                const hReq = https.request({
                                    hostname: 'api.anthropic.com', path: '/v1/messages', method: 'POST',
                                    headers: { 'Content-Type': 'application/json', 'x-api-key': ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
                                }, (hRes) => {
                                    let hData = '';
                                    hRes.on('data', c => hData += c);
                                    hRes.on('end', async () => {
                                        try {
                                            const hJson = JSON.parse(hData);
                                            const hAnswer = hJson.content?.[0]?.text;
                                            if (hAnswer) {
                                                await sendMessage(chatId, `🤖 ${hAnswer}`);
                                                console.log(`[BOT/haiku-fallback] ${userCfg.id}: ${hAnswer.substring(0, 50)}`);
                                            }
                                        } catch (e2) { console.log(`[BOT/haiku-fallback] Error: ${e2.message}`); }
                                    });
                                });
                                hReq.on('error', () => {});
                                hReq.write(hBody);
                                hReq.end();
                            }
                        }
                    } catch (e) { console.log(`[BOT] Error: ${e.message}, data: ${data.substring(0, 100)}`); }
                    resolve();
                });
            });
            req.on('error', (e) => { console.log(`[BOT] Gemini HTTP error: ${e.message}`); resolve(); });
            req.write(body);
            req.end();
        });
    } else if (ANTHROPIC_API_KEY) {
        // Haiku fallback
        const body = JSON.stringify({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 200,
            system: systemPrompt,
            messages: [{ role: 'user', content: question }],
        });
        return new Promise((resolve) => {
            const req = https.request({
                hostname: 'api.anthropic.com',
                path: '/v1/messages',
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
            }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', async () => {
                    try {
                        const json = JSON.parse(data);
                        const answer = json.content?.[0]?.text;
                        if (answer) {
                            await sendMessage(chatId, `🤖 ${answer}`);
                            console.log(`[BOT/haiku] ${userCfg.id}: ${answer.substring(0, 50)}`);
                        } else {
                            console.log(`[BOT/haiku] No answer: ${data.substring(0, 100)}`);
                        }
                    } catch (e) { console.log(`[BOT/haiku] Error: ${e.message}`); }
                    resolve();
                });
            });
            req.on('error', (e) => { console.log(`[BOT/haiku] HTTP error: ${e.message}`); resolve(); });
            req.write(body);
            req.end();
        });
    }
}

// --- Webhook handler ---
function handleWebhook(payload) {
    const event = payload.event;
    
    if (event === 'message' || event === 'message.any') {
        const msg = payload.payload;
        if (!msg) return;
        
        const chatId = msg.from;
        const body = msg.body || '';
        const isGroup = chatId.includes('@g.us');
        
        // Encontrar usuario por grupo
        const users = loadUsers();
        let userCfg = null;
        
        for (const u of users) {
            const groups = u.whatsapp_groups || [];
            const grupoMonitor = u.whatsapp?.grupo_monitor;
            if (grupoMonitor === chatId || groups.some(g => g.id === chatId)) {
                userCfg = u;
                break;
            }
        }
        
        if (!userCfg) return;
        
        // Guardar mensaje en whatsapp_messages.json
        if (isGroup) {
            const groupCfg = (userCfg.whatsapp_groups || []).find(g => g.id === chatId);
            const label = groupCfg ? `${groupCfg.hijo?.split(' ')[0] || 'grupo'}_${groupCfg.name?.substring(0,10) || chatId}`.replace(/[^a-zA-Z0-9_]/g, '') : chatId;
            
            const messages = loadJSON(WA_MESSAGES_FILE, {});
            if (!messages[label]) messages[label] = [];
            messages[label].push({
                from: msg.notifyName || msg._data?.notifyName || 'unknown',
                body: body.substring(0, 500),
                date: new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' }),
                time: new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Santiago' }),
                timestamp: Math.floor(Date.now() / 1000),
            });
            // Keep last 50
            if (messages[label].length > 50) messages[label] = messages[label].slice(-50);
            saveJSON(WA_MESSAGES_FILE, messages);
            console.log(`[${userCfg.id}][${label}] ${msg.notifyName}: ${body.substring(0, 50)}`);
        }
        
        // Bot respond (solo en grupo monitor y si tiene ?)
        const grupoMonitor = userCfg.whatsapp?.grupo_monitor;
        console.log(`[DEBUG] chatId=${chatId}, grupoMonitor=${grupoMonitor}, has?=${body.includes('?')}, fromMe=${msg.fromMe}`);
        if (chatId === grupoMonitor && body.includes('?')) {
            botRespond(chatId, body, userCfg);
        }
    }
}

// --- Outbox watcher (enviar mensajes pendientes via WAHA) ---
function processOutbox() {
    const outboxDir = path.join(DATA_DIR, 'outbox');
    if (!fs.existsSync(outboxDir)) return;
    
    const files = fs.readdirSync(outboxDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
        const filePath = path.join(outboxDir, file);
        const data = loadJSON(filePath, null);
        if (!data) continue;
        
        if (data.status === 'pending' || (data.status === 'error' && (data._retries || 0) < 3)) {
            if (data.status === 'error') {
                data._retries = (data._retries || 0) + 1;
                console.log(`[OUTBOX] Retry #${data._retries} for ${file}`);
            }
            
            (async () => {
                try {
                    for (const target of (data.targets || [])) {
                        await sendMessage(target, data.message);
                        console.log(`[OUTBOX] Sent to ${target}`);
                    }
                    data.status = 'sent';
                    data.sent_at = new Date().toISOString();
                    saveJSON(filePath, data);
                    // Cleanup after 5 min
                    setTimeout(() => { try { fs.unlinkSync(filePath); } catch {} }, 300000);
                } catch (e) {
                    data.status = 'error';
                    data.error = e.message;
                    saveJSON(filePath, data);
                    console.log(`[OUTBOX] Error: ${e.message}`);
                }
            })();
        }
    }
}

// --- HTTP Server (webhook receiver) ---
const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url === '/webhook') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            try {
                const payload = JSON.parse(body);
                console.log(`[WEBHOOK] Event: ${payload.event}, from: ${payload.payload?.from || 'unknown'}, body: ${(payload.payload?.body || '').substring(0, 50)}`);
                handleWebhook(payload);
            } catch (e) {
                console.log(`[WEBHOOK] Parse error: ${e.message}`);
            }
            res.writeHead(200);
            res.end('ok');
        });
    } else {
        res.writeHead(404);
        res.end('not found');
    }
});

// --- Start ---
fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(path.join(DATA_DIR, 'outbox'), { recursive: true });

server.listen(8080, () => {
    console.log('WA Handler listening on :8080 (webhook receiver)');
    console.log(`WAHA: ${WAHA_URL}, AI: ${AI_ENGINE}`);
    
    // Outbox watcher every 3s
    setInterval(processOutbox, 3000);
});
