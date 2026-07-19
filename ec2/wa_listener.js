/**
 * WhatsApp Listener Multi-Sesión.
 * Lee config/users.json y abre una sesión Baileys por cada usuario
 * que tenga auth guardada (baileys_auth/{user_id}/).
 * 
 * Mensajes se guardan en data/whatsapp_messages.json (compartido)
 * y data/monitor_inputs_{user_id}.json (instrucciones por usuario).
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } = require('@whiskeysockets/baileys');
const fs = require('fs');
const path = require('path');
const https = require('https');

const BASE_DIR = '/opt/monitor-colegio';
const DATA_DIR = path.join(BASE_DIR, 'data');
const ATTACHMENTS_DIR = path.join(DATA_DIR, 'attachments');
const USERS_FILE = path.join(BASE_DIR, 'config', 'users.json');
const WA_MESSAGES_FILE = path.join(DATA_DIR, 'whatsapp_messages.json');

// Cargar API key de Anthropic desde .env
let ANTHROPIC_API_KEY = '';
try {
    const envFile = fs.readFileSync(path.join(BASE_DIR, '.env'), 'utf-8');
    for (const line of envFile.split('\n')) {
        if (line.startsWith('ANTHROPIC_API_KEY=')) {
            ANTHROPIC_API_KEY = line.split('=')[1].trim().replace(/['"]/g, '');
        }
    }
} catch {}


function loadJSON(file, fallback) {
    try { return JSON.parse(fs.readFileSync(file, 'utf-8')); }
    catch { return fallback !== undefined ? fallback : {}; }
}

function saveJSON(file, data) {
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf-8');
}

function cleanOld(arr) {
    const weekAgo = Math.floor(Date.now() / 1000) - 7 * 24 * 60 * 60;
    return arr.filter(m => (m.timestamp || 0) > weekAgo);
}

/**
 * Bot conversacional: responde preguntas del apoderado en el grupo Monitor.
 */
