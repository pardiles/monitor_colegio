# Modelo de Negocio - Monitor Colegio

## Propuesta de valor
Resúmenes diarios automáticos por WhatsApp con toda la información escolar relevante: comunicaciones, horarios, evaluaciones, entrevistas, extraprogramáticas. El apoderado no tiene que revisar emails, apps del colegio ni grupos de WhatsApp — recibe todo resumido 2 veces al día.

## Cliente
El colegio (B2B). El colegio ofrece el servicio a todos sus apoderados. El que quiere lo usa.

## Pricing (en UF)

| Concepto | Valor |
|---|---|
| Base mensual | 26 UF (~$1.000.000 CLP) — incluye hasta 500 alumnos |
| Alumno extra (sobre 500) | $1.000 CLP/alumno/mes |
| Setup | Incluido |
| Prueba | 1er mes gratis |
| Contrato mínimo | 12 meses (después del mes de prueba) |

### Ejemplos por tamaño de colegio

| Colegio | Alumnos | Cobro mensual | Cobro anual |
|---|---|---|---|
| Chico (300 alumnos) | 300 | $1.000.000 | $12.000.000 |
| Mediano (800 alumnos) | 800 | $1.300.000 | $15.600.000 |
| Grande (1500 alumnos) | 1500 | $2.000.000 | $24.000.000 |

### Costo de infraestructura

| Familias registradas | Costo real/mes (CLP) |
|---|---|
| 50 | ~$10.000 |
| 200 | ~$40.000 |
| 500 | ~$100.000 |
| 1000 | ~$200.000 |

Basado en $0.21 USD/usuario/mes (arquitectura escalable con Gemini Flash + proxy bulk).

### Márgenes

| Colegio | Cobro/mes | Costo/mes (60% adopción) | Margen |
|---|---|---|---|
| Chico (300 al, 120 familias) | $1.000.000 | ~$25.000 | 97% |
| Mediano (800 al, 300 familias) | $1.300.000 | ~$64.000 | 95% |
| Grande (1500 al, 600 familias) | $2.000.000 | ~$126.000 | 94% |

## Proyección primer año (solo, sin equipo, colegios medianos)

| Mes | Colegios pagando | Ingreso | Costo infra | Profit |
|---|---|---|---|---|
| 1 | 0 (1 en prueba) | $0 | $19.000 | -$19.000 |
| 2 | 1 | $1.300.000 | $38.000 | $1.262.000 |
| 3 | 2 | $2.600.000 | $57.000 | $2.543.000 |
| 4 | 3 | $3.900.000 | $76.000 | $3.824.000 |
| 5 | 4 | $5.200.000 | $95.000 | $5.105.000 |
| 6 | 5 | $6.500.000 | $114.000 | $6.386.000 |
| 7 | 6 | $7.800.000 | $133.000 | $7.667.000 |
| 8 | 7 | $9.100.000 | $152.000 | $8.948.000 |
| 9 | 8 | $10.400.000 | $171.000 | $10.229.000 |
| 10 | 9 | $11.700.000 | $190.000 | $11.510.000 |
| 11 | 10 | $13.000.000 | $209.000 | $12.791.000 |
| 12 | 10 | $13.000.000 | $209.000 | $12.791.000 |

**Total año 1: ~$84M ingreso / ~$1.5M costo / ~$82.5M profit**

**Sueldo objetivo: $6M líquidos/mes → cubierto en mes 7 (6 colegios).**

## Target de mercado (primer año)
- Colegios particulares pagados de Santiago
- Comunas: Las Condes, Vitacura, Lo Barnechea, La Dehesa, Providencia
- Perfil: mensualidad >$300K/alumno, usan SchoolNet/Colegium, apoderados activos en WhatsApp
- Caso de éxito: Colegio del Sagrado Corazón Apoquindo (piloto gratuito)

## Notas pendientes
- (por completar)

## Plan de contratación

### Costos de equipo

| Rol | Base/mes | Comisión | Total estimado/mes (con carga) |
|---|---|---|---|
| Fundador (Pablo) | - | - | $8.000.000 (sueldo objetivo) |
| Vendedor | $800.000-1.000.000 | 12% del primer año por colegio nuevo | ~$3.000.000 promedio |
| IT/Respaldo | $1.500.000-2.000.000 | - | ~$2.500.000 |

**Total equipo completo: $13.500.000/mes**

### Comisión del vendedor (detalle)
- Colegio mediano (800 alumnos): contrato $15.6M/año × 12% = $1.870.000 por colegio cerrado
- Si cierra 2 colegios/mes: base $1M + comisiones $3.7M = $4.7M (meses buenos)
- Promedio mensualizado: ~$3M/mes (incluye meses sin cierre)

### Cuándo contratar

