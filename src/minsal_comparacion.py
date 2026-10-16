"""Comparación entre el cálculo local y el corte MINSAL (Programáticas).

Cruza el CSV semilla del corte MINSAL (`coberturas_vacunas_{T}_V7_MINSAL.csv`,
publicado tal cual, sin recalcular) con la base local elegida (SD / CD / MIXTA)
y devuelve:
  - resumen : una fila por vacuna-dosis (las 23 combinaciones del corte)
  - detalle : una fila por comuna-vacuna-dosis

La base local no tiene filas para combinaciones que MINSAL no publica
(ej. VPH 5° básico), por lo que quedan fuera de la comparación.
"""

from __future__ import annotations

import pandas as pd

from . import config_programaticas as cfgmod
from .pipeline.coberturas import latest_dated_file_any

BASES = ["SD", "CD", "Mixto"]
SUFIJOS_BASE = {"SD": "SD", "CD": "CD", "Mixto": "MIXTA"}

COLUMNAS_DETALLE = [
    "comuna", "COD_COMUNA_JOIN", "VACUNA_DASHBOARD",
    "vacunados_minsal", "vacunados_local", "dif_vacunados",
    "poblacion_minsal", "poblacion_local", "dif_poblacion",
    "pct_minsal", "pct_local", "dif_pp", "pp_ok",
]


def cargar_comparacion(anio: int, base: str = "SD") -> dict:
    """Devuelve resumen/detalle de la comparación local vs MINSAL.

    base: "SD", "CD" o "Mixto" (MIXTA = mejor base por vacuna).
    """
    T = cfgmod.get_config(anio).T
    sufijo = SUFIJOS_BASE.get(base, "SD")
    ruta_minsal = latest_dated_file_any(
        cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{T}_V7_MINSAL.csv"
    )
    ruta_local = latest_dated_file_any(
        cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{T}_V7_{sufijo}.csv"
    )
    minsal = pd.read_csv(ruta_minsal, encoding="utf-8-sig")
    local = pd.read_csv(ruta_local, encoding="utf-8-sig")

    det = minsal.merge(
        local[["COD_COMUNA_JOIN", "VACUNA_DASHBOARD",
               "VACUNAS_ADMINISTRADAS", "POBLACION_OBJETIVO"]],
        on=["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"], how="left",
        suffixes=("_minsal", "_local"),
    )
    det = det.rename(columns={
        "COMUNA_CALCULO": "comuna",
        "PORC_COBERTURA": "pct_minsal",
        "VACUNAS_ADMINISTRADAS_minsal": "vacunados_minsal",
        "VACUNAS_ADMINISTRADAS_local": "vacunados_local",
        "POBLACION_OBJETIVO_minsal": "poblacion_minsal",
        "POBLACION_OBJETIVO_local": "poblacion_local",
    })
    det["pct_local"] = (
        det["vacunados_local"] / det["poblacion_local"].replace(0, pd.NA) * 100
    ).round(1)
    det["dif_vacunados"] = det["vacunados_minsal"] - det["vacunados_local"]
    det["dif_poblacion"] = det["poblacion_minsal"] - det["poblacion_local"]
    det["dif_pp"] = (det["pct_minsal"] - det["pct_local"]).round(1)
    det["pp_ok"] = det["dif_pp"].abs() <= 0.5

    resumen = det.groupby("VACUNA_DASHBOARD", as_index=False).agg(
        comunas_total=("pp_ok", "size"),
        comunas_pp_ok=("pp_ok", "sum"),
        vacunados_minsal=("vacunados_minsal", "sum"),
        vacunados_local=("vacunados_local", "sum"),
        poblacion_minsal=("poblacion_minsal", "sum"),
        poblacion_local=("poblacion_local", "sum"),
    )
    resumen[["vacunados_local", "poblacion_local"]] = (
        resumen[["vacunados_local", "poblacion_local"]].fillna(0)
    )
    resumen["dif_vacunados"] = resumen["vacunados_minsal"] - resumen["vacunados_local"]
    resumen["dif_poblacion"] = resumen["poblacion_minsal"] - resumen["poblacion_local"]
    resumen["pct_minsal"] = (
        resumen["vacunados_minsal"] / resumen["poblacion_minsal"].replace(0, pd.NA) * 100
    ).round(1)
    resumen["pct_local"] = (
        resumen["vacunados_local"] / resumen["poblacion_local"].replace(0, pd.NA) * 100
    ).round(1)
    resumen["dif_pp"] = (resumen["pct_minsal"] - resumen["pct_local"]).round(1)

    return {
        "resumen": resumen,
        "detalle": det[COLUMNAS_DETALLE].copy(),
        "ruta_minsal": ruta_minsal,
        "ruta_local": ruta_local,
        "base": base,
    }
