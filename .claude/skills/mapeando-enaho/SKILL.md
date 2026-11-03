---
name: mapeando-enaho
description: Hace el mapa coroplético de la pobreza monetaria o extrema del Perú por departamento con la ENAHO del INEI, uniendo por código de ubigeo y validando los 25 departamentos contra la cifra oficial. Úsala cuando pidan un mapa, mapear o ver en el territorio la pobreza por departamento o región del Perú con la ENAHO.
argument-hint: "[pobre|pobre_extremo]"
allowed-tools: Bash(uv run:*), Read
---

# Mapear la ENAHO

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y vuelve aquí cuando su validación diga `RESULTADO: OK`.
2. Corre exactamente:
   `uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py`
   Para pobreza extrema (o si `$0` es `pobre_extremo`), agrega `--indicador pobre_extremo`.
3. Si imprime `MAPA NO GENERADO`, detente y muestra el error. No lo arregles uniendo por nombre ni rellenando departamentos.
4. Responde con la ruta del mapa en `mapas/`, los tres departamentos con más pobreza y los tres con menos, con un decimal.

Los límites de los 25 departamentos están en `recursos/peru_departamental.geojson` y la pobreza oficial 2024 por departamento en `recursos/pobreza_departamento_2024.csv`. No bajes otro mapa.

Si te piden un mapa distinto y escribes el código tú, cumple las mismas reglas:

- Une `ubigeo[:2]` con `FIRST_IDDP`, ambos como texto de 2 dígitos. Nunca por nombre: «APURIMAC» no es «Apurímac».
- Exige 25 departamentos y ninguno sin dato; Lima (15) y Callao (07) van separados.
- Pondera con `facpob07`.
- Un solo tono de claro a oscuro, que empiece en 0; nunca arcoíris.
- Leyenda con la unidad («% de personas»), título con qué y cuándo, «Fuente: INEI, ENAHO 2024» al pie.
- PNG a 200 dpi en `mapas/`.