async function botRespond(sock, groupId, question, userCfg) {
    if (!ANTHROPIC_API_KEY) return;

    // Solo responder a preguntas (contiene ?)
    if (!question.includes('?')) return;

    // No responder a mensajes propios o del bot
    if (question.startsWith('🤖') || question.startsWith('📋') || question.startsWith('📬')) return;

    // Construir contexto del usuario
    const hijos = (userCfg.hijos || []).map(h => {
        let line = `${h.nombre} (${h.curso})`;
        if (h.profesora_jefe) line += ` — Profesora jefe: ${h.profesora_jefe}`;
        if (h.colegio) line += ` [${h.colegio}]`;
        return line;
    }).join('\n');
    const extras = (userCfg.extraprogramaticas || []).map(e => `${e.nombre}: ${e.dia} ${e.horario} (${e.hijo}) → sale ${e.hora_salida_real}`).join('\n');
    const horarios = loadJSON(path.join(DATA_DIR, 'horarios.json'), {});
    const calendario = loadJSON(path.join(DATA_DIR, `eventos_${userCfg.id}.json`), []);
    const today = new Date().toISOString().split('T')[0];
    const upcoming = calendario.filter(e => e.fecha >= today).slice(0, 20);
    const eventosStr = upcoming.map(e => `${e.fecha}${e.hora ? ' '+e.hora : ''} | ${e.descripcion} | hijo=${e.hijo}${e.lugar ? ' | lugar='+e.lugar : ''}`).join('\n');

    // Datos adicionales del colegio (profesores, compañeros, etc.)
    const colegio = userCfg.colegio || {};
    const regimen = userCfg.regimen || {};

    // Cargar contexto enriquecido (generado por el scraping diario)
    const botContext = loadJSON(path.join(DATA_DIR, `bot_context_${userCfg.id}.json`), {});
    const companeros = botContext.companeros ? `\nCompañeros por curso:\n${JSON.stringify(botContext.companeros).substring(0, 1000)}` : '';
    const profesores = botContext.profesores ? `\nProfesores:\n${JSON.stringify(botContext.profesores)}` : '';
    const calificaciones = botContext.calificaciones ? `\nCalificaciones (promedios):\n${JSON.stringify(botContext.calificaciones).substring(0, 800)}` : '';
    const conducta = botContext.conducta ? `\nÚltimas anotaciones:\n${JSON.stringify(botContext.conducta).substring(0, 600)}` : '';
    const asistencia = botContext.asistencia ? `\nAsistencia:\n${JSON.stringify(botContext.asistencia)}` : '';
    const waReciente = botContext.whatsapp_reciente ? `\nMensajes recientes en grupos WA:\n${JSON.stringify(botContext.whatsapp_reciente).substring(0, 1000)}` : '';

    const context = `Hijos:
${hijos}

Colegio: ${colegio.nombre || ''}
${colegio.schoolnet_user ? 'Plataforma: SchoolNet (Colegium)' : ''}

Extraprogramáticas:
${extras || 'No configuradas'}

Régimen custodia: ${regimen.tipo || 'No aplica'}${regimen.padre ? ` (${regimen.padre} / ${regimen.madre})` : ''}

Horarios semanales:
${JSON.stringify(horarios).substring(0, 1500)}

Próximos eventos (calendario):
${eventosStr || 'Sin eventos próximos'}
${profesores}${calificaciones}${conducta}${asistencia}${companeros}${waReciente}

Fecha de hoy: ${today}`;

    const body = JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 200,
        system: `Eres un bot de WhatsApp que responde preguntas de un apoderado sobre el colegio de sus hijos. Responde breve (1-3 líneas máximo), amigable, útil. Si no tienes la info, di "No tengo esa info, mejor confirma con el colegio 📞". Contexto:\n${context}`,
        messages: [{ role: 'user', content: question }],
    });

    return new Promise((resolve) => {
        const req = https.request({
            hostname: 'api.anthropic.com',
            path: '/v1/messages',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01',
            },
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', async () => {
                try {
                    const json = JSON.parse(data);
                    const answer = json.content?.[0]?.text;
                    if (answer) {
                        // Delay humano (3-8 segundos)
                        const delay = 3000 + Math.random() * 5000;
                        await sock.sendPresenceUpdate('composing', groupId);
                        await new Promise(r => setTimeout(r, delay));
                        await sock.sendMessage(groupId, { text: `🤖 ${answer}` });
                        console.log(`[${userCfg.id}][BOT] Respondió: ${answer.substring(0, 50)}`);
                    }
                } catch (e) {
                    console.log(`[${userCfg.id}][BOT] Error parsing: ${e.message}`);
                }
                resolve();
            });
        });
        req.on('error', (e) => {
            console.log(`[${userCfg.id}][BOT] Error HTTP: ${e.message}`);
            resolve();
        });
        req.write(body);
        req.end();
    });
}

/**
 * Inicia una sesión Baileys para un usuario.
 * Retorna el socket para uso en outbox.
 */
