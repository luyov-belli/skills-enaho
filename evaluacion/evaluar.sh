#!/usr/bin/env bash
# Corre los tres pedidos del proyecto con y sin skills usando `claude -p`.
#
#   bash evaluacion/evaluar.sh            # los 6 casos
#   bash evaluacion/evaluar.sh cusco      # solo un pedido (cusco | urbano | mapa)
#
# Cada caso corre en una carpeta temporal limpia, con datos/ enlazado y sin salidas/,
# para que la corrida sin skills no reutilice la base que dejó la corrida con skills
# y para que la corrida con skills tenga que encadenar limpiando-enaho.
#   con skills: copia .claude/, pyproject.toml y uv.lock
#   sin skills: copia solo pyproject.toml y uv.lock, y además --disallowedTools Skill
# Resultados en evaluacion/corridas/<pedido>_<con|sin>/ y resumen en evaluacion/automatico.md

set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
CORRIDAS="$RAIZ/evaluacion/corridas"

# Compatible con el bash 3.2 de macOS: sin arreglos asociativos
pedido_de() {
  case "$1" in
    cusco)  echo "¿Cuál fue la pobreza en Cusco en 2024?" ;;
    urbano) echo "Grafica la pobreza urbana y rural" ;;
    mapa)   echo "Haz un mapa de la pobreza por departamento" ;;
    *)      echo "Pedido desconocido: $1 (usa cusco, urbano o mapa)" >&2; exit 1 ;;
  esac
}
ORDEN=(cusco urbano mapa)
[[ $# -gt 0 ]] && ORDEN=("$@")

PERMITIDAS=(
  "Bash(uv run:*)" "Bash(uv add:*)" "Bash(python:*)" "Bash(python3:*)"
  "Bash(ls:*)" "Bash(mkdir:*)" "Bash(unzip:*)" "Bash(head:*)" "Bash(cat:*)"
  Read Write Edit Glob Grep Skill
)

command -v claude >/dev/null || { echo "Falta Claude Code (claude) en el PATH."; exit 1; }
ls "$RAIZ"/datos/*-Modulo34.zip "$RAIZ"/datos/*-Modulo02.zip >/dev/null 2>&1 \
  || { echo "Faltan los zip de la ENAHO en datos/. Mira el README."; exit 1; }

for clave in "${ORDEN[@]}"; do
  pedido="$(pedido_de "$clave")"
  for modo in con sin; do
    caso="${clave}_${modo}"
    tmp="$(mktemp -d)"
    cp "$RAIZ/pyproject.toml" "$RAIZ/uv.lock" "$tmp/"
    ln -s "$RAIZ/datos" "$tmp/datos"
    extra=()
    if [[ $modo == con ]]; then
      cp -R "$RAIZ/.claude" "$tmp/.claude"
    else
      extra=(--disallowedTools Skill)
    fi

    echo "▶ $caso: $pedido"
    inicio=$(date +%s)
    ( cd "$tmp" && claude -p "$pedido" --output-format stream-json --verbose \
        ${extra[@]+"${extra[@]}"} --allowedTools "${PERMITIDAS[@]}" ) > "$tmp/log.jsonl" 2> "$tmp/stderr.txt" || true
    echo "  terminó en $(( $(date +%s) - inicio )) s"

    destino="$CORRIDAS/$caso"
    rm -rf "$destino" && mkdir -p "$destino"
    cp "$tmp/log.jsonl" "$tmp/stderr.txt" "$destino/"
    for d in figuras mapas; do [[ -d "$tmp/$d" ]] && cp -R "$tmp/$d" "$destino/"; done
    [[ -f "$tmp/salidas/validacion.txt" ]] && cp "$tmp/salidas/validacion.txt" "$destino/"
    # el código que escribió Claude por su cuenta (sobre todo sin skills)
    find "$tmp" -maxdepth 2 -name "*.py" -not -path "*/.claude/*" -not -path "*/.venv/*" \
      -exec cp {} "$destino/" \; 2>/dev/null || true
    rm -rf "$tmp"
  done
done

python3 "$RAIZ/evaluacion/resumir.py"
