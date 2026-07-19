/**
 * Genera imagen con texto y la pone como foto del grupo Monitor via outbox.
 */
const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');

const BASE_DIR = '/opt/monitor-colegio';
const GROUP_ID = '120363409985436264@g.us';
const COLEGIO = 'Colegio del Sagrado Corazón Apoquindo';

// Generar imagen 500x500
const canvas = createCanvas(500, 500);
const ctx = canvas.getContext('2d');

// Fondo gradiente
const grad = ctx.createLinearGradient(0, 0, 0, 500);
grad.addColorStop(0, '#0a0a2a');
grad.addColorStop(1, '#1a1a4a');
ctx.fillStyle = grad;
ctx.fillRect(0, 0, 500, 500);

// Emoji
ctx.font = '80px serif';
ctx.textAlign = 'center';
ctx.fillText('📚', 250, 150);

// "Monitor Colegio"
ctx.font = 'bold 36px sans-serif';
ctx.fillStyle = '#4fc3f7';
ctx.fillText('Monitor Colegio', 250, 240);

// Nombre del colegio (wrap)
ctx.font = '24px sans-serif';
ctx.fillStyle = '#e0e0e0';
const words = COLEGIO.split(' ');
let lines = [];
let currentLine = '';
for (const word of words) {
    const test = currentLine ? currentLine + ' ' + word : word;
    if (ctx.measureText(test).width > 420) {
        lines.push(currentLine);
        currentLine = word;
    } else {
        currentLine = test;
    }
}
if (currentLine) lines.push(currentLine);
lines.forEach((line, i) => {
    ctx.fillText(line, 250, 300 + i * 35);
});

// Guardar
const photoPath = path.join(BASE_DIR, 'data', 'group_photo.png');
fs.writeFileSync(photoPath, canvas.toBuffer('image/png'));
console.log(`Imagen generada: ${photoPath}`);

// Escribir comando outbox
const cmd = {
    user_id: 'pablo_ardiles',
    type: 'update_photo',
    group_id: GROUP_ID,
    photo_path: photoPath,
    status: 'pending'
};
const outboxFile = path.join(BASE_DIR, 'data', 'outbox', 'cmd_photo.json');
fs.writeFileSync(outboxFile, JSON.stringify(cmd, null, 2));
fs.chmodSync(outboxFile, 0o666);
console.log('Comando de foto en outbox. wa_listener lo procesará en ~3s.');