async function startSession(userCfg) {
    const userId = userCfg.id;
    const waCfg = userCfg.whatsapp || {};
    const authFolder = path.join(BASE_DIR, waCfg.auth_folder || `baileys_auth/${userId}`);
    const groups = waCfg.grupos_lectura || {};
    const monitorGroup = waCfg.grupo_monitor || null;

    // Solo iniciar si tiene auth guardada
    if (!fs.existsSync(authFolder)) {
        console.log(`[${userId}] Sin auth en ${authFolder}, saltando`);
        return null;
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const sock = makeWASocket({ auth: state, printQRInTerminal: false });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', (m) => {
        for (const msg of m.messages) {
            const groupId = msg.key.remoteJid;
            const label = groups[groupId];
            const isMonitor = monitorGroup && groupId === monitorGroup;

            if (!label && !isMonitor) continue;

            const body = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
            const docMsg = msg.message?.documentMessage || msg.message?.documentWithCaptionMessage?.message?.documentMessage;

            if (!body && !docMsg) continue;

            const ts = msg.messageTimestamp ? Number(msg.messageTimestamp) : Math.floor(Date.now() / 1000);
            const entry = {
                from: msg.pushName || 'desconocido',
                time: new Date(ts * 1000).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' }),
                date: new Date(ts * 1000).toISOString().split('T')[0],
                body: body,
                timestamp: ts,
            };

            // PDF adjunto
            if (docMsg && docMsg.mimetype === 'application/pdf') {
                const fileName = docMsg.fileName || `doc_${ts}.pdf`;
                entry.attachment = { type: 'pdf', filename: fileName, mimetype: docMsg.mimetype };
                (async () => {
                    try {
                        const buffer = await downloadMediaMessage(msg, 'buffer', {});
                        fs.mkdirSync(ATTACHMENTS_DIR, { recursive: true });
                        const savePath = path.join(ATTACHMENTS_DIR, `${userId}_${label || 'monitor'}_${ts}_${fileName}`);
                        fs.writeFileSync(savePath, buffer);
                        console.log(`[${userId}][PDF] ${savePath} (${buffer.length} bytes)`);
                    } catch (e) {
                        console.log(`[${userId}][PDF] Error: ${e.message}`);
                    }
                })();
            }

            // Monitor group (instrucciones de los padres)
            if (isMonitor) {
                // Ignorar mensajes del bot (emojis de resumen)
                if (body.startsWith('\u{1F4CB}') || body.startsWith('\u{1F4EC}') || body.startsWith('\u{1F680}') || body.startsWith('\u{1F9EA}') || body.startsWith('🤖') || body.startsWith('✅')) return;

                // Si es pregunta (tiene ?), NO guardar como instrucción — solo responder
                if (body.includes('?')) {
                    console.log(`[${userId}][MONITOR] Pregunta de ${entry.from}: ${body.substring(0, 50)}`);
                    botRespond(sock, groupId, body, userCfg).catch(e => {
                        console.log(`[${userId}][BOT] Error: ${e.message}`);
                    });
                    return;
                }

                // Guardar como instrucción (solo si NO es pregunta)
                const monitorFile = path.join(DATA_DIR, `monitor_inputs_${userId}.json`);
                const monitor = loadJSON(monitorFile, []);
                monitor.push(entry);
                saveJSON(monitorFile, cleanOld(monitor));
                console.log(`[${userId}][MONITOR] ${entry.from}: ${body.substring(0, 50)}`);

                // Confirmar instrucción con "Anotado" después de delay
                if (body.length > 5) {
                    (async () => {
                        const delay = 2000 + Math.random() * 3000;
                        await new Promise(r => setTimeout(r, delay));
                        await sock.sendMessage(groupId, { text: '✅ Anotado' });
                        console.log(`[${userId}][BOT] Anotado: ${body.substring(0, 40)}`);
                    })().catch(() => {});
                }
            } else if (label) {
                // Grupo del colegio
                const messages = loadJSON(WA_MESSAGES_FILE, {});
                if (!messages[label]) messages[label] = [];
                messages[label].push(entry);
                messages[label] = cleanOld(messages[label]);
                saveJSON(WA_MESSAGES_FILE, messages);
                console.log(`[${userId}][${label}] ${entry.from}: ${(body || entry.attachment?.filename || '').substring(0, 50)}`);
            }
        }
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'open') {
            console.log(`[${userId}] WhatsApp ONLINE (${waCfg.phone})`);
            sock._isOnline = true;
            // Guardar lista de grupos localmente para list_groups.js
            (async () => {
                try {
                    const groups = await sock.groupFetchAllParticipating();
                    const groupList = Object.values(groups).map(g => ({
                        id: g.id, name: g.subject, participants: g.participants?.length || 0,
                    }));
                    const groupsFile = path.join(DATA_DIR, `groups_${userId}.json`);
                    fs.writeFileSync(groupsFile, JSON.stringify(groupList, null, 2));
                    console.log(`[${userId}] ${groupList.length} grupos guardados localmente`);
                } catch (e) {
                    console.log(`[${userId}] Error guardando grupos: ${e.message}`);
                }
            })();
        }
        if (connection === 'close') {
            sock._isOnline = false;
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log(`[${userId}] LOGGED OUT - necesita re-vincular QR`);
                return; // No reconectar si fue logout manual
            }
            console.log(`[${userId}] Desconectado, reconectando en 5s...`);
            setTimeout(async () => {
                const newSock = await startSession(userCfg);
                if (newSock && global._activeSessions) {
                    global._activeSessions[userId] = newSock;
                }
            }, 5000);
        }
    });

    return sock;
}

