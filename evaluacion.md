# Evaluación: con y sin skills

Tres pedidos corridos con `claude -p`, cada uno dos veces: con las tres skills y sin ninguna
(`--disallowedTools Skill`, en una carpeta sin `.claude/`). Cada corrida empieza sin `salidas/`,
así que con skills los pedidos de gráfico y mapa tienen que encadenar `limpiando-enaho`.

Para repetirla: `bash evaluacion/evaluar.sh`. El detalle (skills activadas, comandos y respuesta
final de cada corrida) queda en [`evaluacion/automatico.md`](evaluacion/automatico.md) y las
figuras en `evaluacion/corridas/`.

| Pedido | Skills | Se activaron | Cifra | ¿Ponderó? | La figura | Debe salir |
|---|---|---|---|---|---|---|
| ¿Cuál fue la pobreza en Cusco en 2024? | con | | | | — | 18.5 % |
| | sin | — | | | — | 18.5 % |
| Grafica la pobreza urbana y rural | con | | | | | 24.8 % y 39.3 % |
| | sin | — | | | | 24.8 % y 39.3 % |
| Haz un mapa de la pobreza por departamento | con | | | | | Cajamarca 45.0 %, Ica 6.0 % |
| | sin | — | | | | Cajamarca 45.0 %, Ica 6.0 % |

## Qué cambió con las skills

_(completar después de correr la evaluación)_
