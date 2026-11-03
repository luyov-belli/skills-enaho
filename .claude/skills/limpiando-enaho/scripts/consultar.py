"""Tabula la pobreza ponderada con facpob07 desde la base limpia.

Uso:
    uv run .claude/skills/limpiando-enaho/scripts/consultar.py --por departamento
    uv run .claude/skills/limpiando-enaho/scripts/consultar.py --por area --indicador pobre_extremo
    uv run .claude/skills/limpiando-enaho/scripts/consultar.py            # nacional

--por: nacional, departamento, area, sexo, grupo_edad, dominio
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
GRUPOS = ["nacional", "departamento", "area", "sexo", "grupo_edad", "dominio"]
DOMINIOS = {
    1: "Costa norte", 2: "Costa centro", 3: "Costa sur", 4: "Sierra norte",
    5: "Sierra centro", 6: "Sierra sur", 7: "Selva", 8: "Lima Metropolitana",
}


def tabular(base: pd.DataFrame, por: str, indicador: str) -> pd.DataFrame:
    df = base.assign(_w=base["facpob07"], _xw=base[indicador].astype(float) * base["facpob07"])
    if por == "nacional":
        df["_g"] = "Perú"
    elif por == "departamento":
        df["_g"] = df["departamento"] + " " + df["departamento_nombre"]
    elif por == "dominio":
        df["_g"] = df["dominio"].map(DOMINIOS)
    else:
        df["_g"] = df[por]
    t = df.groupby("_g", observed=True).agg(xw=("_xw", "sum"), w=("_w", "sum"), n=("_w", "size"))
    t["pct"] = 100 * t["xw"] / t["w"]
    t = t.rename_axis(por).reset_index()[[por, "pct", "w", "n"]]
    return t.rename(columns={"pct": f"{indicador}_pct", "w": "poblacion", "n": "n_encuestados"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--por", choices=GRUPOS, default="nacional")
    ap.add_argument("--indicador", choices=["pobre", "pobre_extremo"], default="pobre")
    ap.add_argument("--anio", type=int, default=2024)
    args = ap.parse_args()

    ruta = RAIZ / "salidas" / f"personas_{args.anio}.parquet"
    if not ruta.exists():
        sys.exit(f"No existe {ruta.relative_to(RAIZ)}. Corre primero la skill limpiando-enaho (limpiar.py).")
    t = tabular(pd.read_parquet(ruta), args.por, args.indicador)
    t = t.sort_values(t.columns[0] if args.por == "departamento" else f"{args.indicador}_pct", ascending=args.por == "departamento")
    print(f"ENAHO {args.anio} · % de personas · ponderado con facpob07 · {args.indicador} por {args.por}")
    print(t.to_string(index=False, formatters={
        f"{args.indicador}_pct": "{:.1f}".format, "poblacion": "{:,.0f}".format, "n_encuestados": "{:,}".format,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
