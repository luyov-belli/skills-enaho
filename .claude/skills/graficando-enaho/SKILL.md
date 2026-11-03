---
name: graficando-enaho
description: Hace gráficos de barras de la pobreza monetaria o extrema del Perú con la ENAHO del INEI, por área urbana y rural, sexo, grupo de edad, dominio o departamento, siempre ponderados y con las mismas reglas de diseño. Úsala cuando pidan graficar, comparar o visualizar la pobreza de la ENAHO, o un gráfico o figura con datos de la ENAHO.
argument-hint: "[area|sexo|grupo_edad|dominio|departamento]"
allowed-tools: Bash(uv run:*), Read
---

# Graficar la ENAHO

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y vuelve aquí cuando su validación diga `RESULTADO: OK`.
2. Elige `--por` según el pedido (o `$0` si lo llamaron a mano): urbano/rural → `area`; hombres/mujeres → `sexo`; edad → `grupo_edad`; costa/sierra/selva o Lima Metropolitana → `dominio`; regiones → `departamento`. Para pobreza extrema agrega `--indicador pobre_extremo`. Si piden varios cortes, corre el script una vez por cada uno.
3. Corre exactamente:
   `uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --por <corte> [--indicador pobre_extremo]`
4. Responde con la ruta de la figura en `figuras/` y las cifras que imprime el script, con un decimal y en % de personas.

Si el pedido no cabe en el script (otra variable, otro tipo de gráfico), escribe el código tú, pero cumple las mismas reglas:

- Pondera siempre con `facpob07`; nunca cuentes encuestados.
- Barras que empiezan en cero, ordenadas de mayor a menor (o en su orden natural, como la edad).
- Un solo color; el valor escrito en cada barra.
- El título dice qué se mide, dónde y cuándo.
- Nota al pie: «Fuente: INEI, ENAHO 2024».
- PNG a 200 dpi en `figuras/`.
- Nada de pasteles, 3D ni ejes truncados.
