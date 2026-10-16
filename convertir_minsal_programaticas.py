"""Convierte el corte MINSAL de Programáticas (Región-Comuna) al esquema local.

Copia los resultados publicados por MINSAL (sin recalcular) al CSV semilla
`output/coberturas_vacunas_{T}_V7_MINSAL.csv`, con las mismas columnas que los
outputs del pipeline local:

    COD_COMUNA_JOIN, COMUNA_CALCULO, VACUNA_DASHBOARD, CLAVE_DENOMINADOR,
    VACUNAS_ADMINISTRADAS, POBLACION_OBJETIVO, PORC_COBERTURA

También expone `cargar_corte()` (usada por comparar_minsal_programaticas.py)
que devuelve el detalle por comuna y el resumen nacional publicado.

Uso:
    python convertir_minsal_programaticas.py
    python convertir_minsal_programaticas.py --corte-dir "ruta" --anio 2025
"""

from __future__ import annotations

import argparse
import os
import unicodedata
from glob import glob
from pathlib import Path

import pandas as pd

from src import config_programaticas as cfgmod

BASE_DIR = Path(__file__).resolve().parent
CORTE_DEFAULT = Path(
    os.environ.get(
        "PROGRAMATICAS_MINSAL_DIR",
        BASE_DIR.parent / "CORTE MINSAL 2026-10-09" / "PROGRAMATICAS 2025",
    )
)

# Orden de archivos y mapeo a los nombres/claves del pipeline local.
MAPPING = [
    {"archivo": "BCG", "criterio": None, "dosis": None,
     "vacuna_minsal": "BCG", "dosis_minsal": "unica",
     "vacuna": "VACUNA BCG", "clave": "BCG_RN"},
    {"archivo": "DTPA ESCOLAR", "criterio": "1° Básico", "dosis": "1° Refuerzo",
     "vacuna_minsal": "DTPA ESCOLAR", "dosis_minsal": "1° refuerzo",
     "vacuna": "VACUNA DTPA 1 BASICO", "clave": "dTpa_1basico"},
    {"archivo": "DTPA ESCOLAR", "criterio": "8° Básico", "dosis": "2° Refuerzo",
     "vacuna_minsal": "DTPA ESCOLAR", "dosis_minsal": "2° refuerzo",
     "vacuna": "VACUNA DTPA 8 BASICO", "clave": "dTpa_8basico"},
    {"archivo": "DTPA GESTANTES", "criterio": "Gestante", "dosis": "Única",
     "vacuna_minsal": "DTPA GESTANTES", "dosis_minsal": "unica",
     "vacuna": "VACUNA DTPA GESTANTES", "clave": "dTpa_Gestantes"},
    {"archivo": "HEP A", "criterio": None, "dosis": "Única",
     "vacuna_minsal": "HEP A", "dosis_minsal": "unica",
     "vacuna": "VACUNA HEPATITIS A PEDIATRICA", "clave": "Cohorte_18M"},
    {"archivo": "HEP B", "criterio": None, "dosis": "Única",
     "vacuna_minsal": "HEP B", "dosis_minsal": "unica",
     "vacuna": "VACUNA HEPATITIS B RN", "clave": "HepB_RN"},
    {"archivo": "HEXAVALENTE", "criterio": None, "dosis": "1° Dosis",
     "vacuna_minsal": "HEXAVALENTE", "dosis_minsal": "1° dosis",
     "vacuna": "VACUNA HEXAVALENTE 1RA DOSIS", "clave": "Cohorte_2M"},
    {"archivo": "HEXAVALENTE", "criterio": None, "dosis": "2° Dosis",
     "vacuna_minsal": "HEXAVALENTE", "dosis_minsal": "2° dosis",
     "vacuna": "VACUNA HEXAVALENTE 2DA DOSIS", "clave": "Cohorte_4M"},
    {"archivo": "HEXAVALENTE", "criterio": None, "dosis": "3° Dosis",
     "vacuna_minsal": "HEXAVALENTE", "dosis_minsal": "3° dosis",
     "vacuna": "VACUNA HEXAVALENTE 3RA DOSIS", "clave": "Hexavalente_3d_6m"},
    {"archivo": "HEXAVALENTE", "criterio": None, "dosis": "Refuerzo",
     "vacuna_minsal": "HEXAVALENTE", "dosis_minsal": "refuerzo",
     "vacuna": "VACUNA HEXAVALENTE REFUERZO", "clave": "Hexavalente_ref_18m"},
    {"archivo": "MENINGO CONJUGADA", "criterio": None, "dosis": "Única",
     "vacuna_minsal": "MENINGO CONJUGADA", "dosis_minsal": "unica",
     "vacuna": "VACUNA MENINGOCOCICA CONJUGADA DOSIS UNICA", "clave": "Cohorte_12M"},
    {"archivo": "MENINGO RECO", "criterio": None, "dosis": "1° Dosis",
     "vacuna_minsal": "MENINGO RECO", "dosis_minsal": "1° dosis",
     "vacuna": "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS", "clave": "Cohorte_2M"},
    {"archivo": "MENINGO RECO", "criterio": None, "dosis": "2° Dosis",
     "vacuna_minsal": "MENINGO RECO", "dosis_minsal": "2° dosis",
     "vacuna": "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS", "clave": "Cohorte_4M"},
    {"archivo": "MENINGO RECO", "criterio": None, "dosis": "Refuerzo",
     "vacuna_minsal": "MENINGO RECO", "dosis_minsal": "refuerzo",
     "vacuna": "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO", "clave": "Cohorte_18M"},
    {"archivo": "NEUMO POLI", "criterio": "65 años", "dosis": "Única",
     "vacuna_minsal": "NEUMO POLI", "dosis_minsal": "unica",
     "vacuna": "VACUNA NEUMOCOCICA POLISACARIDA", "clave": "Neumococica_Polisacarida_65"},
    {"archivo": "NEUMOCO", "criterio": None, "dosis": "1° Dosis",
     "vacuna_minsal": "NEUMOCO", "dosis_minsal": "1° dosis",
     "vacuna": "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS", "clave": "Cohorte_2M"},
    {"archivo": "NEUMOCO", "criterio": None, "dosis": "2° Dosis",
     "vacuna_minsal": "NEUMOCO", "dosis_minsal": "2° dosis",
     "vacuna": "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS", "clave": "Cohorte_4M"},
    {"archivo": "NEUMOCO", "criterio": None, "dosis": "Refuerzo",
     "vacuna_minsal": "NEUMOCO", "dosis_minsal": "refuerzo",
     "vacuna": "VACUNA NEUMOCOCICA CONJUGADA REFUERZO", "clave": "Cohorte_12M"},
    {"archivo": "SRP TRIVIRICA", "criterio": None, "dosis": "1° Dosis",
     "vacuna_minsal": "SRP TRIVIRICA", "dosis_minsal": "1° dosis",
     "vacuna": "VACUNA SRP (TRIVIRICA) 1RA DOSIS", "clave": "Cohorte_12M"},
    {"archivo": "SRP TRIVIRICA", "criterio": None, "dosis": "2° Dosis",
     "vacuna_minsal": "SRP TRIVIRICA", "dosis_minsal": "2° dosis",
     "vacuna": "VACUNA SRP (TRIVIRICA) 2DA DOSIS", "clave": "Cohorte_36M"},
    {"archivo": "VARICELA", "criterio": None, "dosis": "1° Dosis",
     "vacuna_minsal": "VARICELA", "dosis_minsal": "1° dosis",
     "vacuna": "VACUNA VARICELA 1RA DOSIS", "clave": "Cohorte_18M"},
    {"archivo": "VARICELA", "criterio": None, "dosis": "2° Dosis",
     "vacuna_minsal": "VARICELA", "dosis_minsal": "2° dosis",
     "vacuna": "VACUNA VARICELA 2DA DOSIS", "clave": "Cohorte_36M"},
    {"archivo": "VPH", "criterio": "4° Básico", "dosis": "1° Dosis o Única",
     "vacuna_minsal": "VPH", "dosis_minsal": "1° dosis o unica",
     "vacuna": "VACUNA VPH 4 BASICO", "clave": "VPH_4basico"},
]

