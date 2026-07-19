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

