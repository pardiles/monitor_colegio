# Fuentes Descubiertas - Monitor Colegio

## Resumen de exploración (12 julio 2026)

### Hijos
- **FRANCO ANTONIO ARDILES VALENZUELA** - 5°A (Profesora jefe: María Valentina Mozó Laso)
- **BLANCA FERNANDA** - 1°C (Profesora jefe: Andrea Alejandra Ortega García)

---

## 1. Web Pública del Colegio (sin login)

### 1.1 Calendario de Evaluaciones ✅ API JSON pública
```
GET https://colegiodelsagradocorazon.cl/evaluation/calendar.json
    ?category[]=5&category[]=1
    &start=2026-07-07
    &end=2026-07-20
```
**Respuesta:** Array JSON con objetos:
```json
{
  "id": 11710,
  "title": "Día No Disponible",
  "description": "feriado",
  "start": "2026-07-16",
  "end": "2026-07-17",
  "start_date": "Jueves 16",
  "allDay": true,
  "assessmentCalendar": true,
  "category": "",
  "color": "#cccccc",
  "url": "/evaluation/assessments/11710"
}
```
**Nota:** Esta semana solo muestra feriados/Semana SC. Las evaluaciones aparecen cuando hay pruebas programadas.

### 1.2 Noticias ⚠️ Solo HTML (no hay API JSON ni RSS)
- URL: `https://colegiodelsagradocorazon.cl/noticias`
- Necesita scraping HTML (títulos + links + fechas de publicación)
- No tiene feed RSS ni endpoint JSON

### 1.3 Documentos Importantes ✅ HTML con PDFs
- URL: `https://colegiodelsagradocorazon.cl/documentos_importantes`
- 53 PDFs disponibles (reglamentos, programas, etc.)
- Relevantes: RIE, programa familia, pastoral, etc.

### 1.4 Extraprogramáticas ⚠️ Solo HTML
- URL: `https://colegiodelsagradocorazon.cl/talleres-extraprogramaticos`
- Contacto: inscripcion@colegiodelsagradocorazon.cl (Claudia Cortés)
- No hay API JSON

### 1.5 Charlas para Apoderados ⚠️ Solo HTML
- URL: `https://colegiodelsagradocorazon.cl/charlas-para-apoderados`

---

## 2. SchoolNet (requiere login)

### Login
- URL: `https://schoolnet.colegium.com/webapp/es_CL/login`
- Método: Playwright (formulario JS) → obtener cookie `sn3app`
- Cookie de sesión: `sn3app` (ej: `ek012204n9n7iqes9pku522644`)
- Selección de alumno: `?alumno=0` (Franco) o `?alumno=1` (Blanca) - **NOTA: alumno=1 no cambió el hijo en las pruebas, puede ser otro parámetro**

### 2.1 Comunicaciones ✅ JSON directo
```
GET https://schoolnet.colegium.com/webapp/es_CL/comunicaciones/index
Cookie: sn3app=...
```
**Respuesta:**
```json
{
  "error": null,
  "comunicaciones": [
    {
      "uuid_comunicacion": "9c8a4e53-...",
      "asunto": "SC Info 09-07-2026",
      "remitente": "Colegio del Sagrado Corazón Apoquindo",
      "fecha_para_ordenar": "2026-07-09T18:09:52.77284",
      "adjuntos": 0,
      "leido_solo_comunicacion_original": true,
      "permite_respuesta": false
    }
  ],
  "filtros": [...]
}
```
**Comunicaciones recientes encontradas:**
- SC Info 09-07-2026
- SC Info 18-06-2026
- SC Info 11-06-2026
- "Información importante: viernes 19 de junio sin clases"
- SC Info 04-06-2026
- SC Info 28-05-2026
- SC Info 20-05-2026
- "Fotografías Reservado para mí, 1° básico"

### 2.2 Agenda ⚠️ Vacía actualmente
```
GET https://schoolnet.colegium.com/webapp/es_CL/agenda/index
```
**Respuesta:** Tiene la estructura pero `eventAgenda: []` (vacía)
- Muestra: `cursos: [2, "5-A", "1-C"]`
- Fechas: inicio 2026-03-02, término 2026-12-10

