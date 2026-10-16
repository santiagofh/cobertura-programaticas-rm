"""Base FINAL del informe: mezcla aprobada Usuario (cálculo propio) / MINSAL.

El criterio vive en `data/prioridad_final_{anio}.csv` (hoja Resumen del Excel
`comparacion_programaticas_{anio}_vs_minsal_revisado.xlsx`):

  - Prioridad "Usuario"  -> filas de la base Mixta (mejor base SD/CD por vacuna).
  - Prioridad "MINSAL"   -> filas del corte MINSAL, publicadas sin recalcular.
  - Prioridad "Eliminar del calculo" -> no entran a la base final.

Genera `output/coberturas_vacunas_{T}_V7_FINAL.csv` (mismo esquema local + la
columna ORIGEN), apta para el dashboard y los Excel imprimibles.

Uso:
    python seleccionar_base_final.py
    python seleccionar_base_final.py --anio 2025
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src import config_programaticas as cfgmod
from src.pipeline.coberturas import latest_dated_file_any

COLUMNAS = [
    "COD_COMUNA_JOIN", "COMUNA_CALCULO", "VACUNA_DASHBOARD",
    "CLAVE_DENOMINADOR", "VACUNAS_ADMINISTRADAS", "POBLACION_OBJETIVO",
    "PORC_COBERTURA",
]


def generar_base_final(anio: int = 2025, salida: Path | None = None) -> Path:
    ruta_criterio = cfgmod.DATA_DIR / f"prioridad_final_{anio}.csv"
    criterio = pd.read_csv(ruta_criterio, encoding="utf-8-sig")
    criterio["prioridad"] = criterio["prioridad"].str.strip()

    ruta_mixta = latest_dated_file_any(cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{anio}_V7_MIXTA.csv")
    ruta_minsal = latest_dated_file_any(cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{anio}_V7_MINSAL.csv")
    mixta = pd.read_csv(ruta_mixta, encoding="utf-8-sig")
    minsal = pd.read_csv(ruta_minsal, encoding="utf-8-sig")

    fuentes = {"Usuario": mixta, "MINSAL": minsal}
    partes = []
    for _, fila in criterio.iterrows():
        prioridad = fila["prioridad"]
        vacuna = fila["vacuna_usuario"]
        if prioridad not in fuentes:
            continue
        bloque = fuentes[prioridad][
            fuentes[prioridad]["VACUNA_DASHBOARD"].eq(vacuna)
        ].copy()
        if bloque.empty:
            raise ValueError(f"{vacuna} no existe en la base {prioridad}")
        bloque["ORIGEN"] = prioridad
        partes.append(bloque)

    final = pd.concat(partes, ignore_index=True)
    final = (final[COLUMNAS + ["ORIGEN"]]
             .sort_values(["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"])
             .reset_index(drop=True))

    salida = salida or cfgmod.OUTPUT_DIR / f"coberturas_vacunas_{anio}_V7_FINAL.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(salida, index=False, encoding="utf-8-sig")
    final.to_excel(salida.with_suffix(".xlsx"), index=False)

    resumen = (final.groupby(["VACUNA_DASHBOARD", "ORIGEN"], as_index=False)
               .agg(VACUNAS_ADMINISTRADAS=("VACUNAS_ADMINISTRADAS", "sum"),
                    POBLACION_OBJETIVO=("POBLACION_OBJETIVO", "sum")))
    resumen["PORC_COBERTURA"] = (
        resumen["VACUNAS_ADMINISTRADAS"] / resumen["POBLACION_OBJETIVO"] * 100
    ).round(2)

    eliminadas = criterio.loc[criterio["prioridad"] == "Eliminar del calculo",
                              "vacuna_usuario"].tolist()
    print(f"Criterio   : {ruta_criterio.name}")
    print(f"Base Mixta : {ruta_mixta.name}")
    print(f"Corte MINSAL: {ruta_minsal.name}")
    print(f"Semilla    : {salida.name}")
    print(f"Vacunas Usuario: {(criterio['prioridad'] == 'Usuario').sum()} | "
          f"MINSAL: {(criterio['prioridad'] == 'MINSAL').sum()} | "
          f"Eliminadas: {len(eliminadas)}")
    print(f"Filas: {len(final)} | Vacunas: {final['VACUNA_DASHBOARD'].nunique()}")
    print()
    print(resumen.to_string(index=False))
    return salida


def main():
    ap = argparse.ArgumentParser(description="Base FINAL Usuario/MINSAL (informe mezcla)")
    ap.add_argument("--anio", type=int, default=2025)
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args()
    generar_base_final(args.anio, args.salida)


if __name__ == "__main__":
    main()
