# Referencia de la ENAHO para `limpiando-enaho`

Léelo solo si necesitas una variable que no está en la base limpia, otro módulo u otro año.

## La base limpia: `salidas/personas_<año>.parquet`

Una fila por persona residente habitual. Columnas:

| Columna | Qué es | Origen |
|---|---|---|
| `conglome`, `vivienda`, `hogar`, `codperso` | Llaves, siempre texto con ceros | ambos módulos |
| `ubigeo` | Distrito, texto de 6 dígitos (`010101`) | sumaria |
| `departamento`, `departamento_nombre` | `ubigeo[:2]` y su nombre; Lima (15) y Callao (07) separados | construida |
| `dominio` | 1 Costa norte · 2 Costa centro · 3 Costa sur · 4 Sierra norte · 5 Sierra centro · 6 Sierra sur · 7 Selva · 8 Lima Metropolitana | sumaria |
| `estrato` | 1 a 8; `urbano = estrato <= 5` | sumaria |
| `area` | Urbano / Rural | construida |
| `p203` | Parentesco con el jefe (1 jefe, 2 cónyuge, 3 hijo…) | módulo 02 |
| `sexo`, `edad`, `grupo_edad` | De `p207` (1 hombre, 2 mujer) y `p208a` | módulo 02 |
| `pobreza` | Código: 1 pobre extremo, 2 pobre no extremo, 3 no pobre. **No es un número** | sumaria |
| `pobre`, `pobre_extremo` | `pobreza <= 2` y `pobreza == 1` | construida |
| `facpob07` | Factor de expansión de personas. **Úsalo para toda cifra de personas** | módulo 02 |
| `factor07`, `mieperho` | Factor de hogares y miembros del hogar | sumaria |
| `linea`, `linpe` | Línea de pobreza y de pobreza extrema (S/ por persona al mes) | sumaria |
| `gashog2d`, `inghog2d` | Gasto e ingreso anual del hogar (S/) | sumaria |

## Cómo se calcula cada cifra

- % de personas pobres: `sum(pobre × facpob07) / sum(facpob07)`.
- Cifra oficial del INEI: en la sumaria, `sum((pobreza <= 2) × factor07 × mieperho) / sum(factor07 × mieperho)`. Da 27.58 % en 2024; con personas y `facpob07`, 27.53 %.
- Gasto per cápita mensual: `gashog2d / (12 × mieperho)`, a nivel de hogar.

## Residentes habituales

`(p204 == 1 & p205 == 2) | (p204 == 2 & p206 == 1)`: miembros del hogar que no estuvieron ausentes 30 días o más, y no miembros que estuvieron presentes 30 días o más. En 2024: 108,664 de 117,721 filas.

## Agregar otro módulo

1. Léelo con `pd.read_stata(..., convert_categoricals=False)` y pasa los nombres a minúscula (la columna del año llega como `aÑo`).
2. Llaves como texto: `conglome` 6, `vivienda` 3, `hogar` 2, `codperso` 2 dígitos con ceros.
3. Si es de hogar, une con `on=["conglome", "vivienda", "hogar"], validate="m:1"`; si es de personas, agrega `codperso` y `validate="1:1"`.
4. Comprueba que el número de filas de la base no cambie.

Módulos frecuentes (zip `<código>-Modulo<NN>.zip`): 01 vivienda y hogar · 03 educación · 04 salud · 05 empleo e ingresos · 34 sumaria · 37 programas sociales.

## Otros años

`limpiar.py` solo trae fijados el código y las cifras oficiales de 2024 (código 966). Para otro año pasa `--codigo` con el código del portal de microdatos del INEI (búscalo ahí, no lo adivines); el script validará la estructura, pero no la cifra oficial, y lo dirá en `validacion.txt`.

## Seis trampas

1. Ceros a la izquierda: `015009`, `010101`. Como número, la unión falla.
2. Nombres rotos: `aÑo` → `anio`.
3. No todos son residentes: filtra siempre.
4. Uniones que duplican: siempre `validate=`.
5. Encuestas no son personas: siempre pondera.
6. `pobreza` es un código: nunca un promedio.
