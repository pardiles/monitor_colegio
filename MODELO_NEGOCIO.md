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
