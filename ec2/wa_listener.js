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
const USERS_DIR = path.join(BASE_DIR, 'config', 'users');
const USERS_FILE = path.join(BASE_DIR, 'config', 'users.json'); // fallback legacy
const WA_MESSAGES_FILE = path.join(DATA_DIR, 'whatsapp_messages.json');

// Cargar API keys desde .env
let ANTHROPIC_API_KEY = '';
let GEMINI_API_KEY = '';
let AI_ENGINE = 'gemini'; // default: gemini (más barato)
try {
    const envFile = fs.readFileSync(path.join(BASE_DIR, '.env'), 'utf-8');
    for (const line of envFile.split('\n')) {
        if (line.startsWith('ANTHROPIC_API_KEY=')) {
            ANTHROPIC_API_KEY = line.split('=')[1].trim().replace(/['"]/g, '');
        }
        if (line.startsWith('GEMINI_API_KEY=')) {
            GEMINI_API_KEY = line.split('=')[1].trim().replace(/['"]/g, '');
        }
        if (line.startsWith('AI_ENGINE=')) {
            AI_ENGINE = line.split('=')[1].trim().replace(/['"]/g, '');
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

// Historial de conversación por usuario (últimas 5 interacciones)
const _conversationHistory = {};
function getConversationHistory(userId, newQuestion) {
    if (!_conversationHistory[userId]) _conversationHistory[userId] = [];
    const history = _conversationHistory[userId];
    // Agregar nueva pregunta
    history.push({ role: 'user', content: newQuestion });
    // Mantener últimas 10 mensajes (5 pares user/assistant)
    while (history.length > 10) history.shift();
    return [...history];
}
function addBotResponse(userId, response) {
    if (!_conversationHistory[userId]) _conversationHistory[userId] = [];
    _conversationHistory[userId].push({ role: 'assistant', content: response });
    while (_conversationHistory[userId].length > 10) _conversationHistory[userId].shift();
}

/**
 * Bot conversacional: responde preguntas del apoderado en el grupo Monitor.
 */
async function botRespond(sock, groupId, question, userCfg) {
    if (!GEMINI_API_KEY && !ANTHROPIC_API_KEY) return;

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
    const extras = (userCfg.extraprogramaticas || []).filter(e => {
        if (!e.fecha_inicio) return true;
        const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' });
        return e.fecha_inicio <= today;
    }).map(e => `${e.nombre}: ${e.dia} ${e.horario} (${e.hijo}) → sale ${e.hora_salida_real}`).join('\n');
    const extrasProximas = (userCfg.extraprogramaticas || []).filter(e => {
        if (!e.fecha_inicio) return false;
        const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' });
        return e.fecha_inicio > today;
    }).map(e => `${e.nombre}: ${e.dia} ${e.horario} (${e.hijo}) — inicia ${e.fecha_inicio}`).join('\n');
    const horarios = loadJSON(path.join(DATA_DIR, 'horarios.json'), {});

    // Datos adicionales del colegio (profesores, compañeros, etc.)
    const colegio = userCfg.colegio || {};
    const regimen = userCfg.regimen || {};

    // Cargar contexto enriquecido (generado por el scraping diario)
    const botContext = loadJSON(path.join(DATA_DIR, `bot_context_${userCfg.id}.json`), {});

    let calendario = loadJSON(path.join(DATA_DIR, `eventos_${userCfg.id}.json`), []);
    const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' }); // YYYY-MM-DD en hora Chile
    let upcoming = calendario.filter(e => e.fecha >= today).slice(0, 20);
    // Fallback: si no hay eventos en archivo directo, usar bot_context.calendario
    if (upcoming.length === 0 && botContext.calendario && botContext.calendario.length > 0) {
        upcoming = botContext.calendario.filter(e => e.fecha >= today).slice(0, 20);
    }
    const eventosStr = upcoming.map(e => `${e.fecha}${e.hora ? ' '+e.hora : ''} | ${e.descripcion} | hijo=${e.hijo}${e.lugar ? ' | lugar='+e.lugar : ''}`).join('\n');
    
    // Formatear compañeros como texto legible (con teléfono, dirección, apoderados)
    let companerosTxt = '';
    if (botContext.companeros) {
        for (const [hijo, lista] of Object.entries(botContext.companeros)) {
            const nombres = lista.map(c => c.nombre).join(', ');
            companerosTxt += `\nCompañeros de ${hijo}: ${nombres}`;
            // Detalle de cada compañero (teléfono, dirección, apoderados)
            const detalles = lista.filter(c => c.telefono || c.direccion || c.padre || c.madre).map(c => {
                let det = c.nombre;
                if (c.telefono) det += ` | Tel: ${c.telefono}`;
                if (c.direccion) det += ` | Dir: ${c.direccion}`;
                if (c.padre) det += ` | Papá: ${c.padre}`;
                if (c.madre) det += ` | Mamá: ${c.madre}`;
                if (c.cumple) det += ` | Cumple: ${c.cumple}`;
                return det;
            }).join('\n  ');
            if (detalles) companerosTxt += `\nDetalle compañeros ${hijo}:\n  ${detalles}`;
        }
    }

    // Formatear calificaciones como texto
    let calificacionesTxt = '';
    if (botContext.calificaciones) {
        for (const [hijo, asigs] of Object.entries(botContext.calificaciones)) {
            if (Array.isArray(asigs) && asigs.length > 0) {
                const nombres = asigs.map(a => a.asignatura).filter(Boolean).join(', ');
                const notas = asigs.filter(a => a.promedio).map(a => `${a.asignatura}: ${a.promedio}`).join(', ');
                calificacionesTxt += `\nAsignaturas de ${hijo}: ${nombres}`;
                if (notas) {
                    calificacionesTxt += `\nNotas 1er semestre ${hijo}: ${notas}`;
                }
            }
        }
    }
    // 2do semestre
    if (botContext.calificaciones_sem2) {
        for (const [hijo, asigs] of Object.entries(botContext.calificaciones_sem2)) {
            if (Array.isArray(asigs) && asigs.length > 0) {
                const notas = asigs.filter(a => a.promedio).map(a => `${a.asignatura}: ${a.promedio}`).join(', ');
                if (notas) {
                    calificacionesTxt += `\nNotas 2do semestre ${hijo}: ${notas}`;
                } else {
                    calificacionesTxt += `\nNotas 2do semestre ${hijo}: Aún no están cargadas en SchoolNet.`;
                }
            }
        }
    } else if (botContext.calificaciones) {
        // Si no hay sem2, indicar que no están disponibles
        for (const hijo of Object.keys(botContext.calificaciones)) {
            calificacionesTxt += `\nNotas 2do semestre ${hijo}: Aún no están cargadas en SchoolNet.`;
        }
    }

    // Formatear conducta
    let conductaTxt = '';
    if (botContext.conducta) {
        for (const [hijo, anots] of Object.entries(botContext.conducta)) {
            if (Array.isArray(anots) && anots.length > 0) {
                const formatted = anots.slice(-5).map(a => {
                    if (typeof a === 'object') {
                        return `${a.fecha || ''}: ${a.motivo || a.observacion || JSON.stringify(a).substring(0, 80)} (${a.profesor || ''})`;
                    }
                    return String(a).substring(0, 80);
                }).join('; ');
                conductaTxt += `\nConducta ${hijo} (últimas): ${formatted}`;
            }
        }
    }

    // Asistencia
    let asistenciaTxt = '';
    if (botContext.asistencia) {
        for (const [hijo, info] of Object.entries(botContext.asistencia)) {
            asistenciaTxt += `\nAsistencia ${hijo}: ${info.inasistencias || 0} inasistencias totales`;
            // Extraer fechas de inasistencias
            if (info.ultimas && Array.isArray(info.ultimas)) {
                const fechas = [];
                for (const asig of info.ultimas) {
                    if (asig.detalle && Array.isArray(asig.detalle)) {
                        for (const d of asig.detalle) {
                            if (d.fecha) fechas.push(`${d.fecha} (${asig.asig})`);
                        }
                    }
                }
                if (fechas.length > 0) {
                    asistenciaTxt += `. Fechas inasistencias: ${fechas.slice(-10).join(', ')}`;
                }
            }
            // Atrasos
            if (info.atrasos && Array.isArray(info.atrasos) && info.atrasos.length > 0) {
                const atrasosStr = info.atrasos.slice(-5).map(a => {
                    if (typeof a === 'object') return `${a.fecha || ''} ${a.asig || ''}`;
                    return String(a);
                }).join(', ');
                asistenciaTxt += `. Atrasos: ${atrasosStr}`;
            }
        }
    }

    // WA reciente
    let waRecienteTxt = '';
    if (botContext.whatsapp_reciente) {
        for (const [grupo, msgs] of Object.entries(botContext.whatsapp_reciente)) {
            if (msgs.length > 0) {
                waRecienteTxt += `\nGrupo ${grupo} (últimos msgs): ${msgs.slice(-5).map(m => `${m.from}: ${m.body}`).join(' | ').substring(0, 300)}`;
            }
        }
    }

    // Emails recientes
    let emailsTxt = '';
    if (botContext.emails_recientes && botContext.emails_recientes.length > 0) {
        emailsTxt = '\nEmails recientes del colegio:';
        for (const e of botContext.emails_recientes.slice(-5)) {
            emailsTxt += `\n  ${e.fecha} | De: ${e.de} | Asunto: ${e.asunto} | ${e.resumen?.substring(0, 100) || ''}`;
        }
    }

    // Documentos PDF recibidos por WhatsApp (circulares, calendarios de pruebas)
    let docsPdfTxt = '';
    if (botContext.documentos_wa && botContext.documentos_wa.length > 0) {
        docsPdfTxt = '\nDocumentos PDF recibidos por WhatsApp:';
        for (const doc of botContext.documentos_wa.slice(0, 5)) {
            docsPdfTxt += `\n  [${doc.fecha_recibido}] ${doc.filename} (grupo: ${doc.grupo}): ${doc.contenido.substring(0, 500)}`;
        }
    }

    // SC Info
    let scinfoTxt = '';
    if (botContext.scinfo && botContext.scinfo.contenido) {
        scinfoTxt = `\nSC Info (${botContext.scinfo.fecha}): ${botContext.scinfo.contenido.substring(0, 500)}`;
    }

    // Pagos realizados (historial)
    let pagosTxt = '';
    if (botContext.pagos) {
        const pagos = botContext.pagos;
        if (pagos.fechas && Array.isArray(pagos.fechas)) {
            pagosTxt = '\nPagos realizados (historial):';
            for (let i = 0; i < pagos.fechas.length && i < 10; i++) {
                const saldo = pagos.saldos?.[i] || '0';
                const estado = saldo === '0' ? '✅ Pagado' : `⚠️ Saldo: $${saldo}`;
                pagosTxt += `\n  ${pagos.fechas[i]} | $${pagos.montos?.[i] || '?'} | ${pagos.formas?.[i] || ''} | ${estado}`;
            }
        } else if (typeof pagos === 'object') {
            pagosTxt += `\nPagos: ${JSON.stringify(pagos).substring(0, 500)}`;
        }
    }

    // Avisos de cobranza (vencimientos futuros)
    let cobranzaTxt = '';
    if (botContext.avisos_cobranza && Array.isArray(botContext.avisos_cobranza)) {
        cobranzaTxt = '\nAvisos de cobranza (próximos vencimientos):';
        for (const av of botContext.avisos_cobranza) {
            const pendiente = av.monto_a_pagar && av.monto_a_pagar !== '0' ? `⚠️ Pendiente: $${av.monto_a_pagar}` : '✅ Pagado';
            cobranzaTxt += `\n  Vence: ${av.vencimiento || ''} | Neto: $${av.monto_neto || ''} | ${pendiente}`;
        }
    }

    const profesoresTxt = (botContext.profesores || []).map(p => `${p.hijo} (${p.curso}) - Prof jefe: ${p.profesora_jefe}${p.email ? ' - ' + p.email : ''}`).join('\n');

    // Formatear horarios como texto legible
    let horariosTxt = '';
    if (horarios) {
        for (const [key, dias] of Object.entries(horarios)) {
            horariosTxt += `\nHorario ${key}:`;
            if (typeof dias === 'object') {
                for (const [dia, info] of Object.entries(dias)) {
                    if (info && info.ramos) {
                        horariosTxt += `\n  ${dia}: ${info.ramos.join(', ')}. Sale: ${info.hora_salida || '?'}`;
                    }
                }
            }
        }
    }

    const context = `Hijos:
${hijos}

Colegio: ${colegio.nombre || ''}

Extraprogramáticas activas:
${extras || 'No configuradas'}
${extrasProximas ? '\nExtraprogramáticas por comenzar (aún no parten):\n' + extrasProximas : ''}

Régimen custodia: ${regimen.tipo || 'No aplica'}${regimen.padre ? ` (${regimen.padre} / ${regimen.madre})` : ''}
${horariosTxt}

Próximos eventos (calendario):
${eventosStr || 'Sin eventos próximos'}

Profesores:
${profesoresTxt}
${calificacionesTxt}
${asistenciaTxt}
${conductaTxt}
${companerosTxt.substring(0, 2000)}
${waRecienteTxt}
${emailsTxt}
${docsPdfTxt}
${scinfoTxt}
${pagosTxt}
${cobranzaTxt}

Menú casino hoy: ${botContext.casino_hoy || botContext.casino_menu || 'No disponible'}

Fecha de hoy: ${today}`;

    const systemPrompt = `Eres un bot de WhatsApp que responde preguntas de un apoderado sobre el colegio de sus hijos. Responde breve (1-3 líneas máximo), amigable, útil. Si no tienes la info, di "No tengo esa info, mejor confirma con el colegio 📞". Contexto:\n${context}`;

    // Seleccionar engine
    const useGemini = AI_ENGINE === 'gemini' && GEMINI_API_KEY;
    
    if (useGemini) {
        // Gemini Flash API
        const body = JSON.stringify({
            contents: [{
                parts: [{ text: `${systemPrompt}\n\n---\nPregunta del apoderado: ${question}` }]
            }],
            generationConfig: {
                maxOutputTokens: 200,
                temperature: 0.3,
            }
        });

        return new Promise((resolve) => {
            const req = https.request({
                hostname: 'generativelanguage.googleapis.com',
                path: `/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            }, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', async () => {
                    try {
                        const json = JSON.parse(data);
                        const answer = json.candidates?.[0]?.content?.parts?.[0]?.text;
                        if (answer) {
                            const delay = 3000 + Math.random() * 5000;
                            await sock.sendPresenceUpdate('composing', groupId);
                            await new Promise(r => setTimeout(r, delay));
                            await sock.sendMessage(groupId, { text: `🤖 ${answer}` });
                            addBotResponse(userCfg.id, answer);
                            console.log(`[${userCfg.id}][BOT/gemini] ${answer.substring(0, 50)}`);
                        }
                    } catch (e) {
                        console.log(`[${userCfg.id}][BOT/gemini] Error: ${e.message}`);
                    }
                    resolve();
                });
            });
            req.on('error', (e) => { console.log(`[${userCfg.id}][BOT/gemini] HTTP Error: ${e.message}`); resolve(); });
            req.write(body);
            req.end();
        });
    } else {
        // Claude Haiku API (fallback)
        const body = JSON.stringify({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 200,
            system: systemPrompt,
            messages: getConversationHistory(userCfg.id, question),
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
                            const delay = 3000 + Math.random() * 5000;
                            await sock.sendPresenceUpdate('composing', groupId);
                            await new Promise(r => setTimeout(r, delay));
                            await sock.sendMessage(groupId, { text: `🤖 ${answer}` });
                            addBotResponse(userCfg.id, answer);
                            console.log(`[${userCfg.id}][BOT/haiku] ${answer.substring(0, 50)}`);
                        }
                    } catch (e) {
                        console.log(`[${userCfg.id}][BOT/haiku] Error: ${e.message}`);
                    }
                    resolve();
                });
            });
            req.on('error', (e) => { console.log(`[${userCfg.id}][BOT/haiku] HTTP Error: ${e.message}`); resolve(); });
            req.write(body);
            req.end();
        });
    }
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
    const sock = makeWASocket({ 
        auth: state, 
        printQRInTerminal: false,
        syncFullHistory: false,
        markOnlineOnConnect: false,
    });
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
                date: new Date(ts * 1000).toLocaleDateString('sv-SE', { timeZone: 'America/Santiago' }),
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
                if (body.startsWith('\u{1F4CB}') || body.startsWith('\u{1F4EC}') || body.startsWith('\u{1F680}') || body.startsWith('\u{1F9EA}') || body.startsWith('🤖') || body.startsWith('✅') || body.startsWith('📬') || body.startsWith('📋') || body.startsWith('⏳') || body.startsWith('#') || body.startsWith('👋')) return;

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

    // Monitorear participantes del grupo Monitor (max 2 + bot)
    sock.ev.on('group-participants.update', async (update) => {
        if (update.action === 'add' && monitorGroup && update.id === monitorGroup) {
            // Verificar si excede max participantes (2 destinatarios + bot = 3)
            try {
                const meta = await sock.groupMetadata(monitorGroup);
                if (meta.participants.length > 3) {
                    // Expulsar a los nuevos (que no son destinatarios originales)
                    const allowed = new Set((waCfg.destinatarios_monitor || []).map(n => n + '@s.whatsapp.net'));
                    const toRemove = update.participants.filter(p => !allowed.has(p));
                    if (toRemove.length > 0) {
                        await sock.groupParticipantsUpdate(monitorGroup, toRemove, 'remove');
                        await sock.sendMessage(monitorGroup, { text: '⚠️ Este grupo acepta máximo 2 destinatarios. Para cambiar a alguien, escribe: "sacar a [nombre]" y "agregar a +56XXXXXXXXX [nombre]". O hazlo desde la landing.' });
                        console.log(`[${userId}][GROUP] Expulsados: ${toRemove.join(', ')}`);
                    }
                }
            } catch (e) {
                console.log(`[${userId}][GROUP] Error monitoreando: ${e.message}`);
            }
        }
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'open') {
            console.log(`[${userId}] WhatsApp ONLINE (${waCfg.phone})`);
            sock._isOnline = true;
            sock._retryCount = 0; // Reset retry count on successful connection
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
            // Reconexión con backoff exponencial
            const retryCount = (sock._retryCount || 0) + 1;
            sock._retryCount = retryCount;
            
            if (retryCount > 10) {
                console.log(`[${userId}] Demasiados reintentos (${retryCount}), reiniciando proceso...`);
                process.exit(1); // systemd lo reiniciará
            }
            
            const baseDelay = Math.min(60000, 5000 * Math.pow(2, retryCount - 1)); // 5s, 10s, 20s, 40s, 60s max
            const jitter = Math.floor(Math.random() * 5000);
            const delay = baseDelay + jitter;
            console.log(`[${userId}] Desconectado (code=${code}), reconectando en ${Math.round(delay/1000)}s (intento #${retryCount})...`);
            
            setTimeout(async () => {
                console.log(`[${userId}] Reconectando...`);
                try {
                    // Crear nuevo socket con las mismas credenciales
                    const newSock = await startSession(userCfg);
                    // Actualizar referencia en activeSessions
                    if (global._activeSessions && newSock) {
                        global._activeSessions[userId] = newSock;
                    }
                } catch (e) {
                    console.log(`[${userId}] Error reconectando: ${e.message}`);
                    // Si falla, process.exit para que systemd reinicie
                    if (retryCount >= 5) {
                        console.log(`[${userId}] Forzando restart del servicio`);
                        process.exit(1);
                    }
                }
            }, delay);
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

    // Cargar usuarios desde archivos individuales (S3) + fallback legacy
    let users = [];
    if (fs.existsSync(USERS_DIR)) {
        const files = fs.readdirSync(USERS_DIR).filter(f => f.endsWith('.json') && f !== 'admin.json');
        for (const file of files) {
            try {
                const u = JSON.parse(fs.readFileSync(path.join(USERS_DIR, file), 'utf-8'));
                if (u.id) users.push(u);
            } catch {}
        }
    }
    // Merge con legacy (para campos que solo existen ahí, como colegio detallado)
    const legacyUsers = loadJSON(USERS_FILE, []);
    for (const lu of legacyUsers) {
        const existing = users.find(u => u.id === lu.id);
        if (existing) {
            // Legacy overrides solo campos vacíos en S3
            for (const [k, v] of Object.entries(lu)) {
                if (v && !existing[k]) existing[k] = v;
            }
        } else {
            users.push(lu);
        }
    }
    if (users.length === 0) {
        console.log('No hay usuarios en config/users/ ni config/users.json');
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
                if (!data) continue;
                // Procesar pendientes y reintentar errores recientes (menos de 30 min)
                if (data.status === 'pending') {
                    // OK, procesar
                } else if (data.status === 'error') {
                    // Reintentar si el error fue hace menos de 30 min y no ha reintentado más de 3 veces
                    const retries = data._retries || 0;
                    const errorAge = Date.now() - new Date(data.created_at || 0).getTime();
                    if (retries >= 3 || errorAge > 30 * 60 * 1000) continue;
                    data._retries = retries + 1;
                    data.status = 'pending';
                    console.log(`[${data.user_id}][OUTBOX] Reintento #${data._retries}`);
                } else {
                    continue;
                }

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