COLUMNAS_SALIDA = [
    "COD_COMUNA_JOIN", "COMUNA_CALCULO", "VACUNA_DASHBOARD",
    "CLAVE_DENOMINADOR", "VACUNAS_ADMINISTRADAS", "POBLACION_OBJETIVO",
    "PORC_COBERTURA",
]


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return " ".join(texto.replace("\xa0", " ").split()).lower()


def _num_chileno(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.astype(str).str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _pct_chileno(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.astype(str).str.strip().str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _limpiar_comuna(serie: pd.Series) -> pd.Series:
    return (
        serie.astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def _mapa_comunas() -> dict:
    return {_normalizar(k): v for k, v in cfgmod.COMUNA_MAP.items()}


def _buscar_archivo(archivos: list[str], token: str) -> str:
    candidatos = [f for f in archivos if os.path.basename(f).startswith(token)]
    if len(candidatos) != 1:
        raise FileNotFoundError(f"No encontré un único CSV MINSAL para '{token}': {candidatos}")
    return candidatos[0]


def cargar_corte(corte_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (detalle por comuna, resumen nacional publicado)."""
    archivos = glob(str(corte_dir / "*.csv"))
    if not archivos:
        raise FileNotFoundError(f"Sin CSV en el corte MINSAL: {corte_dir}")
    mapa_comunas = _mapa_comunas()

    detalle = []
    nacional = []
    for spec in MAPPING:
        ruta = _buscar_archivo(archivos, spec["archivo"])
        df = pd.read_csv(ruta, dtype=str, encoding="utf-8-sig")
        df.columns = [c.strip().strip('"') for c in df.columns]
        col_comuna = "Comuna" if "Comuna" in df.columns else "Comuna de Ocurrencia"

        nac_todas = df[df[col_comuna].isna()]
        if spec["criterio"] is not None:
            df = df[df["Criterio de Elegibilidad"].map(_normalizar) == _normalizar(spec["criterio"])]
        if spec["dosis"] is not None:
            df = df[df["Dosis"].map(_normalizar) == _normalizar(spec["dosis"])]
        if df.empty:
            raise ValueError(f"Sin filas para {spec['archivo']} {spec['criterio']} {spec['dosis']}")

        nac = df[df[col_comuna].isna()]
        fila = None
        if len(nac) == 1:
            fila = nac.iloc[0]
        elif len(nac_todas) == 1:
            fila = nac_todas.iloc[0]
        com = df[df[col_comuna].notna()].copy()

        if fila is not None:
            nacional.append({
                "vacuna_minsal": spec["vacuna_minsal"], "dosis_minsal": spec["dosis_minsal"],
                "vacuna_usuario": spec["vacuna"],
                "minsal_vacunados": _num_chileno(pd.Series([fila["Vacunados"]])).iloc[0],
                "minsal_poblacion": _num_chileno(pd.Series([fila["Población"]])).iloc[0],
                "minsal_pct": _pct_chileno(pd.Series([fila["Cobertura"]])).iloc[0],
            })

        com["COMUNA_CALCULO"] = _limpiar_comuna(com[col_comuna])
        com["COD_COMUNA_JOIN"] = com["COMUNA_CALCULO"].map(_normalizar).map(mapa_comunas)
        sin_codigo = com[com["COD_COMUNA_JOIN"].isna()]["COMUNA_CALCULO"].unique()
        if len(sin_codigo):
            raise ValueError(f"Comunas MINSAL sin código en {spec['archivo']}: {list(sin_codigo)}")
        com["COD_COMUNA_JOIN"] = com["COD_COMUNA_JOIN"].astype(int)
        com["VACUNA_DASHBOARD"] = spec["vacuna"]
        com["CLAVE_DENOMINADOR"] = spec["clave"]
        com["VACUNAS_ADMINISTRADAS"] = _num_chileno(com["Vacunados"]).astype("Int64")
        com["POBLACION_OBJETIVO"] = _num_chileno(com["Población"]).astype("Int64")
        com["PORC_COBERTURA"] = _pct_chileno(com["Cobertura"])

        detalle.append(com[COLUMNAS_SALIDA])

    df_detalle = pd.concat(detalle, ignore_index=True)
    df_nacional = pd.DataFrame(nacional)
    return df_detalle, df_nacional


def escribir_csv_semilla(df_detalle: pd.DataFrame, anio: int, salida: Path | None = None) -> Path:
    salida = salida or cfgmod.OUTPUT_DIR / f"coberturas_vacunas_{anio}_V7_MINSAL.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    orden_vacunas = {spec["vacuna"]: i for i, spec in enumerate(MAPPING)}
    df = df_detalle.copy()
    df["_orden"] = df["VACUNA_DASHBOARD"].map(orden_vacunas)
    df = df.sort_values(["COD_COMUNA_JOIN", "_orden"])[COLUMNAS_SALIDA]
    df.to_csv(salida, index=False, encoding="utf-8-sig")
    return salida


def main():
    ap = argparse.ArgumentParser(description="Corte MINSAL Programáticas -> CSV esquema local")
    ap.add_argument("--corte-dir", type=Path, default=CORTE_DEFAULT)
    ap.add_argument("--anio", type=int, default=2025)
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args()

    detalle, nacional = cargar_corte(args.corte_dir)
    salida = escribir_csv_semilla(detalle, args.anio, args.salida)

    print(f"Corte       : {args.corte_dir}")
    print(f"Semilla     : {salida}")
    print(f"Combinaciones: {detalle['VACUNA_DASHBOARD'].nunique()} | Comunas: {detalle['COD_COMUNA_JOIN'].nunique()} | Filas: {len(detalle)}")
    comparacion = detalle.groupby("VACUNA_DASHBOARD", as_index=False).agg(
        vacunados=("VACUNAS_ADMINISTRADAS", "sum"),
        poblacion=("POBLACION_OBJETIVO", "sum"),
    )
    comparacion = comparacion.merge(
        nacional[["vacuna_usuario", "minsal_vacunados", "minsal_poblacion"]],
        left_on="VACUNA_DASHBOARD", right_on="vacuna_usuario", how="left",
    )
    sin_fila_nacional = comparacion["minsal_vacunados"].isna()
    comparacion["minsal_vacunados"] = comparacion["minsal_vacunados"].fillna(comparacion["vacunados"])
    comparacion["minsal_poblacion"] = comparacion["minsal_poblacion"].fillna(comparacion["poblacion"])
    ok = ((comparacion["vacunados"] == comparacion["minsal_vacunados"]) &
          (comparacion["poblacion"] == comparacion["minsal_poblacion"])).all()
    print(f"Cuadre vs fila nacional MINSAL: {'OK' if ok else 'REVISAR'}"
          + (f" (sin fila nacional: {list(comparacion.loc[sin_fila_nacional, 'VACUNA_DASHBOARD'])})"
             if sin_fila_nacional.any() else ""))
    print(comparacion[["VACUNA_DASHBOARD", "vacunados", "minsal_vacunados",
                       "poblacion", "minsal_poblacion"]].to_string(index=False))


if __name__ == "__main__":
    main()
