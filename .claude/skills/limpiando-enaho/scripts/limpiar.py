"""Limpia la ENAHO del INEI y arma una base de personas residentes habituales.

Uso (desde cualquier carpeta del repo):
    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024

Entra:  datos/<codigo>-Modulo34.zip (sumaria) y datos/<codigo>-Modulo02.zip (miembros),
        en versión STATA (.dta) o CSV, o sus carpetas ya descomprimidas.
Sale:   salidas/personas_<anio>.parquet y salidas/validacion.txt

El pipeline es siempre el mismo, en este orden:
    1 leer  2 normalizar  3 filtrar  4 unir  5 construir  6 validar  7 guardar
Si la validación falla, se escribe validacion.txt con el detalle, NO se guarda la base
y el script termina con código 1.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]  # .claude/skills/<skill>/scripts/limpiar.py
DATOS = RAIZ / "datos"
SALIDAS = RAIZ / "salidas"

# Código de la ENAHO anual en el portal de microdatos del INEI
CODIGOS = {2024: 966}

# Cifras oficiales para validar. Solo están fijadas para 2024.
OFICIAL = {
    2024: {
        "pobreza": 27.6,          # % de personas, INEI
        "pobreza_extrema": 5.5,
        "hogares": 33_691,
        "filas_modulo02": 117_721,
        "residentes": 108_664,
    }
}
TOLERANCIA_PP = 0.1  # puntos porcentuales

# Llaves con su ancho: siempre texto, con ceros a la izquierda
ANCHOS = {"conglome": 6, "vivienda": 3, "hogar": 2, "codperso": 2, "ubigeo": 6}
LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES_HOGAR + ["codperso"]

COLS_SUMARIA = LLAVES_HOGAR + [
    "ubigeo", "dominio", "estrato", "pobreza", "mieperho", "factor07",
    "linea", "linpe", "gashog2d", "inghog2d",
]
COLS_MIEMBROS = LLAVES_PERSONA + ["p203", "p204", "p205", "p206", "p207", "p208a", "facpob07"]
OBLIGATORIAS_SUMARIA = LLAVES_HOGAR + ["ubigeo", "estrato", "pobreza", "mieperho", "factor07"]
OBLIGATORIAS_MIEMBROS = LLAVES_PERSONA + ["p204", "p205", "p206", "p207", "p208a", "facpob07"]

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
    "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
    "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
    "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}


# ---------------------------------------------------------------- 1. Leer
def ubicar(codigo: int, modulo: str, patron: str) -> Path:
    """Devuelve el archivo del módulo (.dta o .csv), descomprimiendo el zip de datos/ si hace falta.

    El INEI publica cada módulo en STATA (.dta) y en CSV; se acepta cualquiera y se prefiere .dta.
    Se ignoran variantes como la sumaria de 12 grupos de gasto (-12g).
    """
    zip_ = DATOS / f"{codigo}-Modulo{modulo}.zip"

    def buscar() -> list[Path]:
        if not DATOS.exists():
            return []
        return sorted(
            (p for p in DATOS.rglob("*")
             if p.suffix.lower() in (".dta", ".csv") and patron in p.stem.lower() and "12g" not in p.stem.lower()),
            key=lambda p: (p.suffix.lower() != ".dta", len(p.name)),
        )

    candidatos = buscar()
    if not candidatos and zip_.exists():
        with zipfile.ZipFile(zip_) as z:
            z.extractall(DATOS / zip_.stem if not z.namelist()[0].startswith(zip_.stem) else DATOS)
        candidatos = buscar()
    if not candidatos:
        sys.exit(
            f"FALTAN DATOS: no encuentro {zip_.relative_to(RAIZ)} o no trae un .dta/.csv con '{patron}'.\n"
            f"Bájalo desde el navegador y guárdalo, sin descomprimir, en datos/:\n"
            f"  https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{codigo}-Modulo{modulo}.zip"
        )
    return candidatos[0]


def leer(ruta: Path, columnas: list[str]) -> pd.DataFrame:
    """Lee el módulo. Las llaves siempre como texto; el resto de columnas útiles, como número."""
    if ruta.suffix.lower() == ".dta":
        # convert_categoricals=False: nos quedamos con los códigos, no con las etiquetas
        return pd.read_stata(ruta, convert_categoricals=False, preserve_dtypes=False)
    # CSV del INEI: Latin-1, separador , o ; y celdas vacías como " "
    with open(ruta, encoding="latin-1") as f:
        sep = ";" if f.readline().count(";") > 0 else ","
    df = pd.read_csv(ruta, sep=sep, encoding="latin-1", dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower() for c in df.columns]
    for c in columnas:
        if c in df.columns and c not in ANCHOS:
            df[c] = pd.to_numeric(df[c].str.strip().replace("", None), errors="coerce")
    return df


# ----------------------------------------------------------- 2. Normalizar
def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas en minúscula y sin tildes; la del año ('aÑo') pasa a 'anio'."""
    def limpio(c: str) -> str:
        c = c.strip().lower().replace("ñ", "ni")
        return unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode()
    df = df.rename(columns={c: limpio(c) for c in df.columns})
    for col, ancho in ANCHOS.items():
        if col in df.columns:
            df[col] = como_texto(df[col], ancho)
    return df


