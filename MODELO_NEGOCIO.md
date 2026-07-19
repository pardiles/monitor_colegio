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


## Plan Comercial

### Producto: Monitor Colegio
Servicio B2B para colegios particulares. Resúmenes diarios automáticos por WhatsApp para apoderados + inteligencia de comunicación para la dirección.

### Paquetes

| Paquete | Incluye | Precio/mes |
|---|---|---|
| **Básico** | Resúmenes AM/PM por WA, calendario, fuentes del colegio. Hasta 500 alumnos. | $1.000.000 + $1.000/alumno extra |
| **Full** | Básico + canal directo del colegio por WA + read receipts + reportes de lectura + inteligencia de grupos WA (sentimiento, alertas, insights semanales) | $2.700.000 + $1.000/alumno extra |

### Condiciones
- Primer mes gratis (prueba)
- Contrato mínimo 12 meses
- Setup incluido
- Precios en UF (ajuste IPC automático)

### Target
- Colegios particulares pagados de Santiago
- Comunas: Las Condes, Vitacura, Lo Barnechea, La Dehesa, Providencia, Ñuñoa
- Mensualidad alumno >$300K
- Usan SchoolNet/Colegium u otra plataforma digital
- 300-1500 alumnos

### Propuesta de valor por audiencia

**Para el Director:**
- "Visibilidad total de lo que pasa en los grupos de apoderados"
- "Reducción de conflictos por desinformación"
- "Diferenciación vs otros colegios (innovación)"

**Para Comunicaciones:**
- "95% de lectura por WA vs 25% por email"
- "Saber exactamente quién no leyó una comunicación"
- "Canal directo al apoderado sin depender de email ni app"

**Para los Apoderados (el usuario final):**
- "Nunca más te pierdes una prueba, reunión o actividad"
- "Todo resumido en 1 mensaje de WhatsApp, 2 veces al día"
- "5 minutos de setup, 0 esfuerzo después"

### Plan de ventas primer año

| Etapa | Mes | Acción | Meta |
|---|---|---|---|
| Piloto | 1 | Sagrado Corazón como caso de éxito (gratis) | Testimonial + métricas |
| Lanzamiento | 2-3 | Contactar 10 colegios similares. Ofrecer mes gratis. | 2-3 colegios en prueba |
| Tracción | 4-6 | Referidos + networking directo. Cerrar contratos anuales. | 5 colegios pagando |
| Crecimiento | 7-9 | Contratar vendedor. Módulos premium. | 8-10 colegios |
| Escala | 10-12 | Equipo completo. Segundo segmento (jardines/subvencionados). | 12+ colegios |

### Proyección financiera primer año (paquete Básico $1.3M/colegio mediano)

| Mes | Colegios | Ingreso | Costos (infra + equipo) | Profit |
|---|---|---|---|---|
| 1-3 | 0→2 | $3.900.000 acum | $57.000 | $3.843.000 |
| 4-6 | 3→5 | $15.600.000 acum | $285.000 | $15.315.000 |
| 7-9 (+ vendedor) | 6→8 | $27.300.000 acum | $9.500.000 | $17.800.000 |
| 10-12 (+ IT) | 9→10 | $38.350.000 acum | $17.000.000 | $21.350.000 |
| **Total año 1** | **10** | **$85.150.000** | **$26.842.000** | **$58.308.000** |

### Proyección año 2 (con equipo, módulos premium, 2-3 colegios/mes nuevos)

| Trimestre | Colegios | Ingreso acumulado trimestre | 
|---|---|---|
| Q1 | 13-16 | $50-60M |
| Q2 | 17-22 | $70-85M |
| Q3 | 23-28 | $90-110M |
| Q4 | 29-34 | $110-135M |
| **Total año 2** | **34** | **$320-390M** |

### Métricas clave (KPIs)

| Métrica | Meta año 1 | Meta año 2 |
|---|---|---|
| Colegios activos | 10 | 34 |
| Tasa de adopción (familias registradas/total) | >50% | >65% |
| Churn anual | <10% | <10% |
| NPS apoderados | >60 | >70 |
| Ingreso mensual recurrente (MRR) | $13M | $45M |

### Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Colegium copia la feature | Media | Velocidad de ejecución + módulos que ellos no pueden hacer (WA bidireccional) |
| Meta banea cuentas WA | Baja | Proxy residencial + sesiones estables |
| Baja adopción de apoderados | Media | Onboarding ultra simple (5 min) + valor inmediato desde día 1 |
| Colegio no renueva | Baja | Contrato anual + demostrar ROI con métricas de lectura |
| Privacidad/datos personales | Media | Solo lectura de grupos que el apoderado elige. Sin acceso a privados. Cumplimiento RGPD/ley chilena. |


## Análisis de Competencia

### Competidores directos (comunicación escolar Chile)

| Competidor | Qué hace | Precio | Limitación vs nosotros |
|---|---|---|---|
| **Colegium/SchoolNet** | Plataforma completa: notas, asistencia, pagos, comunicaciones | $500K-1.5M/mes | Pull (apoderado tiene que abrir la app). No tiene AI ni WA. No resume. |
| **Napsis/SND** | Gestión escolar (2000+ colegios en Chile). 200 funcionalidades. | Similar a Colegium | Misma limitación: pull, no push. Sin WhatsApp. |
| **Alexia (Educaria)** | Plataforma escolar para subvencionados | $200-500K/mes | No tiene comunicación directa a apoderados por WA |
| **Radar Escolar** (adquirido por Colegium 2022) | Sincronizaba datos entre plataformas | Integrado en Colegium | Ya no existe como producto independiente |

### Competidores internacionales (comunicación escolar)

| Competidor | Qué hace | Mercado | Diferencia vs nosotros |
|---|---|---|---|
| **ParentSquare** | Comunicación escolar: alertas, mensajes, formularios, pagos | USA (premio EdTech 2025) | No usa WA, no tiene AI para resumir. Solo en inglés. |
| **TalkingPoints** | Comunicación familia-escuela con traducción AI | USA (9M+ usuarios) | Foco en traducción multiidioma. No resume fuentes múltiples. |
| **ClassDojo** | Red social colegio-familia (comportamiento, fotos, mensajes) | Global (gratis) | No tiene AI, no resume, no integra WA. Es una app más que el papá tiene que abrir. |
| **Remind** | Mensajería para colegios (SMS/app) | USA | Solo envía, no lee ni resume. Sin inteligencia. |
| **Bloomz** | Comunicación + voluntariado + pagos | USA | App propia (no WA). Pull, no push. |

### Competidores AI + Educación

| Competidor | Qué hace | Diferencia vs nosotros |
|---|---|---|
| **MagicSchool AI** | Genera newsletters y comunicaciones para profesores | Ayuda al PROFESOR a escribir, no resume para el APODERADO |
| **Brisk Teaching** | AI para crear contenido educativo | Para profesores, no para familias |
| **TeacherMatic** | Templates de comunicación con AI | Generación de contenido, no consumo/resumen |

### Nuestra diferenciación

**Nadie en el mercado hace exactamente esto:**

| Característica | Nosotros | Competencia |
|---|---|---|
| Canal: WhatsApp (95% lectura) | ✅ | ❌ (todos usan app propia o email) |
| Resume MÚLTIPLES fuentes (WA + email + plataforma + web) | ✅ | ❌ (cada uno solo muestra su propia data) |
| AI genera resumen personalizado por familia | ✅ | ❌ |
| Push 2x/día sin esfuerzo del apoderado | ✅ | ❌ (todos son pull: "abre la app") |
| Lee grupos WA del colegio | ✅ | ❌ (ninguno puede hacer esto) |
| Inteligencia de grupos (sentimiento, alertas) | ✅ | ❌ |
| Read receipts por apoderado | ✅ | Parcial (email open rate solamente) |

### Moat (barrera de entrada)

| Barrera | Fortaleza | Duración |
|---|---|---|
| Integración con WhatsApp (Baileys) | Media | Replicable en 2-3 meses por equipo técnico |
| Prompt engineering + calendar extraction | Baja | Cualquiera con Claude/GPT puede hacerlo |
| Red de colegios + contratos anuales | **Alta** | Lock-in real: cuesta cambiar una vez implementado |
| Data acumulada de grupos WA | **Alta** | Años de histórico = ventaja irreplicable |
| Relación con directores | **Alta** | Confianza se construye con tiempo |

**Conclusión:** la barrera técnica es baja pero la barrera comercial es alta. El que llega primero a un colegio y funciona bien, se queda. El costo de cambio para el colegio es alto (re-vincular 500 WhatsApps).