### 2.3 Horario ⚠️ Vacío en la API
```
GET https://schoolnet.colegium.com/webapp/es_CL/horario/index
```
**Respuesta:** Estructura con `horas: [], dia_1: [], dia_2: []...` todo vacío.
El colegio aparentemente no tiene cargado el horario en SchoolNet.

### 2.4 Calificaciones ✅ JSON completo
```
GET https://schoolnet.colegium.com/webapp/es_CL/calificaciones/index?tipocalificacion=nota
```
**Respuesta:** Notas por asignatura con parciales, promedios, etc.
- Asignaturas: Lenguaje, Inglés, Historia, Matemática, Ciencias, Artes Visuales, Artes Musicales, Tecnología, Ed. Física, Religión, Orientación
- Periodos: Primer Semestre, Segundo Semestre

### 2.5 Asistencia/Conducta ✅ JSON
```
GET https://schoolnet.colegium.com/webapp/es_CL/asistencia/index
GET https://schoolnet.colegium.com/webapp/es_CL/conducta/index
```
- Franco: 20 inasistencias, 0 atrasos, 100% asistencia
- Conducta: 25 anotaciones (13 positivas, 7 negativas, 5 neutras)

### 2.6 Pagos ✅ JSON
```
GET https://schoolnet.colegium.com/webapp/es_CL/pagos/index
```
**Respuesta:** Historial de pagos con fechas, montos, forma de pago.

### 2.7 Cobranza ✅ URL con JWT
```
GET https://schoolnet.colegium.com/webapp/es_CL/cobranza/index
```
**Respuesta:** URL de redirección con JWT para ver detalles de cobranza en `sn4.colegium.com/cobranza`

### 2.8 Informes ✅ JSON con links a PDFs
```
GET https://schoolnet.colegium.com/webapp/es_CL/informes/index
```
**Respuesta:** Lista de informes con rutas a PDFs descargables.

### 2.9 Compañeros ✅ JSON
```
GET https://schoolnet.colegium.com/webapp/es_CL/companeros/index
```
**Respuesta:** Lista de compañeros con datos de contacto (nombres padres, emails, teléfonos, dirección).

---

## 3. Gmail (por implementar)
- Remitente principal: `comunicaciones@colegiodelsagradocorazon.cl`
- Otros: sdcbasico@, sdcmedio@, administracion@, centrodepadres@
- Método: Gmail API con OAuth2

---

## Arquitectura Final - Opción A

### Lambda 1: Ingesta (diaria, 5:00 AM)
1. **Login SchoolNet** (Playwright headless) → extraer cookie `sn3app`
2. **Comunicaciones SchoolNet** (requests con cookie) → guardar en S3
3. **Calendario evaluaciones** (API pública, requests) → guardar en S3
4. **Noticias web** (scraping HTML con Scrapling) → guardar en S3
5. **Gmail** (Gmail API) → guardar en S3

### Lambda 2: Resumen (diaria, 6:30 AM)
1. Leer datos consolidados de S3
2. Generar resumen con OpenAI (contexto: hoy + semana)
3. Enviar por WhatsApp (Twilio)

### Consideración Lambda + Playwright
- Lambda 1 necesita Playwright → **Lambda con Docker image** (custom runtime)
- O alternativamente: **ECS Fargate task** para el login, y una Lambda liviana para el resto

---

## Datos clave para el .env
```
SCHOOLNET_USERNAME=avalenzuela143
SCHOOLNET_PASSWORD=2776523xX#
SCHOOL_CALENDAR_URL=https://colegiodelsagradocorazon.cl/evaluation/calendar.json
SCHOOL_NEWS_URL=https://colegiodelsagradocorazon.cl/noticias
SCHOOL_CATEGORIES=5,1
CHILD_1_NAME=Franco
CHILD_1_COURSE=5-A
CHILD_1_ALUMNO_IDX=0
CHILD_2_NAME=Blanca
CHILD_2_COURSE=1-C
CHILD_2_ALUMNO_IDX=1
```
