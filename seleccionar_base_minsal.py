"""Elige la mejor base local (SD o CD) por vacuna frente al corte MINSAL.

Regla: se parte de la base SD (sin duplicados, criterio del dashboard) y se
cambia a CD solo cuando la diferencia comunal acumulada contra MINSAL se
reduce a menos de la mitad (SAE_CD < umbral * SAE_SD, umbral=0.5 por defecto).

Genera `output/coberturas_vacunas_{T}_V7_MIXTA.csv` con el mismo esquema de
los outputs locales, apta para el selector "Cálculo: Propio / Mixto / MINSAL".

Uso:
    python seleccionar_base_minsal.py
    python seleccionar_base_minsal.py --umbral 0.5 --anio 2025
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


def _sae(minsal: pd.DataFrame, base: pd.DataFrame) -> pd.Series:
    m = minsal.merge(
        base[["COD_COMUNA_JOIN", "VACUNA_DASHBOARD", "VACUNAS_ADMINISTRADAS"]],
        on=["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"], how="left",
        suffixes=("_m", "_b"),
    )
    m["dif"] = m["VACUNAS_ADMINISTRADAS_m"] - m["VACUNAS_ADMINISTRADAS_b"]
    return m.groupby("VACUNA_DASHBOARD")["dif"].apply(lambda s: s.abs().sum())


def generar_base_mixta(anio: int = 2025, umbral: float = 0.5,
                       salida: Path | None = None) -> Path:
    minsal = pd.read_csv(
        latest_dated_file_any(cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{anio}_V7_MINSAL.csv"),
        encoding="utf-8-sig",
    )
    ruta_sd = latest_dated_file_any(cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{anio}_V7_SD.csv")
    ruta_cd = latest_dated_file_any(cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{anio}_V7_CD.csv")
    sd = pd.read_csv(ruta_sd, encoding="utf-8-sig")
    cd = pd.read_csv(ruta_cd, encoding="utf-8-sig")

    sae_sd = _sae(minsal, sd)
    sae_cd = _sae(minsal, cd)

    decisiones = []
    for vacuna in sae_sd.index:
        elegida = "CD" if sae_cd[vacuna] < umbral * sae_sd[vacuna] else "SD"
        decisiones.append({"VACUNA_DASHBOARD": vacuna,
                           "SAE_SD": int(sae_sd[vacuna]),
                           "SAE_CD": int(sae_cd[vacuna]),
                           "ELEGIDA": elegida})
    tabla = pd.DataFrame(decisiones)
    print(f"Regla: CD si SAE_CD < {umbral} x SAE_SD (resto SD)")
    print(tabla.to_string(index=False))

    mix = sd.copy()
    cambian = tabla.loc[tabla["ELEGIDA"] == "CD", "VACUNA_DASHBOARD"].tolist()
    for vacuna in cambian:
        mix = mix[~mix["VACUNA_DASHBOARD"].eq(vacuna)]
        mix = pd.concat([mix, cd[cd["VACUNA_DASHBOARD"].eq(vacuna)]], ignore_index=True)
    mix = mix[COLUMNAS].sort_values(["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"]).reset_index(drop=True)

    salida = salida or cfgmod.OUTPUT_DIR / f"coberturas_vacunas_{anio}_V7_MIXTA.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    mix.to_csv(salida, index=False, encoding="utf-8-sig")

    comunes = mix.merge(minsal[["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"]],
                        on=["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"])
    tot_mix = comunes["VACUNAS_ADMINISTRADAS"].sum()
    tot_minsal = minsal["VACUNAS_ADMINISTRADAS"].sum()
    print()
    print(f"Base SD   : {ruta_sd.name}")
    print(f"Base CD   : {ruta_cd.name}")
    print(f"Semilla   : {salida.name}")
    print(f"Vacunas en CD: {cambian}")
    print(f"Filas: {len(mix)} | Vacunas: {mix['VACUNA_DASHBOARD'].nunique()}")
    print(f"23 combos compartidos -> Mixto {tot_mix:,} vs MINSAL {tot_minsal:,} (dif {tot_minsal - tot_mix:+,})")
    return salida


def main():
    ap = argparse.ArgumentParser(description="Base mixta SD/CD por vacuna vs corte MINSAL")
    ap.add_argument("--anio", type=int, default=2025)
    ap.add_argument("--umbral", type=float, default=0.5,
                    help="Cambia a CD si SAE_CD < umbral x SAE_SD (def. 0.5)")
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args()
    generar_base_mixta(args.anio, args.umbral, args.salida)


if __name__ == "__main__":
    main()
