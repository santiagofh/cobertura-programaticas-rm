"""Convierte el Informe Ejecutivo 2024 (Excel cerrado) al esquema local.

Copia los resultados publicados en
`2024 Cerrado/2026-06-17_coberturas_vacunas_Programaticas_2024_V7_Informe
Ejecutivo 2024.xlsx` (hoja `Por_Comuna (final)`, corte 15-06-2026) al CSV
semilla `output/coberturas_vacunas_2024_V7_INFORME.csv`, con las mismas
columnas que los outputs del pipeline local:

    COD_COMUNA_JOIN, COMUNA_CALCULO, VACUNA_DASHBOARD, CLAVE_DENOMINADOR,
    VACUNAS_ADMINISTRADAS, POBLACION_OBJETIVO, PORC_COBERTURA

Sin recalcular: los vacunados, la población objetivo y el % de cobertura se
copian tal cual están publicados en el Excel. El script además cuadra la suma
comunal contra la hoja `Resumen_Regional (final)`.

Uso:
    python convertir_informe_2024.py
    python convertir_informe_2024.py --xlsx "ruta" --salida "ruta.csv"
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from convertir_minsal_programaticas import _limpiar_comuna, _mapa_comunas, _normalizar
from src import config_programaticas as cfgmod

BASE_DIR = Path(__file__).resolve().parent
XLSX_DEFAULT = Path(
    os.environ.get(
        "PROGRAMATICAS_INFORME_2024_XLSX",
        BASE_DIR / "2024 Cerrado"
        / "2026-06-17_coberturas_vacunas_Programaticas_2024_V7_Informe Ejecutivo 2024.xlsx",
    )
)

HOJA_COMUNA = "por_comuna"
HOJA_REGIONAL = "resumen_regional"

COLUMNAS_SALIDA = [
    "COD_COMUNA_JOIN", "COMUNA_CALCULO", "VACUNA_DASHBOARD",
    "CLAVE_DENOMINADOR", "VACUNAS_ADMINISTRADAS", "POBLACION_OBJETIVO",
    "PORC_COBERTURA",
]


def _hoja(xl: pd.ExcelFile, token: str) -> str:
    for nombre in xl.sheet_names:
        if _normalizar(nombre).startswith(token):
            return nombre
    raise KeyError(f"No encontré la hoja '{token}' en {xl.io.name}: {xl.sheet_names}")


def cargar_informe(xlsx: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (detalle por comuna, resumen regional publicado)."""
    with pd.ExcelFile(xlsx) as xl:
        com = pd.read_excel(xl, sheet_name=_hoja(xl, HOJA_COMUNA), header=2)
        reg = pd.read_excel(xl, sheet_name=_hoja(xl, HOJA_REGIONAL), header=0)

    com.columns = [str(c).strip() for c in com.columns]
    com = com[com["NOMBRE VACUNA"].notna()].copy()

    reg.columns = [str(c).strip() for c in reg.columns]
    col_vac = next(c for c in reg.columns if "TRAZADORAS" in c)
    reg = reg[reg["VACUNAS ADMINISTRADAS"].notna()].copy()
    reg = reg.rename(columns={col_vac: "vacuna"})

    mapa_comunas = _mapa_comunas()
    com["COMUNA_CALCULO"] = _limpiar_comuna(com["COMUNA RESIDENCIA"])
    com["COD_COMUNA_JOIN"] = com["COMUNA_CALCULO"].map(_normalizar).map(mapa_comunas)
    sin_codigo = com[com["COD_COMUNA_JOIN"].isna()]["COMUNA_CALCULO"].unique()
    if len(sin_codigo):
        raise ValueError(f"Comunas del informe sin código en COMUNA_MAP: {list(sin_codigo)}")
    com["COD_COMUNA_JOIN"] = com["COD_COMUNA_JOIN"].astype(int)
    com["VACUNA_DASHBOARD"] = com["NOMBRE VACUNA"].astype(str).str.strip()
    com["CLAVE_DENOMINADOR"] = com["DESCRPCION"].astype(str).str.strip()
    com["VACUNAS_ADMINISTRADAS"] = pd.to_numeric(
        com["VACUNAS ADMINISTRADAS"], errors="raise").astype("Int64")
    com["POBLACION_OBJETIVO"] = pd.to_numeric(
        com["POBLACION OBJETIVO"], errors="raise").astype("Int64")
    com["PORC_COBERTURA"] = pd.to_numeric(
        com["% Cobertura COBERTURA"], errors="raise").astype(float)

    return com[COLUMNAS_SALIDA].copy(), reg


def escribir_csv_semilla(df_detalle: pd.DataFrame, anio: int,
                         salida: Path | None = None) -> Path:
    salida = salida or cfgmod.OUTPUT_DIR / f"coberturas_vacunas_{anio}_V7_INFORME.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    orden_vacunas = {v: i for i, v in enumerate(pd.unique(df_detalle["VACUNA_DASHBOARD"]))}
    df = df_detalle.copy()
    df["_orden"] = df["VACUNA_DASHBOARD"].map(orden_vacunas)
    df = df.sort_values(["COD_COMUNA_JOIN", "_orden"])[COLUMNAS_SALIDA]
    df.to_csv(salida, index=False, encoding="utf-8-sig")
    return salida


def main():
    ap = argparse.ArgumentParser(
        description="Informe Ejecutivo 2024 (Excel) -> CSV esquema local")
    ap.add_argument("--xlsx", type=Path, default=XLSX_DEFAULT)
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args()

    detalle, regional = cargar_informe(args.xlsx)
    salida = escribir_csv_semilla(detalle, args.anio, args.salida)

    print(f"Informe     : {args.xlsx}")
    print(f"Semilla     : {salida}")
    print(f"Combinaciones: {detalle['VACUNA_DASHBOARD'].nunique()} | "
          f"Comunas: {detalle['COD_COMUNA_JOIN'].nunique()} | Filas: {len(detalle)}")

    comparacion = detalle.groupby("VACUNA_DASHBOARD", as_index=False).agg(
        vacunados=("VACUNAS_ADMINISTRADAS", "sum"),
        poblacion=("POBLACION_OBJETIVO", "sum"),
    )
    comparacion = comparacion.merge(
        regional[["vacuna", "VACUNAS ADMINISTRADAS", "POBLACION OBJETIVO"]],
        left_on="VACUNA_DASHBOARD", right_on="vacuna", how="left",
    )
    sin_fila_regional = comparacion["VACUNAS ADMINISTRADAS"].isna()
    comparacion["minsal_vacunados"] = comparacion["VACUNAS ADMINISTRADAS"].fillna(
        comparacion["vacunados"])
    comparacion["minsal_poblacion"] = comparacion["POBLACION OBJETIVO"].fillna(
        comparacion["poblacion"])
    ok = ((comparacion["vacunados"] == comparacion["minsal_vacunados"]) &
          (comparacion["poblacion"] == comparacion["minsal_poblacion"])).all()
    print(f"Cuadre vs Resumen_Regional: {'OK' if ok else 'REVISAR'}"
          + (f" (sin fila regional: {list(comparacion.loc[sin_fila_regional, 'VACUNA_DASHBOARD'])})"
             if sin_fila_regional.any() else ""))
    print(comparacion[["VACUNA_DASHBOARD", "vacunados", "minsal_vacunados",
                       "poblacion", "minsal_poblacion"]].to_string(index=False))


if __name__ == "__main__":
    main()
