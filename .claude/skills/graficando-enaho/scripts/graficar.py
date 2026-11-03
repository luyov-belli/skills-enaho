"""Grafica la pobreza de la ENAHO con las reglas fijas del proyecto.

Uso:
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --por area
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --por departamento --indicador pobre_extremo

--por: area, sexo, grupo_edad, dominio, departamento
Sale:  figuras/<indicador>_por_<por>_<anio>.png  (200 dpi) y la tabla impresa.

Reglas: pondera con facpob07 · barras desde cero · ordenadas · un solo color ·
valor escrito en cada barra · título con qué y cuándo · fuente al pie.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
COLOR = "#1f4e79"
DOMINIOS = {
    1: "Costa norte", 2: "Costa centro", 3: "Costa sur", 4: "Sierra norte",
    5: "Sierra centro", 6: "Sierra sur", 7: "Selva", 8: "Lima Metropolitana",
}
ORDEN_NATURAL = {"grupo_edad": ["0-13", "14-17", "18-29", "30-44", "45-59", "60+"]}
NOMBRES = {
    "area": "área", "sexo": "sexo", "grupo_edad": "grupo de edad",
    "dominio": "dominio geográfico", "departamento": "departamento",
}
INDICADORES = {"pobre": "Pobreza monetaria", "pobre_extremo": "Pobreza extrema"}


def tabular(base: pd.DataFrame, por: str, indicador: str) -> pd.Series:
    """% de personas, ponderado con facpob07. Nunca cuenta encuestados."""
    g = base["dominio"].map(DOMINIOS) if por == "dominio" else (
        base["departamento_nombre"] if por == "departamento" else base[por])
    xw = (base[indicador].astype(float) * base["facpob07"]).groupby(g).sum()
    w = base["facpob07"].groupby(g).sum()
    s = (100 * xw / w).dropna()
    if por in ORDEN_NATURAL:  # categorías con orden propio se ordenan por ese orden
        return s.reindex([c for c in ORDEN_NATURAL[por] if c in s.index])
    return s.sort_values(ascending=False)


def graficar(s: pd.Series, por: str, indicador: str, anio: int) -> Path:
    horizontal = len(s) > 4
    alto = 0.32 * len(s) + 1.6 if horizontal else 4.5
    fig, ax = plt.subplots(figsize=(8, alto))
    if horizontal:
        s = s.iloc[::-1]  # el mayor arriba
        barras = ax.barh(s.index.astype(str), s.values, color=COLOR)
        ax.set_xlim(0, s.max() * 1.15)
        ax.set_xlabel("% de personas")
        ax.bar_label(barras, fmt="%.1f", padding=3, fontsize=9)
        ax.tick_params(axis="y", length=0)
    else:
        barras = ax.bar(s.index.astype(str), s.values, color=COLOR, width=0.6)
        ax.set_ylim(0, s.max() * 1.18)
        ax.set_ylabel("% de personas")
        ax.bar_label(barras, fmt="%.1f %%", padding=3, fontsize=11)
        ax.tick_params(axis="x", length=0)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.set_title(f"{INDICADORES[indicador]} por {NOMBRES[por]}, Perú {anio}",
                 loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, f"Fuente: INEI, ENAHO {anio}. % de personas, ponderado con facpob07.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    destino = RAIZ / "figuras" / f"{indicador}_por_{por}_{anio}.png"
    destino.parent.mkdir(exist_ok=True)
    fig.savefig(destino, dpi=200)
    plt.close(fig)
    return destino


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--por", choices=list(NOMBRES), required=True)
    ap.add_argument("--indicador", choices=list(INDICADORES), default="pobre")
    ap.add_argument("--anio", type=int, default=2024)
    args = ap.parse_args()

    ruta = RAIZ / "salidas" / f"personas_{args.anio}.parquet"
    if not ruta.exists():
        sys.exit(f"No existe {ruta.relative_to(RAIZ)}. Usa primero la skill limpiando-enaho.")
    base = pd.read_parquet(ruta)
    s = tabular(base, args.por, args.indicador)
    if s.empty or (s < 0).any():
        sys.exit("La tabla salió vacía o con valores negativos; revisa la base.")
    destino = graficar(s, args.por, args.indicador, args.anio)

    print(f"{INDICADORES[args.indicador]} por {NOMBRES[args.por]}, {args.anio} (% de personas, facpob07)")
    print(s.round(1).to_string())
    print(f"\nFigura: {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
