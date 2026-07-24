/**
 * WhatsApp Handler via WAHA.
 * Recibe webhooks de WAHA (mensajes entrantes) y responde via API REST.
 * También expone endpoints HTTP para que la Lambda gestione sesiones.
 * 
 * WAHA corre en localhost:3000 (Docker).
 * Este handler corre en localhost:8080.
 * 
 * Endpoints:
 *   POST /webhook           — Recibe webhooks de WAHA
 *   POST /api/session/start — Crear/iniciar sesión WAHA para un usuario
 *   GET  /api/session/qr    — Obtener QR de una sesión
 *   GET  /api/session/status— Estado de una sesión
 *   POST /api/session/stop  — Detener sesión
 *   GET  /api/groups        — Listar grupos de una sesión
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
function wahaRequest(method, endpoint, body = null) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'localhost', port: 3000,
            path: endpoint, method: method,
            headers: { 'Content-Type': 'application/json', 'X-Api-Key': WAHA_API_KEY },
        };
        const req = http.request(options, (res) => {
            let buf = '';
            res.on('data', c => buf += c);
            res.on('end', () => {
                try { resolve({ status: res.statusCode, data: JSON.parse(buf) }); }
                catch { resolve({ status: res.statusCode, data: buf }); }
            });
        });
        req.on('error', reject);
        if (body) req.write(JSON.stringify(body));
        req.end();
    });
}

async function sendMessage(chatId, text, session) {
    return wahaRequest('POST', '/api/sendText', { session, chatId, text });
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

// Determinar sesión WAHA para un usuario
function getSessionForUser(userCfg) {
    // Cada usuario tiene su propia sesión WAHA
    // Prioridad: waha_session config > user_id > 'default'
    if (userCfg.whatsapp?.waha_session) return userCfg.whatsapp.waha_session;
    if (userCfg.id) return userCfg.id;
    return 'default';
}

// Obtener todas las sesiones activas de WAHA
async function getActiveSessions() {
    try {
        const result = await wahaRequest('GET', '/api/sessions');
        if (result.status === 200 && Array.isArray(result.data)) {
            return result.data.filter(s => s.status === 'WORKING').map(s => s.name);
        }
    } catch {}
    return [];
}

// --- Bot respond (Gemini/Haiku) con contexto COMPLETO ---
async function botRespond(chatId, question, userCfg) {
    if (!GEMINI_API_KEY && !ANTHROPIC_API_KEY) return;
    if (!question.includes('?')) return;
    if (question.startsWith('🤖') || question.startsWith('📋') || question.startsWith('📬')) return;

    const session = getSessionForUser(userCfg);

    // Intentar RAG primero (chunks relevantes)
    let contextParts = [];
    let ragUsed = false;
    try {
        const ragResp = await new Promise((resolve) => {
            const ragBody = JSON.stringify({ user_id: userCfg.id, question, n_results: 8 });
            const req = http.request({
                hostname: 'localhost', port: 8086,
                path: '/query', method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(ragBody) },
            }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => { try { resolve(JSON.parse(data)); } catch { resolve(null); } });
            });
            req.on('error', (e) => { console.log(`[BOT/RAG] Connection error: ${e.message}`); resolve(null); });
            req.setTimeout(5000, () => { console.log(`[BOT/RAG] Timeout`); req.destroy(); resolve(null); });
            req.write(ragBody);
            req.end();
        });
        if (ragResp && ragResp.ok && ragResp.chunks && ragResp.chunks.length > 0) {
            contextParts = ragResp.chunks;
            ragUsed = true;
            console.log(`[BOT/RAG] ${userCfg.id}: ${ragResp.chunks.length} chunks found`);
        } else {
            console.log(`[BOT/RAG] No chunks: ${JSON.stringify(ragResp).substring(0, 100)}`);
        }
    } catch (e) {
        console.log(`[BOT/RAG] Exception: ${e.message}`);
    }

    // SIEMPRE agregar contexto base (horarios, extras, fecha) — RAG complementa, no reemplaza
    const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' });
    const dayIndex = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Santiago' })).getDay();
    const dayName = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'][dayIndex];

    contextParts.unshift(`Fecha: ${dayName} ${today}`);

    // Hijos
    const hijos = (userCfg.hijos || []).map(h => `${h.nombre} (${h.curso})`).join(', ');
    if (hijos) contextParts.unshift(`Hijos: ${hijos}`);

    // Extraprogramáticas activas (siempre incluir)
    const extras = (userCfg.extraprogramaticas || [])
        .filter(e => !e.fecha_inicio || e.fecha_inicio <= today)
        .map(e => `${e.nombre}: ${e.dia} ${e.horario} (${e.hijo}) → sale ${e.hora_salida_real || ''}`)
        .join('\n');
    if (extras) contextParts.push(`Extraprogramáticas activas:\n${extras}`);

    // Horarios (siempre incluir del bot_context)
    const botContextFile = path.join(DATA_DIR, `bot_context_${userCfg.id}.json`);
    const botContext = loadJSON(botContextFile, null);
    if (botContext) {
        if (botContext.horarios) {
            contextParts.push(`Horarios:\n${JSON.stringify(botContext.horarios).substring(0, 2000)}`);
        }
        if (botContext.casino_hoy) {
            contextParts.push(`Casino hoy: ${botContext.casino_hoy}`);
        }

    // Instrucciones de los padres (MÁXIMA PRIORIDAD)
    const instruccionesFile = path.join(DATA_DIR, `monitor_inputs_${userCfg.id}.json`);
    const instrucciones = loadJSON(instruccionesFile, []);
    if (instrucciones.length > 0) {
        const instrText = instrucciones.slice(-5).map(i => `${i.date || ''}: ${i.body}`).join('\n');
        contextParts.unshift(`⚠️ INSTRUCCIONES DE LOS PADRES (prioridad máxima):\n${instrText}`);
    }
        // Si RAG no encontró nada, agregar calendario también
        if (!ragUsed) {
            if (botContext.calendario_persistente) {
                const upcoming = botContext.calendario_persistente
                    .filter(e => e.fecha >= today)
                    .slice(0, 15)
                    .map(e => `${e.fecha} ${e.hora || ''}: ${e.titulo} (${e.hijo || 'todos'})`)
                    .join('\n');
                if (upcoming) contextParts.push(`Calendario próximo:\n${upcoming}`);
            }
            if (botContext.comunicaciones) {
                contextParts.push(`Comunicaciones:\n${JSON.stringify(botContext.comunicaciones).substring(0, 1500)}`);
            }
            if (botContext.pagos) {
                contextParts.push(`Pagos: ${JSON.stringify(botContext.pagos).substring(0, 500)}`);
            }
            for (const hijo of (userCfg.hijos || [])) {
                const nombre = hijo.nombre.toLowerCase();
                const notas = botContext[`calificaciones_${nombre}`];
                if (notas) contextParts.push(`Notas ${hijo.nombre}: ${JSON.stringify(notas).substring(0, 800)}`);
            }
        }
    }

    const context = contextParts.join('\n\n');
    const truncatedContext = context.substring(0, 8000);

    // Historial de conversación (últimas 5 preguntas/respuestas)
    if (!global._chatHistory) global._chatHistory = {};
    const history = global._chatHistory[userCfg.id] || [];
    let historyText = '';
    if (history.length > 0) {
        historyText = '\n\nConversación reciente:\n' + history.map(h => `P: ${h.q}\nR: ${h.a}`).join('\n');
    }

    const systemPrompt = `Eres un asistente de WhatsApp que responde preguntas de un apoderado sobre el colegio de sus hijos.
Responde breve (1-4 líneas máximo), amigable, en español chileno.
Si no tienes la info exacta, di "No tengo esa info, confirma con el colegio 📞".
NUNCA inventes información que no esté en el contexto.
Usa los nombres EXACTAMENTE como aparecen en el contexto (no agregar tildes ni modificar).

Contexto:
${truncatedContext}${historyText}`;

    // Llamar LLM
    const useGemini = AI_ENGINE === 'gemini' && GEMINI_API_KEY;

    try {
        const answer = await callLLM(systemPrompt, question, useGemini);
        if (answer) {
            await sendMessage(chatId, `🤖 ${answer}`, session);
            console.log(`[BOT] ${userCfg.id}: ${answer.substring(0, 60)}`);
            // Guardar en historial (máximo 5)
            history.push({ q: question.substring(0, 100), a: answer.substring(0, 150) });
            if (history.length > 5) history.shift();
            global._chatHistory[userCfg.id] = history;
        }
    } catch (e) {
        console.log(`[BOT] Error: ${e.message}`);
    }
}

function callLLM(systemPrompt, question, useGemini) {
    return new Promise((resolve, reject) => {
        if (useGemini) {
            const body = JSON.stringify({
                contents: [{ parts: [{ text: `${systemPrompt}\n\nPregunta: ${question}` }] }],
                generationConfig: { maxOutputTokens: 250, temperature: 0.3 }
            });
            const req = https.request({
                hostname: 'generativelanguage.googleapis.com',
                path: `/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
                method: 'POST', headers: { 'Content-Type': 'application/json' },
            }, (res) => {
                let data = '';
                res.on('data', c => data += c);
                res.on('end', () => {
                    try {
                        const json = JSON.parse(data);
                        const answer = json.candidates?.[0]?.content?.parts?.[0]?.text;
                        if (answer) { resolve(answer); return; }
                    } catch {}
                    // Fallback to Haiku
                    if (ANTHROPIC_API_KEY) {
                        callHaiku(systemPrompt, question).then(resolve).catch(reject);
                    } else { resolve(null); }
                });
            });
            req.on('error', () => {
                if (ANTHROPIC_API_KEY) callHaiku(systemPrompt, question).then(resolve).catch(reject);
                else resolve(null);
            });
            req.write(body);
            req.end();
        } else if (ANTHROPIC_API_KEY) {
            callHaiku(systemPrompt, question).then(resolve).catch(reject);
        } else {
            resolve(null);
        }
    });
}

function callHaiku(systemPrompt, question) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify({
            model: 'claude-haiku-4-5-20251001', max_tokens: 250,
            system: systemPrompt, messages: [{ role: 'user', content: question }],
        });
        const req = https.request({
            hostname: 'api.anthropic.com', path: '/v1/messages', method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-api-key': ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
        }, (res) => {
            let data = '';
            res.on('data', c => data += c);
            res.on('end', () => {
                try {
                    const json = JSON.parse(data);
                    resolve(json.content?.[0]?.text || null);
                } catch { resolve(null); }
            });
        });
        req.on('error', () => resolve(null));
        req.write(body);
        req.end();
    });
}

// --- Webhook handler ---
function handleWebhook(payload) {
    const event = payload.event;

    // Session status changes — save to file for S3 sync
    if (event === 'session.status') {
        const session = payload.session || 'unknown';
        const status = payload.payload?.status || '';
        console.log(`[SESSION] ${session}: ${status}`);
        // Write status file (Lambda reads this via S3)
        const statusFile = path.join(DATA_DIR, 'sessions', `${session}.json`);
        fs.mkdirSync(path.join(DATA_DIR, 'sessions'), { recursive: true });
        saveJSON(statusFile, { session, status, updated: new Date().toISOString() });
        // Sync to S3 in background
        const { exec } = require('child_process');
        exec(`/home/ubuntu/.local/bin/aws s3 cp ${statusFile} s3://monitor-colegio-config-669294688330/whatsapp/sessions/${session}/status.json --region us-east-2`, (err) => {
            if (err) console.log(`[SESSION] S3 sync error: ${err.message}`);
            else console.log(`[SESSION] ${session} status synced to S3: ${status}`);
        });

        // If SCAN_QR_CODE, also fetch and save QR image to S3
        if (status === 'SCAN_QR_CODE') {
            setTimeout(async () => {
                try {
                    // WAHA NOWEB returns QR as PNG binary
                    const qrResult = await new Promise((resolve, reject) => {
                        const req = http.request({
                            hostname: 'localhost', port: 3000,
                            path: `/api/${session}/auth/qr`,
                            method: 'GET',
                            headers: { 'X-Api-Key': WAHA_API_KEY },
                        }, (res) => {
                            const chunks = [];
                            res.on('data', c => chunks.push(c));
                            res.on('end', () => {
                                const buf = Buffer.concat(chunks);
                                const contentType = res.headers['content-type'] || '';
                                resolve({ status: res.statusCode, contentType, buffer: buf });
                            });
                        });
                        req.on('error', reject);
                        req.end();
                    });

                    if (qrResult.status === 200 && qrResult.buffer.length > 100) {
                        let qrValue = '';
                        if (qrResult.contentType.includes('image') || qrResult.buffer[0] === 0x89) {
                            // PNG binary → base64 data URL
                            qrValue = `data:image/png;base64,${qrResult.buffer.toString('base64')}`;
                        } else {
                            // JSON or text
                            const text = qrResult.buffer.toString('utf-8');
                            try {
                                const json = JSON.parse(text);
                                qrValue = json.value || json.qr || text;
                            } catch {
                                qrValue = text;
                            }
                        }

                        // Save QR to file and S3
                        const qrFile = path.join(DATA_DIR, 'sessions', `${session}_qr.json`);
                        saveJSON(qrFile, { qr: qrValue, updated: new Date().toISOString() });
                        const { exec } = require('child_process');
                        exec(`/home/ubuntu/.local/bin/aws s3 cp ${qrFile} s3://monitor-colegio-config-669294688330/whatsapp/sessions/${session}/qr.json --region us-east-2`, (err2) => {
                            if (!err2) console.log(`[SESSION] ${session} QR saved to S3 (${qrValue.length} chars)`);
                        });
                    }
                } catch (e) {
                    console.log(`[SESSION] QR fetch error: ${e.message}`);
                }
            }, 3000); // Wait 3s for QR to be fully generated
        }
        return;
    }

    if (event === 'message' || event === 'message.any') {
        const msg = payload.payload;
        if (!msg) return;

        const chatId = msg.from;
        const body = msg.body || '';
        const isGroup = chatId.includes('@g.us');
        const sessionName = payload.session || 'default';

        // Ignorar mensajes propios EXCEPTO en grupo monitor (el apoderado pregunta desde su mismo teléfono)
        if (msg.fromMe) {
            const users = loadUsers();
            let isMonitorGroup = false;
            for (const u of users) {
                if (u.whatsapp?.grupo_monitor === chatId) {
                    isMonitorGroup = true;
                    break;
                }
            }
            if (!isMonitorGroup) return;
        }

        // Encontrar usuario por grupo o por sesión
        const users = loadUsers();
        let userCfg = null;

        for (const u of users) {
            const groups = u.whatsapp_groups || [];
            const grupoMonitor = u.whatsapp?.grupo_monitor;
            const userSession = getSessionForUser(u);
            // Match by grupo monitor, whatsapp_groups, or session name
            if (grupoMonitor === chatId || groups.some(g => g.id === chatId) || userSession === sessionName) {
                userCfg = u;
                break;
            }
        }

        if (!userCfg) return;

        // Guardar mensaje en whatsapp_messages.json
        if (isGroup && body) {
            const groupCfg = (userCfg.whatsapp_groups || []).find(g => g.id === chatId);
            const label = groupCfg
                ? `${groupCfg.hijo?.split(' ')[0] || 'grupo'}_${groupCfg.name?.substring(0,15) || chatId}`.replace(/[^a-zA-Z0-9_]/g, '')
                : chatId;

            const messages = loadJSON(WA_MESSAGES_FILE, {});
            if (!messages[label]) messages[label] = [];
            messages[label].push({
                from: msg.notifyName || msg._data?.notifyName || 'unknown',
                body: body.substring(0, 500),
                date: new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' }),
                time: new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Santiago' }),
                timestamp: Math.floor(Date.now() / 1000),
            });
            // Keep last 50 per group
            if (messages[label].length > 50) messages[label] = messages[label].slice(-50);
            saveJSON(WA_MESSAGES_FILE, messages);
            console.log(`[${userCfg.id}][${label}] ${msg.notifyName}: ${body.substring(0, 50)}`);
        }

        // Guardar instrucciones en grupo monitor (mensajes que no son del bot, >10 chars)
        const grupoMonitor = userCfg.whatsapp?.grupo_monitor;
        if (chatId === grupoMonitor && body && !body.startsWith('🤖') && !body.startsWith('📋') && !body.startsWith('📬') && !body.startsWith('📝')) {
            // Solo guardar instrucciones con contenido real (>10 chars, no es pregunta)
            if (body.length > 10 && !body.includes('?')) {
                const session = getSessionForUser(userCfg);
                const monitorFile = path.join(DATA_DIR, `monitor_inputs_${userCfg.id}.json`);
                const inputs = loadJSON(monitorFile, []);
                inputs.push({
                    from: msg.notifyName || 'unknown',
                    body: body.substring(0, 500),
                    date: new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' }),
                    time: new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Santiago' }),
                });
                // Keep last 20 instructions
                if (inputs.length > 20) inputs.splice(0, inputs.length - 20);
                saveJSON(monitorFile, inputs);
                // Confirmar con "Anotado"
                sendMessage(chatId, '📝 Anotado', session);
                console.log(`[${userCfg.id}][INSTRUCCION] ${body.substring(0, 50)}`);
            }
        }

        // Bot respond (solo en grupo monitor y si tiene ?)
        if (chatId === grupoMonitor && body.includes('?')) {
            botRespond(chatId, body, userCfg);
        }
    }
}

// --- Outbox watcher (enviar mensajes pendientes via WAHA) ---
function processOutbox() {
    const outboxDir = path.join(DATA_DIR, 'outbox');
    if (!fs.existsSync(outboxDir)) return;

    let files;
    try {
        files = fs.readdirSync(outboxDir).filter(f => f.endsWith('.json'));
    } catch (e) {
        console.log(`[OUTBOX] Cannot read dir: ${e.message}`);
        return;
    }

    for (const file of files) {
        const filePath = path.join(outboxDir, file);
        let data;
        try {
            data = loadJSON(filePath, null);
        } catch { continue; }
        if (!data) continue;

        if (data.status === 'pending' || (data.status === 'error' && (data._retries || 0) < 3)) {
            if (data.status === 'error') {
                data._retries = (data._retries || 0) + 1;
                console.log(`[OUTBOX] Retry #${data._retries} for ${file}`);
            }

            // Mark as processing immediately to avoid re-entry
            try {
                data.status = 'processing';
                saveJSON(filePath, data);
            } catch (e) {
                console.log(`[OUTBOX] Cannot write ${file}: ${e.message}`);
                continue;
            }

            // Determine which session to use
            const userId = data.user_id;
            const users = loadUsers();
            const userCfg = users.find(u => u.id === userId);
            const session = userCfg ? getSessionForUser(userCfg) : 'default';

            (async () => {
                try {
                    for (const target of (data.targets || [])) {
                        await sendMessage(target, data.message, session);
                        console.log(`[OUTBOX] Sent to ${target} via session ${session}`);
                    }
                    data.status = 'sent';
                    data.sent_at = new Date().toISOString();
                    try { saveJSON(filePath, data); } catch {}
                    // Cleanup after 5 min
                    setTimeout(() => { try { fs.unlinkSync(filePath); } catch {} }, 300000);
                } catch (e) {
                    data.status = 'error';
                    data.error = e.message;
                    try { saveJSON(filePath, data); } catch {}
                    console.log(`[OUTBOX] Error: ${e.message}`);
                }
            })();
        }
    }
}

// --- Session management API (called by Lambda via SSM or direct HTTP) ---
async function handleSessionStart(body) {
    const { session, phone } = body;
    if (!session) return { ok: false, error: 'session requerido' };

    // Verificar si sesión ya existe y está activa
    try {
        const check = await wahaRequest('GET', `/api/sessions/${session}`);
        if (check.status === 200 && check.data?.status === 'WORKING') {
            return { ok: true, status: 'already_connected', session };
        }
        // Si existe pero no está WORKING, detenerla primero
        if (check.status === 200) {
            await wahaRequest('POST', '/api/sessions/stop', { name: session });
            await new Promise(r => setTimeout(r, 1000));
        }
    } catch {}

    // Crear sesión nueva
    try {
        const startBody = {
            name: session,
            config: {
                webhooks: [{ url: 'http://localhost:8080/webhook', events: ['message', 'message.any', 'session.status'] }],
            },
        };
        const result = await wahaRequest('POST', '/api/sessions/start', startBody);
        console.log(`[SESSION] Started ${session}: ${JSON.stringify(result.data).substring(0, 100)}`);
        // Sync status to S3
        const statusFile = path.join(DATA_DIR, 'sessions', `${session}.json`);
        fs.mkdirSync(path.join(DATA_DIR, 'sessions'), { recursive: true });
        saveJSON(statusFile, { session, status: 'STARTING', updated: new Date().toISOString() });
        const { exec } = require('child_process');
        exec(`/home/ubuntu/.local/bin/aws s3 cp ${statusFile} s3://monitor-colegio-config-669294688330/whatsapp/sessions/${session}/status.json --region us-east-2`);
        return { ok: true, status: 'starting', session };
    } catch (e) {
        return { ok: false, error: e.message };
    }
}

async function handleSessionQR(query) {
    const session = query.session || 'default';
    try {
        const result = await wahaRequest('GET', `/api/${session}/auth/qr`);
        if (result.status === 200 && result.data) {
            return { ok: true, qr: result.data };
        }
        return { ok: false, error: 'No QR available' };
    } catch (e) {
        return { ok: false, error: e.message };
    }
}

async function handleSessionStatus(query) {
    const session = query.session || 'default';
    try {
        const result = await wahaRequest('GET', `/api/sessions/${session}`);
        if (result.status === 200) {
            const status = result.data?.status || 'UNKNOWN';
            return { ok: true, status: status, name: session };
        }
        return { ok: false, status: 'NOT_FOUND' };
    } catch (e) {
        return { ok: false, error: e.message };
    }
}

async function handleSessionStop(body) {
    const { session } = body;
    if (!session) return { ok: false, error: 'session requerido' };
    try {
        await wahaRequest('POST', '/api/sessions/stop', { name: session });
        return { ok: true };
    } catch (e) {
        return { ok: false, error: e.message };
    }
}

async function handleListGroups(query) {
    const session = query.session || 'default';
    try {
        const result = await wahaRequest('GET', `/api/${session}/chats`);
        if (result.status === 200 && Array.isArray(result.data)) {
            const groups = result.data
                .filter(c => c.id?.includes('@g.us'))
                .map(c => ({ id: c.id, name: c.name || c.id, participants: c.participants?.length || 0 }));
            return { ok: true, groups };
        }
        return { ok: false, groups: [] };
    } catch (e) {
        return { ok: false, error: e.message, groups: [] };
    }
}

// --- Create monitor group + welcome message ---
async function handleCreateGroup(body) {
    const { session, name, participants, user_id, photo_url } = body;
    if (!session || !name || !participants || !participants.length) {
        return { ok: false, error: 'session, name, participants requeridos' };
    }

    // 1. Crear grupo
    console.log(`[GROUP] Creating "${name}" with ${participants.length} participants`);
    let groupId = '';
    try {
        const result = await wahaRequest('POST', `/api/${session}/groups`, {
            name: name,
            participants: participants.map(p => ({ id: p })),
        });
        if (result.status === 201 || result.status === 200) {
            groupId = result.data?.id || result.data?.gid || '';
            console.log(`[GROUP] Created: ${groupId}`);
        } else {
            console.log(`[GROUP] Create failed: ${JSON.stringify(result.data).substring(0, 200)}`);
            return { ok: false, error: 'Group creation failed', details: result.data };
        }
    } catch (e) {
        return { ok: false, error: e.message };
    }

    if (!groupId) return { ok: false, error: 'No group ID returned' };

    // 2. Cambiar descripción
    try {
        await wahaRequest('PUT', `/api/${session}/groups/${groupId}/description`, {
            description: '📚 Monitor Colegio — Resúmenes diarios + asistente 24/7\n🤖 Pregúntame con "?"\n📝 Escribe instrucciones y las anoto'
        });
    } catch {}

    // 3. Cambiar foto (generada dinámicamente con nombre colegio + apellido)
    try {
        const { execSync } = require('child_process');
        // Generar foto con Python — leer colegio del config del usuario
        const apellido = name.replace('Monitor Colegio ', '');
        let colegio = 'Monitor Colegio';
        if (user_id) {
            const userFile = path.join(USERS_DIR, `${user_id}.json`);
            if (fs.existsSync(userFile)) {
                const cfg = loadJSON(userFile, {});
                colegio = cfg.colegio?.nombre || cfg.colegios?.[0]?.nombre || 'Monitor Colegio';
            }
        }
        const photoPath = `/tmp/group_photo_${user_id || 'default'}.png`;
        // Write params to temp JSON to avoid shell encoding issues
        const paramsFile = `/tmp/group_photo_params_${user_id || 'default'}.json`;
        fs.writeFileSync(paramsFile, JSON.stringify({ colegio, apellido, output: photoPath }));
        execSync(
            `cd /opt/monitor-colegio && python3 -c "
import json
params = json.load(open('${paramsFile}'))
from src.utils.group_photo import generate_group_photo
generate_group_photo(params['colegio'], params['apellido'], params['output'])
"`,
            { timeout: 10000 }
        );
        if (require('fs').existsSync(photoPath)) {
            // Upload photo to group via WAHA
            const photoBase64 = require('fs').readFileSync(photoPath).toString('base64');
            await wahaRequest('PUT', `/api/${session}/groups/${groupId}/picture`, {
                file: { mimetype: 'image/png', data: photoBase64 }
            });
            console.log(`[GROUP] Photo set for ${groupId} (${colegio} - ${apellido})`);
        }
    } catch (e) {
        console.log(`[GROUP] Photo error: ${e.message}`);
    }

    // 4. Enviar mensaje de bienvenida
    const welcomeMsg = `🎉 *¡Bienvenido a Monitor Colegio!*

📋 Resúmenes diarios: 7:00 AM + 20:00 PM
🤖 Pregúntame lo que quieras con "?"
📝 Escribe instrucciones y las anoto
📌 Fija este grupo arriba para no perderte nada

_Tu primer resumen llegará en la próxima corrida (AM o PM)._`;

    try {
        await sendMessage(groupId, welcomeMsg, session);
        console.log(`[GROUP] Welcome sent to ${groupId}`);
    } catch {}

    // 5. Guardar grupo_monitor en config del usuario
    if (user_id) {
        const userFile = path.join(USERS_DIR, `${user_id}.json`);
        if (fs.existsSync(userFile)) {
            try {
                const cfg = loadJSON(userFile, {});
                if (!cfg.whatsapp) cfg.whatsapp = {};
                cfg.whatsapp.grupo_monitor = groupId;
                saveJSON(userFile, cfg);
                console.log(`[GROUP] Updated config: grupo_monitor = ${groupId}`);
                // Sync to S3
                const { exec } = require('child_process');
                exec(`/home/ubuntu/.local/bin/aws s3 cp ${userFile} s3://monitor-colegio-config-669294688330/config/users/${user_id}.json --region us-east-2`);
            } catch {}
        }
    }

    return { ok: true, groupId, name };
}

// --- HTTP Server ---
const server = http.createServer((req, res) => {
    // Parse URL
    const url = new URL(req.url, `http://localhost:8080`);
    const pathname = url.pathname;
    const query = Object.fromEntries(url.searchParams);

    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', async () => {
            let parsed = {};
            try { parsed = JSON.parse(body); } catch {}

            if (pathname === '/webhook') {
                try {
                    console.log(`[WEBHOOK] Event: ${parsed.event}, from: ${parsed.payload?.from || 'unknown'}, body: ${(parsed.payload?.body || '').substring(0, 50)}`);
                    handleWebhook(parsed);
                } catch (e) {
                    console.log(`[WEBHOOK] Error: ${e.message}`);
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ ok: true }));
            }
            else if (pathname === '/api/session/start') {
                const result = await handleSessionStart(parsed);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            }
            else if (pathname === '/api/session/stop') {
                const result = await handleSessionStop(parsed);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            }
            else if (pathname === '/api/group/create') {
                const result = await handleCreateGroup(parsed);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            }
            else {
                res.writeHead(404);
                res.end('not found');
            }
        });
    }
    else if (req.method === 'GET') {
        (async () => {
            if (pathname === '/api/session/qr') {
                const result = await handleSessionQR(query);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            }
            else if (pathname === '/api/session/status') {
                const result = await handleSessionStatus(query);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            }
            else if (pathname === '/api/sessions') {
                const sessions = await getActiveSessions();
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ ok: true, sessions }));
            }
            else if (pathname === '/api/groups') {
                const result = await handleListGroups(query);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            }
            else if (pathname === '/health') {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ ok: true, uptime: process.uptime(), ai: AI_ENGINE }));
            }
            else {
                res.writeHead(404);
                res.end('not found');
            }
        })();
    }
    else {
        res.writeHead(405);
        res.end('method not allowed');
    }
});

// --- Start ---
fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(path.join(DATA_DIR, 'outbox'), { recursive: true });

server.listen(8080, () => {
    console.log('WA Handler listening on :8080');
    console.log(`  Webhooks: POST /webhook`);
    console.log(`  Session API: /api/session/{start,stop,qr,status}`);
    console.log(`  Groups: GET /api/groups?session=xxx`);
    console.log(`  WAHA: ${WAHA_URL}, AI: ${AI_ENGINE}`);

    // Outbox watcher every 3s
    setInterval(processOutbox, 3000);
});