def como_texto(s: pd.Series, ancho: int) -> pd.Series:
    """Llaves como texto con ceros a la izquierda, vengan como texto o como número."""
    if pd.api.types.is_numeric_dtype(s):
        s = s.astype("Int64").astype("string")
    return s.astype("string").str.strip().str.zfill(ancho)


def exigir(df: pd.DataFrame, cols: list[str], nombre: str) -> None:
    faltan = [c for c in cols if c not in df.columns]
    if faltan:
        sys.exit(f"Al módulo {nombre} le faltan columnas: {faltan}")


# ---------------------------------------------------------- 5. Construir
def construir(base: pd.DataFrame, anio: int) -> pd.DataFrame:
    base = base.copy()
    base["anio"] = anio
    base["departamento"] = base["ubigeo"].str[:2]
    base["departamento_nombre"] = base["departamento"].map(DEPARTAMENTOS)
    base["urbano"] = base["estrato"] <= 5
    base["area"] = np.where(base["urbano"], "Urbano", "Rural")
    base["sexo"] = base["p207"].map({1: "Hombre", 2: "Mujer"})
    base["edad"] = base["p208a"]
    base["grupo_edad"] = pd.cut(
        base["edad"], bins=[-1, 13, 17, 29, 44, 59, 200],
        labels=["0-13", "14-17", "18-29", "30-44", "45-59", "60+"],
    ).astype("string")
    base["pobre"] = base["pobreza"] <= 2           # código: 1 extremo, 2 no extremo, 3 no pobre
    base["pobre_extremo"] = base["pobreza"] == 1
    orden = ["anio"] + LLAVES_PERSONA + [
        "ubigeo", "departamento", "departamento_nombre", "dominio", "estrato", "urbano", "area",
        "p203", "sexo", "edad", "grupo_edad", "pobreza", "pobre", "pobre_extremo",
        "facpob07", "factor07", "mieperho", "linea", "linpe", "gashog2d", "inghog2d",
    ]
    return base[[c for c in orden if c in base.columns]]


def pct(x: pd.Series, w: pd.Series) -> float:
    """Porcentaje ponderado; ignora filas sin peso."""
    m = w.notna()
    return float(100 * np.average(x[m].astype(float), weights=w[m]))


