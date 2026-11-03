"""Mapa de la pobreza por departamento con la ENAHO, unido por código.

Uso:
    uv run .claude/skills/mapeando-enaho/scripts/mapear.py
    uv run .claude/skills/mapeando-enaho/scripts/mapear.py --indicador pobre_extremo

Entra: salidas/personas_<anio>.parquet y recursos/peru_departamental.geojson (en la skill)
Sale:  mapas/pobreza_departamento.png (o pobreza_extrema_departamento.png), 200 dpi

Reglas: une ubigeo[:2] con FIRST_IDDP como texto, nunca por nombre · exige 25 departamentos
con dato · un solo tono de claro a oscuro desde 0 · leyenda con la unidad · Lima (15) y
Callao (07) separados · en 2024, compara con la pobreza oficial por departamento.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SKILL = Path(__file__).resolve().parents[1]
RAIZ = Path(__file__).resolve().parents[4]
GEOJSON = SKILL / "recursos" / "peru_departamental.geojson"
REFERENCIA = {2024: SKILL / "recursos" / "pobreza_departamento_2024.csv"}
TOLERANCIA_PP = 0.1  # la referencia viene redondeada a un decimal
INDICADORES = {"pobre": "Pobreza monetaria", "pobre_extremo": "Pobreza extrema"}


def por_departamento(base: pd.DataFrame, indicador: str) -> pd.DataFrame:
    """Dos cálculos: personas con facpob07 (el del mapa) y el método INEI (hogares, factor07 × mieperho)."""
    x = base[indicador].astype(float)
    per = (x * base["facpob07"]).groupby(base["departamento"]).sum() / base["facpob07"].groupby(base["departamento"]).sum()
    hog = base.drop_duplicates(["conglome", "vivienda", "hogar"])
    w = hog["factor07"] * hog["mieperho"]
    inei = (hog[indicador].astype(float) * w).groupby(hog["departamento"]).sum() / w.groupby(hog["departamento"]).sum()
    return pd.DataFrame({"pct": 100 * per, "pct_inei": 100 * inei}).rename_axis("departamento").reset_index()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--indicador", choices=list(INDICADORES), default="pobre")
    ap.add_argument("--anio", type=int, default=2024)
    args = ap.parse_args()

    ruta = RAIZ / "salidas" / f"personas_{args.anio}.parquet"
    if not ruta.exists():
        sys.exit(f"No existe {ruta.relative_to(RAIZ)}. Usa primero la skill limpiando-enaho.")
    base = pd.read_parquet(ruta)
    tabla = por_departamento(base, args.indicador)

    # Unir por código, como texto de 2 dígitos. Nunca por nombre.
    geo = gpd.read_file(GEOJSON)
    geo["departamento"] = geo["FIRST_IDDP"].astype(str).str.zfill(2)
    tabla["departamento"] = tabla["departamento"].astype(str).str.zfill(2)
    mapa = geo.merge(tabla, on="departamento", how="left", validate="1:1")

    errores = []
    if len(mapa) != 25:
        errores.append(f"El mapa tiene {len(mapa)} departamentos, no 25.")
    sin_dato = mapa.loc[mapa["pct"].isna(), "NOMBDEP"].tolist()
    if sin_dato:
        errores.append(f"Departamentos sin dato (la unión falló): {sin_dato}")
    if not {"07", "15"} <= set(mapa.loc[mapa["pct"].notna(), "departamento"]):
        errores.append("Lima (15) y Callao (07) deben ir separados y con dato.")

    ref_path = REFERENCIA.get(args.anio)
    if ref_path and args.indicador == "pobre":
        ref = pd.read_csv(ref_path, dtype={"ccdd": str})
        comp = mapa.merge(ref, left_on="departamento", right_on="ccdd", how="left")
        dif = (comp["pct_inei"] - comp["pobreza_pct"]).abs()
        malos = comp.loc[dif > TOLERANCIA_PP, ["NOMBDEP", "pct_inei", "pobreza_pct"]]
        if len(malos):
            errores.append("No replica la pobreza oficial por departamento:\n" + malos.round(2).to_string(index=False))
        print(f"Comparación con la cifra oficial: máxima diferencia {dif.max():.2f} pp (método INEI), "
              f"{(comp['pct'] - comp['pobreza_pct']).abs().max():.2f} pp (personas, facpob07).")
    if errores:
        print("MAPA NO GENERADO\n" + "\n".join(errores))
        return 1

    # Dibujar: un solo tono, desde 0, leyenda con la unidad
    vmax = float(np.ceil(mapa["pct"].max() / 10) * 10)
    fig, ax = plt.subplots(figsize=(7, 8))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.06)
    mapa.plot(column="pct", cmap="Reds", vmin=0, vmax=vmax, edgecolor="white", linewidth=0.6, ax=ax,
              legend=True, legend_kwds={"label": "% de personas", "shrink": 0.55, "pad": 0.01})
    for _, fila in mapa.iterrows():
        p = fila.geometry.representative_point()
        oscuro = fila["pct"] > vmax * 0.55
        texto = f"{fila['pct']:.1f}"
        if fila["departamento"] == "07":  # Callao es diminuto: etiqueta afuera, en el mar
            ax.annotate(f"Callao {texto}", xy=(p.x, p.y), xytext=(p.x - 2.2, p.y - 0.3), fontsize=7,
                        arrowprops={"arrowstyle": "-", "lw": 0.5, "color": "#444444"}, ha="right", va="center")
        else:
            ax.text(p.x, p.y, texto, fontsize=7, ha="center", va="center",
                    color="white" if oscuro else "#222222")
    ax.set_axis_off()
    ax.set_title(f"{INDICADORES[args.indicador]} por departamento, Perú {args.anio}",
                 loc="left", fontsize=13, fontweight="bold")
    fig.text(0.02, 0.06, f"Fuente: INEI, ENAHO {args.anio}. % de personas, ponderado con facpob07. "
             "Departamentos unidos por código de ubigeo.", fontsize=7, color="#555555")
    nombre = "pobreza_departamento.png" if args.indicador == "pobre" else "pobreza_extrema_departamento.png"
    destino = RAIZ / "mapas" / nombre
    destino.parent.mkdir(exist_ok=True)
    fig.savefig(destino, dpi=200, bbox_inches="tight")
    plt.close(fig)

    t = mapa[["departamento", "NOMBDEP", "pct", "pct_inei"]].sort_values("pct", ascending=False)
    t.columns = ["ccdd", "departamento", "pct_facpob07", "pct_inei"]
    print(f"{INDICADORES[args.indicador]} por departamento, {args.anio} (% de personas). 25 de 25 con dato.")
    print(t.round(1).to_string(index=False))
    print(f"\nMapa: {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