// --- MAIN ---
async function main() {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.mkdirSync(path.join(DATA_DIR, 'outbox'), { recursive: true });
    // Ensure outbox is world-writable (send_whatsapp.js runs as root via SSM)
    try { fs.chmodSync(path.join(DATA_DIR, 'outbox'), 0o777); } catch {}

    // Cargar usuarios
    const users = loadJSON(USERS_FILE, []);
    if (users.length === 0) {
        console.log('No hay usuarios en config/users.json');
        return;
    }

    console.log(`Starting WhatsApp listener for ${users.length} usuarios...`);

    // Map de sesiones activas para envío via outbox
    const activeSessions = {};
    global._activeSessions = activeSessions;

    // Iniciar sesión para cada usuario que tenga auth
    for (const userCfg of users) {
        const authFolder = path.join(BASE_DIR, userCfg.whatsapp?.auth_folder || `baileys_auth/${userCfg.id}`);
        if (fs.existsSync(authFolder)) {
            try {
                const sock = await startSession(userCfg);
                if (sock) activeSessions[userCfg.id] = sock;
                console.log(`[${userCfg.id}] Sesión iniciada`);
            } catch (e) {
                console.log(`[${userCfg.id}] Error: ${e.message}`);
            }
            // Pequeña pausa entre conexiones para no parecer sospechoso
            await new Promise(r => setTimeout(r, 2000));
        }
    }

    console.log('Todas las sesiones iniciadas. Escuchando mensajes...');

    // --- OUTBOX WATCHER: Revisar mensajes pendientes cada 3s ---
    const OUTBOX_DIR = path.join(DATA_DIR, 'outbox');
    console.log('[OUTBOX] Watcher iniciado, revisando cada 3s en', OUTBOX_DIR);
    setInterval(() => {
        try {
            const files = fs.readdirSync(OUTBOX_DIR).filter(f => f.endsWith('.json'));
            for (const file of files) {
                const filePath = path.join(OUTBOX_DIR, file);
                const data = loadJSON(filePath, null);
                if (!data || data.status !== 'pending') continue;

                const userId = data.user_id;
                const sock = activeSessions[userId];
                if (!sock) continue;

                // Comando especial (update description, etc.)
                if (data.type === 'update_description') {
                    data.status = 'processing';
                    saveJSON(filePath, data);
                    (async () => {
                        try {
                            await sock.groupUpdateDescription(data.group_id, data.description);
                            data.status = 'sent';
                            saveJSON(filePath, data);
                            console.log(`[${userId}][CMD] Descripción actualizada`);
                            setTimeout(() => { try { fs.unlinkSync(filePath); } catch {} }, 60000);
                        } catch (e) {
                            data.status = 'error'; data.error = e.message;
                            saveJSON(filePath, data);
                            console.log(`[${userId}][CMD] Error desc: ${e.message}`);
                        }
                    })();
                    continue;
                }

                if (data.type === 'update_photo') {
                    data.status = 'processing';
                    saveJSON(filePath, data);
                    (async () => {
                        try {
                            const photoBuffer = fs.readFileSync(data.photo_path);
                            await sock.updateProfilePicture(data.group_id, photoBuffer);
                            data.status = 'sent';
                            saveJSON(filePath, data);
                            console.log(`[${userId}][CMD] Foto del grupo actualizada`);
                            setTimeout(() => { try { fs.unlinkSync(filePath); } catch {} }, 60000);
                        } catch (e) {
                            data.status = 'error'; data.error = e.message;
                            saveJSON(filePath, data);
                            console.log(`[${userId}][CMD] Error foto: ${e.message}`);
                        }
                    })();
                    continue;
                }

                // Mensaje normal

                // Mark as processing to avoid re-entry
                data.status = 'processing';
                saveJSON(filePath, data);

                (async () => {
                    try {
                        for (const target of data.targets) {
                            await sock.sendMessage(target, { text: data.message });
                            console.log(`[${userId}][OUTBOX] Enviado a ${target}`);
                        }
                        data.status = 'sent';
                        data.sent_at = new Date().toISOString();
                        saveJSON(filePath, data);
                        console.log(`[${userId}][OUTBOX] ✅ Completado`);

                        // Limpiar archivo después de 5 min
                        setTimeout(() => {
                            try { fs.unlinkSync(filePath); } catch {}
                        }, 300000);
                    } catch (e) {
                        console.log(`[${userId}][OUTBOX] Error: ${e.message}`);
                        data.status = 'error';
                        data.error = e.message;
                        saveJSON(filePath, data);
                    }
                })();
            }
        } catch (e) {
            // Silently ignore outbox errors
        }
    }, 3000);
}

// Exportar (outbox es el método preferido de envío)
module.exports = { };

// Si se ejecuta directamente (no require'd)
if (require.main === module) {
    main().catch(e => { console.error('Fatal:', e); process.exit(1); });
}
