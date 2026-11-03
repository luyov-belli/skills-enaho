---
name: limpiando-enaho
description: Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO del INEI y arma una base de personas residentes habituales con pobreza monetaria y factor de expansión, validada contra la cifra oficial. Úsala cuando pidan limpiar, unir o analizar la ENAHO, o calcular la pobreza o pobreza extrema del Perú por departamento, región, área urbana o rural, sexo o edad.
argument-hint: "[año]"
allowed-tools: Bash(uv run:*), Read
---

# Limpiar la ENAHO

La limpieza no se improvisa: la hace siempre el mismo script. No escribas tu propio código para leer, filtrar o unir los módulos.

1. Usa el año de `$0`; si está vacío, usa 2024. El código INEI de 2024 es 966.
2. Si `salidas/validacion.txt` ya dice `RESULTADO: OK` para ese año y existe `salidas/personas_<año>.parquet`, salta al paso 5.
3. Corre exactamente:
   `uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py --anio <año>`
   Si termina con `FALTAN DATOS`, detente y pide al usuario bajar los zip con los links que imprime y guardarlos en `datos/` (sin descomprimir). No los busques ni los bajes de otra fuente.
4. Lee `salidas/validacion.txt`. Si dice `RESULTADO: FALLA`, detente: muestra al usuario los chequeos marcados con `X` y no respondas con cifras.
5. Para responder, tabula con el script de consulta, que pondera con `facpob07`:
   `uv run ${CLAUDE_SKILL_DIR}/scripts/consultar.py --por <nacional|departamento|area|sexo|grupo_edad|dominio> [--indicador pobre_extremo]`
6. Responde con la cifra en % de personas, con un decimal, y di que viene de la ENAHO del INEI ponderada con `facpob07`. Si el usuario compara con la cifra oficial publicada por el INEI, aclara que el INEI la calcula con la sumaria (`factor07 × mieperho`) y que puede diferir en décimas.
7. Antes de usar una variable que no está en la base, o un módulo distinto del 34 y 02, lee [reference.md](reference.md).

Nunca: promedies el código `pobreza`, cuentes encuestados sin ponderar, conviertas `ubigeo` o las llaves a número, ni uses a quienes no son residentes habituales.
