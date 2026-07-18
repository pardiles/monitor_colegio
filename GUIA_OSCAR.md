# 🚀 Guía para Oscar - Puesta en marcha del Monitor

## ¿Qué es esto?

Un bot que lee los grupos de WhatsApp de los colegios (Oxford School y Acuarela Montessori), scrapea info de las plataformas, y te manda un resumen diario por WhatsApp con lo importante del día.

---

## Lo que necesitas hacer AHORA

### Paso 1: Vincular tu WhatsApp con Baileys (escanear QR)

El sistema usa **Baileys** (librería que se conecta a WhatsApp Web) para leer los mensajes de los grupos. Necesitas vincular tu número escaneando un código QR, igual que cuando vinculas WhatsApp Web en el computador.

**En la EC2 (o donde corra el servicio):**

```bash
cd /opt/monitor-colegio
node vincular_oscar.js
```

Esto va a mostrar un código QR en la terminal. Escanéalo desde:
- WhatsApp → Menú (⋮) → Dispositivos vinculados → Vincular dispositivo

La sesión queda guardada en `baileys_auth/oscar/` y no necesitas volver a escanear (a menos que se desconecte).

---

### Paso 2: Conseguir los IDs de los grupos de WhatsApp

Una vez vinculado, necesitamos saber los IDs reales de los grupos del colegio. Actualmente están como placeholder (`_pendiente_*`) en la config:

```
"_pendiente_familias_acuarela": "acuarela_simon"
"_pendiente_martin_pescador": "martin_pescador_simon"  
"_pendiente_4basico_a": "4A_esperanza"
```

**Para obtener los IDs reales:**

```bash
node listar_grupos_oscar.js
```

Esto imprime todos los grupos en los que estás. Busca los que te interesan y anota los IDs (tienen formato `120363XXXXXXXXXX@g.us`).

Después hay que actualizar `config/users.json` con los IDs correctos.

---

### Paso 3: Datos de los colegios

Necesitamos que completes esta info (la que tengas):

#### Oxford School (Esperanza)
- [ ] ¿Tiene plataforma de notas online? ¿Cuál? ¿User/pass?
- [ ] ¿Hay calendario de pruebas online?
- [ ] ¿Qué grupos de WhatsApp del colegio tienes? (nombre de cada uno)
- [ ] ¿Recibes emails del colegio? ¿En qué correo?
- [ ] Curso actual de Esperanza
- [ ] Profesora jefe

#### Acuarela Montessori (Simón)
- [x] Cuaderno Rojo (notas): alediferencial@gmail.com / Hola2244
- [ ] ¿Qué grupos de WhatsApp del colegio tienes?
- [ ] Curso actual de Simón
- [ ] Profesora jefe / guía

---

### Paso 4: Gmail (opcional pero recomendado)

Si recibes comunicaciones del colegio por email, necesitamos configurar acceso OAuth a tu Gmail. Esto se hace una sola vez:

1. Te vamos a pasar un link de autorización de Google
2. Lo abres, autorizas, y nos devuelve un token
3. El token se guarda en `config/tokens/oscar_*_token.json`

**Esto NO da acceso a enviar emails ni a tus datos personales**, solo lectura de correos de los dominios del colegio.

---

## ⚠️ Tema: Límite de 4 dispositivos vinculados en WhatsApp

WhatsApp permite **máximo 4 dispositivos vinculados** por número (además del teléfono principal). Esto incluye:
- WhatsApp Web en el navegador
- WhatsApp Desktop (app de PC/Mac)
- Otros dispositivos vinculados

**Nuestro bot usa 1 slot de esos 4.**

### ¿Cómo saber cuántos tienes ocupados?

WhatsApp → ⋮ → Dispositivos vinculados → ahí ves la lista

### ¿Qué pasa si ya tienes 4?

Tienes que cerrar sesión de uno de ellos para que el bot pueda conectarse. El bot aparece como "Dispositivo vinculado" sin nombre visible (o puede decir "Chrome" o similar).

### ¿Se puede desconectar solo?

Sí, después de ~14 días sin actividad WhatsApp desconecta el dispositivo. Si pasa, hay que volver a escanear QR. Nosotros detectamos esto y te avisamos.

### Estrategia para no pasarse:

| Slot | Uso |
|------|-----|
| 1 | Bot Monitor Colegio (Baileys) |
| 2 | WhatsApp Web del PC |
| 3 | WhatsApp Desktop (si usas) |
| 4 | Libre / backup |

**En resumen: asegúrate de tener AL MENOS 1 slot libre antes de vincular el bot.**

---

## ¿Qué va a hacer el bot una vez configurado?

1. **Escucha en tiempo real** los mensajes de los grupos del colegio
2. **2 veces al día** (mañana y noche) genera un resumen con IA:
   - **AM (~7:00)**: Qué pasa HOY (pruebas, actividades, horarios, qué llevar)
   - **PM (~20:00)**: Qué pasó hoy + qué viene mañana
3. Te manda el resumen por WhatsApp (al número tuyo y al de Ale si quieren)

---

## Resumen de acciones pendientes Oscar

| # | Qué | Cómo | Dificultad |
|---|-----|------|-----------|
| 1 | Vincular WhatsApp (QR) | Escanear código desde el teléfono | 🟢 Fácil |
| 2 | Decirnos los grupos WA | Mandar lista de nombres de grupos | 🟢 Fácil |
| 3 | Datos colegios (cursos, profes) | Responder las preguntas de arriba | 🟢 Fácil |
| 4 | Gmail OAuth (opcional) | Click en un link + autorizar | 🟡 Medio |

---

## Contacto

Cualquier duda → grupo Monitor Colegio o directo a Pablo.
