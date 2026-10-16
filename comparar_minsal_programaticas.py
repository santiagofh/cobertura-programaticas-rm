"""Compara el corte MINSAL de Programáticas con la salida local (CD o SD).

Genera `output/comparacion_programaticas_{T}_vs_minsal.xlsx` con:
  - Resumen : una fila por vacuna-dosis MINSAL (totales RM y diferencias)
  - Detalle : una fila por vacuna-dosis-comuna

Uso:
    python comparar_minsal_programaticas.py
    python comparar_minsal_programaticas.py --base SD --anio 2025
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from convertir_minsal_programaticas import CORTE_DEFAULT, MAPPING, cargar_corte
from src import config_programaticas as cfgmod
from src.pipeline.coberturas import latest_dated_file_any

ORDEN_VACUNAS = [spec["vacuna"] for spec in MAPPING]


def generar_comparacion(anio: int, corte_dir: Path, base: str = "CD",
                        salida: Path | None = None) -> Path:
    detalle_m, nacional = cargar_corte(corte_dir)
    ruta_local = latest_dated_file_any(
        cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{anio}_V7_{base}.csv"
    )
    local = pd.read_csv(ruta_local, encoding="utf-8-sig")

    det = detalle_m.merge(
        local[["COD_COMUNA_JOIN", "VACUNA_DASHBOARD", "VACUNAS_ADMINISTRADAS",
               "POBLACION_OBJETIVO", "PORC_COBERTURA"]],
        on=["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"], how="left",
        suffixes=("_minsal", "_usuario"),
    )
    etiquetas = (pd.DataFrame(MAPPING)[["vacuna", "vacuna_minsal", "dosis_minsal"]]
                 .drop_duplicates("vacuna")
                 .rename(columns={"vacuna": "vacuna_usuario"}))
    det = det.merge(etiquetas, left_on="VACUNA_DASHBOARD", right_on="vacuna_usuario", how="left")

    det["dif_vacunados"] = det["VACUNAS_ADMINISTRADAS_minsal"] - det["VACUNAS_ADMINISTRADAS_usuario"]
    det["dif_poblacion"] = det["POBLACION_OBJETIVO_minsal"] - det["POBLACION_OBJETIVO_usuario"]
    det["usuario_pct"] = (
        det["VACUNAS_ADMINISTRADAS_usuario"] / det["POBLACION_OBJETIVO_usuario"].replace(0, pd.NA) * 100
    ).round(1)
    det["dif_pp"] = (det["PORC_COBERTURA_minsal"] - det["usuario_pct"]).round(1)
    det["pp_ok"] = det["dif_pp"].abs() <= 0.5

    nacional = nacional.set_index("vacuna_usuario")
    filas = []
    for vacuna in ORDEN_VACUNAS:
        g = det[det["VACUNA_DASHBOARD"] == vacuna]
        spec = next(s for s in MAPPING if s["vacuna"] == vacuna)
        vac_m = nacional.loc[vacuna, "minsal_vacunados"] if vacuna in nacional.index else pd.NA
        pob_m = nacional.loc[vacuna, "minsal_poblacion"] if vacuna in nacional.index else pd.NA
        pct_m = nacional.loc[vacuna, "minsal_pct"] if vacuna in nacional.index else pd.NA
        vac_u = g["VACUNAS_ADMINISTRADAS_usuario"].sum(min_count=1)
        pob_u = g["POBLACION_OBJETIVO_usuario"].sum(min_count=1)
        vac_u = 0 if pd.isna(vac_u) else vac_u
        pob_u = 0 if pd.isna(pob_u) else pob_u
        if pd.isna(vac_m):
            vac_m = vac_u
        if pd.isna(pob_m):
            pob_m = pob_u
        filas.append({
            "vacuna": spec["vacuna_minsal"],
            "dosis": spec["dosis_minsal"],
            "vacuna_usuario": vacuna,
            "minsal_vacunados": int(vac_m),
            "usuario_vacunados": int(vac_u),
            "dif_vacunados": int(vac_m) - int(vac_u),
            "minsal_poblacion": int(pob_m),
            "usuario_poblacion": int(pob_u),
            "minsal_pct": None if pd.isna(pct_m) else float(pct_m),
            "usuario_pct": None if pob_u == 0 else round(vac_u / pob_u * 100, 2),
            "comunas_dif_vac": int((g["dif_vacunados"].fillna(0) != 0).sum()),
            "max_abs_dif_vac": int(g["dif_vacunados"].abs().max()) if len(g) else 0,
            "comunas_pp_ok": int(g["pp_ok"].fillna(False).sum()),
            "comunas_pp_total": int(len(g)) if pob_u > 0 else 0,
        })
    resumen = pd.DataFrame(filas)

    detalle = det[[
        "vacuna_minsal", "dosis_minsal", "vacuna_usuario", "COMUNA_CALCULO",
        "COD_COMUNA_JOIN", "VACUNAS_ADMINISTRADAS_minsal", "VACUNAS_ADMINISTRADAS_usuario",
        "dif_vacunados", "POBLACION_OBJETIVO_minsal", "POBLACION_OBJETIVO_usuario",
        "dif_poblacion", "PORC_COBERTURA_minsal", "usuario_pct", "dif_pp",
    ]].rename(columns={
        "COMUNA_CALCULO": "comuna",
        "COD_COMUNA_JOIN": "COD",
        "VACUNAS_ADMINISTRADAS_minsal": "vacunados",
        "VACUNAS_ADMINISTRADAS_usuario": "usuario_vacunados",
        "POBLACION_OBJETIVO_minsal": "poblacion",
        "POBLACION_OBJETIVO_usuario": "usuario_poblacion",
        "PORC_COBERTURA_minsal": "pct",
    })

    salida = salida or cfgmod.OUTPUT_DIR / f"comparacion_programaticas_{anio}_vs_minsal.xlsx"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        detalle.to_excel(writer, sheet_name="Detalle", index=False)

    print(f"Base local : {ruta_local.name}")
    print(f"Salida     : {salida}")
    print(f"Resumen: {len(resumen)} filas | Detalle: {len(detalle)} filas")
    print(resumen[["vacuna", "dosis", "usuario_vacunados", "minsal_vacunados", "dif_vacunados",
                   "usuario_poblacion", "minsal_poblacion", "comunas_pp_ok",
                   "comunas_pp_total"]].to_string(index=False))
    return salida


def main():
    ap = argparse.ArgumentParser(description="Comparación local vs corte MINSAL (Programáticas)")
    ap.add_argument("--anio", type=int, default=2025)
    ap.add_argument("--corte-dir", type=Path, default=CORTE_DEFAULT)
    ap.add_argument("--base", choices=["CD", "SD", "MIXTA"], default="CD",
                    help="Base local a comparar (MIXTA = mejor base por vacuna)")
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args()
    generar_comparacion(args.anio, args.corte_dir, args.base, args.salida)


if __name__ == "__main__":
    main()
