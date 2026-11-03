"""Resume las corridas de evaluar.sh en evaluacion/automatico.md.

Lee evaluacion/corridas/<caso>/log.jsonl (stream-json de `claude -p`) y anota qué skills se
activaron, en qué orden, qué comandos corrió, qué archivos dejó y la respuesta final.
Solo usa la biblioteca estándar: python3 evaluacion/resumir.py
"""

from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CORRIDAS = AQUI / "corridas"
PEDIDOS = {
    "cusco": ("¿Cuál fue la pobreza en Cusco en 2024?", "limpiando", "18.5 %"),
    "urbano": ("Grafica la pobreza urbana y rural", "graficando (+ limpiando)", "24.8 % y 39.3 %"),
    "mapa": ("Haz un mapa de la pobreza por departamento", "mapeando (+ limpiando)", "Cajamarca 45.0 %, Ica 6.0 %"),
}


def leer_log(ruta: Path) -> dict:
    skills, comandos, final, costo, turnos, segundos = [], [], "", None, None, None
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []) or []:
                if b.get("type") != "tool_use":
                    continue
                entrada = b.get("input", {}) or {}
                if b.get("name") == "Skill":
                    skills.append(str(entrada.get("skill") or entrada.get("command") or entrada))
                elif b.get("name") == "Bash":
                    comandos.append(str(entrada.get("command", ""))[:160])
        elif ev.get("type") == "result":
            final = ev.get("result") or ""
            costo, turnos = ev.get("total_cost_usd"), ev.get("num_turns")
            segundos = (ev.get("duration_ms") or 0) / 1000
    return {"skills": skills, "comandos": comandos, "final": final,
            "costo": costo, "turnos": turnos, "segundos": segundos}


def main() -> None:
    if not CORRIDAS.exists():
        print("No hay corridas. Ejecuta primero: bash evaluacion/evaluar.sh")
        return
    filas, detalle = [], []
    for clave, (pedido, esperadas, esperado) in PEDIDOS.items():
        for modo in ("con", "sin"):
            caso = CORRIDAS / f"{clave}_{modo}"
            if not (caso / "log.jsonl").exists():
                continue
            r = leer_log(caso / "log.jsonl")
            archivos = sorted(str(p.relative_to(caso)) for p in caso.rglob("*.png"))
            skills = " → ".join(r["skills"]) or "ninguna"
            extra = f"{r['segundos']:.0f} s · {r['turnos']} turnos" if r["segundos"] else ""
            if r["costo"] is not None:
                extra += f" · US$ {r['costo']:.2f}"
            filas.append(f"| {pedido} | {modo} | {skills} | {esperadas} | {esperado} | "
                         f"{', '.join(archivos) or '—'} | {extra} |")
            detalle += [f"### {pedido} · {modo} skills", "", f"Skills: {skills}", "",
                        "Comandos:", "", *([f"- `{c}`" for c in r["comandos"]] or ["- ninguno"]), "",
                        "Respuesta final:", "", *[f"> {l}" for l in r["final"].strip().splitlines()], ""]
    salida = AQUI / "automatico.md"
    salida.write_text("\n".join([
        "# Evaluación automática", "",
        "Generado por `evaluacion/resumir.py` a partir de `evaluacion/corridas/`. "
        "Las conclusiones van en `evaluacion.md`.", "",
        "| Pedido | Skills | Se activaron | Deberían | Debe salir | Figuras | Corrida |",
        "|---|---|---|---|---|---|---|", *filas, "", "## Detalle", "", *detalle,
    ]) + "\n", encoding="utf-8")
    print(f"Resumen en {salida.relative_to(AQUI.parent)}")
    print("\n".join(filas))


if __name__ == "__main__":
    main()