| Hito | Colegios activos | Ingreso/mes | Acción |
|---|---|---|---|
| Solo | 1-4 | $1.3-5.2M | Vender + operar solo |
| +Vendedor | 5 | $6.5M | Contratar vendedor (se paga solo con 1 colegio nuevo) |
| +IT | 8 | $10.4M | Contratar respaldo IT (onboarding + soporte) |
| Equipo completo | 11+ | $14.3M+ | Cubiertos todos los costos con margen |

### Breakeven con equipo completo

| Colegios | Ingreso/mes | Gasto total/mes | Margen libre/mes |
|---|---|---|---|
| 11 | $14.300.000 | $13.500.000 | $800.000 |
| 13 | $16.900.000 | $13.500.000 | $3.400.000 |
| 15 | $19.500.000 | $13.500.000 | $6.000.000 |
| 20 | $26.000.000 | $13.500.000 | $12.500.000 |

### Proyección con equipo (año 2)

Asumiendo vendedor cierra 2-3 colegios/mes:

| Mes (año 2) | Colegios | Ingreso/mes | Profit después de costos |
|---|---|---|---|
| 1 | 12 | $15.600.000 | $2.100.000 |
| 3 | 16 | $20.800.000 | $7.300.000 |
| 6 | 22 | $28.600.000 | $15.100.000 |
| 12 | 34 | $44.200.000 | $30.700.000 |

**Año 2 con equipo: ~$250M ingreso / ~$180M profit**



## Expansión vertical

### Módulos premium (upsell a colegios existentes)

| Módulo | Cobro extra/mes | Descripción |
|---|---|---|
| Alertas de inasistencia | $300-500K | Aviso en tiempo real al apoderado si el hijo no llegó al colegio |
| Reportes de engagement | $200-300K | Dashboard para el colegio: qué apoderados leen, cuáles no responden |
| Canal bidireccional | $500-800K | Apoderado responde en el grupo WA y llega organizado al colegio |
| Recordatorio de pagos | $300-500K | "Tu cuota vence en 3 días" — reduce morosidad |

**Impacto:** con 10 colegios comprando 2 módulos extra → +$6-10M/mes adicionales.

### Otros segmentos educativos

| Segmento | Tamaño (Chile) | Pricing/mes | Adaptación necesaria |
|---|---|---|---|
| Jardines infantiles | 5.000+ | $500-800K | Simplificar (menos fuentes, foco en rutina diaria) |
| Colegios subvencionados | 6.000+ | $300-500K | Precio más bajo, más volumen. Muchos usan Alexia/Syscol |
| Universidades (padres de mechones) | 60+ | $2-5M | Fuentes distintas (portal alumno, emails, calendario académico) |
| Preuniversitarios | 200+ | $500-1M | Resultados de ensayos, horarios, simulacros |

### Expansión geográfica (Latam)

Mismo producto, misma infra. Seguir la base de Colegium/Alexia en cada país.

| País | Colegios particulares | Pricing estimado (USD/mes) | Plataformas dominantes |
|---|---|---|---|
| Colombia | 5.000+ | $500-1.000 | Colegium, Phidias, CiberColegio |
| Perú | 3.000+ | $400-800 | Colegium, Sieweb |
| México | 15.000+ | $600-1.200 | Colegium, Educamos |
| Argentina | 4.000+ | $300-600 | Colegium, Aulica |

**Requisitos para Latam:**
- Adaptar scraping a plataformas locales (Phidias, Sieweb, etc.)
- WhatsApp funciona igual en toda Latam (misma infra)
- Proxy residencial por país (~mismos proveedores)
- Gemini/Claude funciona igual (español neutro)

### Roadmap de expansión

| Fase | Timing | Foco | Ingreso adicional esperado |
|---|---|---|---|
| 1. Módulos premium | Mes 8-12 (año 1) | Alertas + reportes a colegios existentes | +$3-5M/mes |
| 2. Jardines infantiles | Año 2 Q1 | Nuevo segmento Chile, pricing más bajo | +$3-5M/mes |
| 3. Colombia | Año 2 Q2 | Primer país Latam, 5-10 colegios | +$5-10M/mes |
| 4. Subvencionados | Año 2 Q3 | Volumen Chile (requiere precio bajo) | +$5-10M/mes |
| 5. México + Perú | Año 3 | Escala Latam | +$20-50M/mes |


## Data como producto

### Activo principal: canal directo con el apoderado por WhatsApp

Con miles de apoderados conectados vía WhatsApp, el canal es el activo más valioso del negocio — más que la tecnología o los resúmenes. Permite comunicación push directa, personalizada, con tasa de lectura >95%.

### Data extraíble de grupos WA (agregada, anonimizada)