# ----------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--codigo", type=int, help="Código INEI de la encuesta (2024 = 966)")
    args = ap.parse_args()
    anio = args.anio
    codigo = args.codigo or CODIGOS.get(anio)
    if codigo is None:
        sys.exit(f"No conozco el código INEI de {anio}. Pásalo con --codigo.")

    # 1. Leer  ·  2. Normalizar
    sumaria = normalizar(leer(ubicar(codigo, "34", f"sumaria-{anio}"), COLS_SUMARIA))
    miembros = normalizar(leer(ubicar(codigo, "02", f"-{anio}-200"), COLS_MIEMBROS))
    exigir(sumaria, OBLIGATORIAS_SUMARIA, "34 (sumaria)")
    exigir(miembros, OBLIGATORIAS_MIEMBROS, "02 (miembros)")
    sumaria = sumaria[[c for c in COLS_SUMARIA if c in sumaria.columns]]
    filas_modulo02 = len(miembros)
    miembros = miembros[[c for c in COLS_MIEMBROS if c in miembros.columns]]

    # 3. Filtrar: residentes habituales (definición INEI)
    #    miembros no ausentes 30+ días, o no miembros presentes 30+ días
    residente = ((miembros["p204"] == 1) & (miembros["p205"] == 2)) | (
        (miembros["p204"] == 2) & (miembros["p206"] == 1)
    )
    personas = miembros.loc[residente].copy()

    # 4. Unir: muchas personas a un hogar; si no es m:1, pandas falla en vez de duplicar
    base = personas.merge(sumaria, on=LLAVES_HOGAR, how="left", validate="m:1", indicator=True)

    # 6. Validar (se calcula todo y se reporta todo, aunque algo falle)
    chequeos: list[tuple[str, bool, str]] = []

    def chequear(nombre: str, ok: bool, detalle: str) -> None:
        chequeos.append((nombre, bool(ok), detalle))

    dup_p = int(personas.duplicated(LLAVES_PERSONA).sum())
    dup_h = int(sumaria.duplicated(LLAVES_HOGAR).sum())
    sin_hogar = int((base["_merge"] != "both").sum())
    chequear("Llaves de persona únicas", dup_p == 0, f"{dup_p} duplicadas")
    chequear("Llaves de hogar únicas en la sumaria", dup_h == 0, f"{dup_h} duplicadas")
    chequear("La unión no perdió ni duplicó filas", len(base) == len(personas),
             f"{len(base):,} filas en la base, {len(personas):,} residentes")
    chequear("Toda persona encontró su hogar", sin_hogar == 0, f"{sin_hogar} sin hogar")
    base = base.drop(columns="_merge")

    ubi = base["ubigeo"].dropna()
    chequear("Ubigeo de 6 dígitos con ceros", bool(ubi.str.fullmatch(r"\d{6}").all()),
             f"ejemplo: {ubi.iloc[0] if len(ubi) else '—'}")

    base = construir(base, anio)
    ndep = base.loc[base["departamento_nombre"].notna(), "departamento"].nunique()
    chequear("25 departamentos con nombre", ndep == 25, f"{ndep} departamentos")

    pob_hog = pct(sumaria["pobreza"] <= 2, sumaria["factor07"] * sumaria["mieperho"])
    ext_hog = pct(sumaria["pobreza"] == 1, sumaria["factor07"] * sumaria["mieperho"])
    pob_per = pct(base["pobre"], base["facpob07"])
    ext_per = pct(base["pobre_extremo"], base["facpob07"])
    poblacion = base["facpob07"].sum()

    of = OFICIAL.get(anio)
    if of:
        chequear("Hogares en la sumaria", len(sumaria) == of["hogares"],
                 f"{len(sumaria):,} (INEI: {of['hogares']:,})")
        chequear("Filas del módulo 02", filas_modulo02 == of["filas_modulo02"],
                 f"{filas_modulo02:,} (esperado: {of['filas_modulo02']:,})")
        chequear("Residentes habituales", len(personas) == of["residentes"],
                 f"{len(personas):,} (esperado: {of['residentes']:,})")
        chequear("Pobreza = cifra oficial (sumaria, factor07 × mieperho)",
                 abs(pob_hog - of["pobreza"]) < TOLERANCIA_PP,
                 f"{pob_hog:.2f} % (INEI: {of['pobreza']} %)")
        chequear("Pobreza = cifra oficial (personas, facpob07)",
                 abs(pob_per - of["pobreza"]) < TOLERANCIA_PP,
                 f"{pob_per:.2f} % (INEI: {of['pobreza']} %)")
        chequear("Pobreza extrema = cifra oficial (sumaria)",
                 abs(ext_hog - of["pobreza_extrema"]) < TOLERANCIA_PP,
                 f"{ext_hog:.2f} % (INEI: {of['pobreza_extrema']} %)")

    ok = all(c[1] for c in chequeos)

    # 7. Guardar
    SALIDAS.mkdir(exist_ok=True)
    parquet = SALIDAS / f"personas_{anio}.parquet"
    lineas = [
        f"VALIDACIÓN ENAHO {anio} (código INEI {codigo})",
        f"Generado: {datetime.now():%Y-%m-%d %H:%M}",
        f"RESULTADO: {'OK' if ok else 'FALLA'}",
        "",
        "Chequeos",
        *[f"  [{'OK' if b else 'X '}] {n}: {d}" for n, b, d in chequeos],
        "",
        "Cifras",
        f"  Pobreza (personas, facpob07):          {pob_per:6.2f} %",
        f"  Pobreza (sumaria, factor07 × mieperho): {pob_hog:6.2f} %",
        f"  Pobreza extrema (personas, facpob07):  {ext_per:6.2f} %",
        f"  Pobreza extrema (sumaria):             {ext_hog:6.2f} %",
        f"  Población expandida (facpob07):        {poblacion:,.0f}",
        f"  Hogares: {len(sumaria):,} · Personas residentes: {len(personas):,} de {filas_modulo02:,} filas",
        "",
        f"Base: {parquet.relative_to(RAIZ) if ok else 'NO SE GUARDÓ porque la validación falló'}",
        f"Una fila por persona residente habitual; {base.shape[1]} columnas. Pondera con facpob07.",
    ]
    if not of:
        lineas.insert(3, f"AVISO: no hay cifras oficiales fijadas para {anio}; solo se validó la estructura.")
    (SALIDAS / "validacion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    if ok:
        base.to_parquet(parquet, index=False)
    elif parquet.exists():
        parquet.unlink()  # que nadie use una base vieja o mal limpia

    print("\n".join(lineas))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