| Data | Ejemplo | Cliente potencial |
|---|---|---|
| Temas más discutidos/mes | "Oct: 40% uniformes, 30% transporte, 20% evaluaciones" | El colegio (anticipar problemas) |
| Sentimiento de apoderados | "Semana 15-jul: sentimiento negativo por cambio horario" | Dirección del colegio |
| Preguntas frecuentes no resueltas | "35% pregunta lo mismo: ¿hora de salida?" | Colegio (mejorar comunicación) |
| Detección de conflictos | "Grupo 3°B: tensión alta, tema bullying" | Convivencia escolar |
| Influenciadores de opinión | "3 apoderados generan 60% de conversaciones" | Dirección (gestión de stakeholders) |
| Necesidades no cubiertas | "Se menciona 'furgón' 50 veces/mes" | Empresas de transporte escolar |
| Efectividad de comunicaciones del colegio | "70% leyó la circular, 30% sigue preguntando" | Comunicaciones del colegio |

### Cierre del loop de comunicación (upsell al colegio)

El colegio hoy manda circulares sin saber si se leyeron ni qué efecto tuvieron. Con nuestra data:
- "El 70% de los apoderados leyó la circular del lunes"
- "En el grupo de 5°A siguen preguntando por la fecha del paseo — la comunicación no fue clara"
- "El cambio de horario generó 45 mensajes negativos en 2 horas — intervenir"

Esto se puede empaquetar como módulo "Analytics de Comunicación Escolar" — $500K-1M extra/mes por colegio.

### Monetización del canal (con cautela)

| Producto | Descripción | Quién paga | Pricing |
|---|---|---|---|
| Ofertas segmentadas | "Feria uniformes sábado" a apoderados de 1°-4° | Empresas de uniforme | $200-500K/campaña |
| Encuestas rápidas | "¿Inscribirías a tu hijo en robótica?" | Empresas de talleres | $300-800K/encuesta |
| Promoción de eventos | "Obra infantil, 20% dcto familias SC" | Productoras | $100-300K/envío |

**⚠️ Riesgo:** si el apoderado siente spam, pierde confianza. Solo con consentimiento explícito y contenido de valor real para la familia.

### Timing
- Módulo Analytics: viable con 10+ colegios (año 1)
- Monetización del canal: viable con 50+ colegios y opt-in del apoderado (año 2-3)
- Venta de data agregada: viable con 100+ colegios (año 3+)


## Módulos premium detallados

### Módulo 1: Canal de comunicación directa + Read Receipts ($1M extra/mes)

**Qué incluye:**
- El colegio envía comunicados urgentes vía nuestro canal WA (95% lectura vs 25% email)
- Reporte de lectura: quién leyó, quién no, por curso
- Alerta: "estos 15 apoderados no leyeron la comunicación del viernes"

**Implementación técnica (pendiente):**
- Agregar listener de `messages.update` en wa_listener.js para detectar read receipts (doble check azul)
- Guardar log por mensaje: {msg_id, destinatario, enviado_at, leido_at}
- Endpoint API para que el colegio vea reportes

**Valor para el colegio:** elimina el problema #1 ("no me avisaron") con evidencia objetiva.

### Módulo 2: Inteligencia de grupos WA ($700K extra/mes)

**Qué incluye:**
- Reporte semanal de clima escolar por curso (sentimiento, temas top, alertas)
- Alertas en tiempo real de conflictos ("12 mensajes negativos sobre tema X en última hora")
- Detección de desinformación ("se dice en grupo que mañana no hay clases — es falso")
- Identificación de preguntas frecuentes no resueltas

**Para quién:**
- Director: visión general, anticipar conflictos
- Convivencia escolar: detección temprana bullying/tensión
- Comunicaciones: qué se entendió mal, qué reforzar
- Profesores jefe: qué se dice de su curso

**Implementación técnica:**
- Análisis semanal con AI (Gemini/Claude) de mensajes agregados por grupo
- Clasificación de sentimiento (positivo/negativo/neutro)
- Extracción de temas recurrentes
- Alertas si sentimiento negativo supera umbral

### Pricing full stack

| Módulo | Cobro/mes |
|---|---|
| Base (resúmenes a apoderados, hasta 500 alumnos) | $1.000.000 |
| Canal de comunicación directa + read receipts | $1.000.000 |
| Inteligencia de grupos WA | $700.000 |
| Alumno extra (sobre 500) | $1.000/alumno |
| **Total colegio mediano (800 alumnos, full)** | **$3.000.000/mes** |

### Proyección con módulos premium

| Colegios (full stack $3M) | Ingreso/mes | Para tu sueldo ($8M) |
|---|---|---|
| 3 | $9.000.000 | ✅ Cubierto |
| 5 | $15.000.000 | + 1 persona |
| 7 | $21.000.000 | + equipo de 3 |
| 10 | $30.000.000 | Escala Latam |
