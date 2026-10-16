"""Excel imprimibles (matriz comunas x vacuna-dosis) — Programáticas RM.

Genera planillas con formato de impresión (estilo proyecto Influenza):

  - output/coberturas_vacunas_{T}_PROPIO_{base}_imprimible.xlsx  (cálculo local)
  - output/coberturas_vacunas_{T}_MINSAL_imprimible.xlsx         (corte MINSAL)

Con `--base Final` genera además:
  - output/coberturas_vacunas_{T}_FINAL_imprimible.xlsx  (informe final imprimible)
  - output/informe_final_coberturas_{T}.xlsx             (Excel para enviar)

Cada archivo trae 3 hojas: "Cobertura %" (con semáforo rojo→verde),
"Vacunados" y "Población objetivo". Filas: 52 comunas RM ordenadas
alfabéticamente + fila TOTAL REGIÓN METROPOLITANA.

Impresión: apaisado, ajustado a 1 página de ancho, títulos y encabezados
repetidos, congelado de paneles y pie de página.

Uso:
    python exportar_excels_imprimibles.py
    python exportar_excels_imprimibles.py --anio 2025 --base SD
    python exportar_excels_imprimibles.py --base Final
"""

from __future__ import annotations

import argparse
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties

from src import config_programaticas as cfgmod
from src.dashboard_comun import DISPLAY_ORDER, VACUNA_META
from src.pipeline.coberturas import latest_dated_file_any

FILA_TOTAL = "TOTAL REGIÓN METROPOLITANA"
SUFIJOS_BASE = {"SD": "SD", "CD": "CD", "Mixto": "MIXTA", "Final": "FINAL"}
MARCAS_ORIGEN = {"MINSAL": " *", "Usuario": " **"}
COLOR_ORIGEN = {"Usuario": "E2EFDA", "MINSAL": "D9E1F2"}
LEYENDA_ORIGEN = ("* Origen MINSAL (resultados publicados en el corte oficial, sin recalcular) · "
                  "** Origen Usuario (cálculo propio, base Mixta).")

# Etiquetas cortas para columnas (imprimibles en una página apaisada).
ETIQUETAS = {
    "VACUNA BCG": "BCG",
    "VACUNA HEPATITIS B RN": "Hep B RN",
    "VACUNA HEXAVALENTE 1RA DOSIS": "Hexa 1°",
    "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS": "Neumo 1°",
    "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS": "MenR 1°",
    "VACUNA HEXAVALENTE 2DA DOSIS": "Hexa 2°",
    "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS": "Neumo 2°",
    "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS": "MenR 2°",
    "VACUNA HEXAVALENTE 3RA DOSIS": "Hexa 3°",
    "VACUNA MENINGOCOCICA CONJUGADA DOSIS UNICA": "MenC 12m",
    "VACUNA SRP (TRIVIRICA) 1RA DOSIS": "SRP 1° 12m",
    "VACUNA NEUMOCOCICA CONJUGADA REFUERZO": "Neumo Ref",
    "VACUNA HEPATITIS A PEDIATRICA": "Hep A 18m",
    "VACUNA VARICELA 1RA DOSIS": "Varicela 1°",
    "VACUNA HEXAVALENTE REFUERZO": "Hexa Ref",
    "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO": "MenR Ref",
    "VACUNA SRP (TRIVIRICA) 2DA DOSIS": "SRP 2° 36m",
    "VACUNA VARICELA 2DA DOSIS": "Varicela 2°",
    "VACUNA DTPA 1 BASICO": "dTpa 1° bás",
    "VACUNA VPH 4 BASICO": "VPH 4° bás",
    "VACUNA DTPA 8 BASICO": "dTpa 8° bás",
    "VACUNA VPH 5 BASICO": "VPH 5° bás",
    "VACUNA NEUMOCOCICA POLISACARIDA": "Neumo Poli 65a",
    "VACUNA DTPA GESTANTES": "dTpa Gest.",
}

ESTRATEGIA_COLOR = {
    "Infantil": "C6EFCE",
    "Escolar": "FFEB9C",
    "Gestantes": "FCE4D6",
    "Personas mayores": "D9E1F2",
}


def _clave_orden(nombre: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", str(nombre))
        if not unicodedata.combining(c)
    )
    return sin_tildes.casefold()


def _estilo_header(cell, bg="1F4E79", color="FFFFFF", size=11):
    cell.font = Font(bold=True, color=color, name="Arial", size=size)
    cell.fill = PatternFill("solid", start_color=bg)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _borde_fino():
    s = Side(style="thin", color="BFBFBF")
    return Border(left=s, right=s, top=s, bottom=s)


def _escribir_tabla(ws, pivot: pd.DataFrame, titulo: str, fmt_num: str,
                    tipo_grupo: dict, origen_grupo: dict | None = None) -> None:
    grupos, comunas = list(pivot.columns), list(pivot.index)
    ncols = len(grupos)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols + 1)
    _estilo_header(ws.cell(1, 1, titulo), size=12)
    ws.row_dimensions[1].height = 22
    _estilo_header(ws.cell(2, 1, "Comuna"), bg="2E75B6")
    for j, g in enumerate(grupos, 2):
        etiqueta = g + (MARCAS_ORIGEN.get((origen_grupo or {}).get(g), ""))
        _estilo_header(ws.cell(2, j, etiqueta), bg="2E75B6")
    ws.row_dimensions[2].height = 46
    c_tipo = ws.cell(3, 1, "Estrategia")
    c_tipo.font = Font(bold=True, name="Arial", size=9, italic=True)
    c_tipo.fill = PatternFill("solid", start_color="F2F2F2")
    c_tipo.alignment = Alignment(horizontal="center", vertical="center")
    c_tipo.border = _borde_fino()
    for j, g in enumerate(grupos, 2):
        tipo = tipo_grupo.get(g, "")
        c = ws.cell(3, j, tipo)
        c.fill = PatternFill("solid", start_color=ESTRATEGIA_COLOR.get(tipo, "F2F2F2"))
        c.font = Font(bold=True, name="Arial", size=9)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = _borde_fino()
    ws.row_dimensions[3].height = 18

    fila_datos = 4
    if origen_grupo:
        c_ori = ws.cell(4, 1, "Origen")
        c_ori.font = Font(bold=True, name="Arial", size=9, italic=True)
        c_ori.fill = PatternFill("solid", start_color="F2F2F2")
        c_ori.alignment = Alignment(horizontal="center", vertical="center")
        c_ori.border = _borde_fino()
        for j, g in enumerate(grupos, 2):
            origen = origen_grupo.get(g, "")
            c = ws.cell(4, j, origen)
            c.fill = PatternFill("solid", start_color=COLOR_ORIGEN.get(origen, "F2F2F2"))
            c.font = Font(bold=True, name="Arial", size=9)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = _borde_fino()
        ws.row_dimensions[4].height = 18
        fila_datos = 5

    for i, comuna in enumerate(comunas):
        row = fila_datos + i
        es_total = comuna == FILA_TOTAL
        bg_fila = "F2F2F2" if i % 2 == 0 else "FFFFFF"
        c_com = ws.cell(row, 1, comuna)
        c_com.font = Font(bold=True, name="Arial", size=10,
                          color="FFFFFF" if es_total else "000000")
        c_com.fill = PatternFill("solid", start_color="1F4E79" if es_total else "BDD7EE")
        c_com.alignment = Alignment(vertical="center")
        c_com.border = _borde_fino()
        for j, g in enumerate(grupos, 2):
            val = pivot.loc[comuna, g]
            c = ws.cell(row, j)
            c.value = round(float(val), 2) if pd.notna(val) else "S/D"
            c.number_format = fmt_num
            if es_total:
                c.fill = PatternFill("solid", start_color="1F4E79")
                c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            else:
                c.fill = PatternFill("solid", start_color=bg_fila)
                c.font = Font(name="Arial", size=10)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = _borde_fino()

    if origen_grupo:
        row_fin = fila_datos + len(comunas) + 1
        ws.merge_cells(start_row=row_fin, start_column=1,
                       end_row=row_fin, end_column=ncols + 1)
        celda = ws.cell(row_fin, 1, LEYENDA_ORIGEN)
        celda.font = Font(italic=True, name="Arial", size=9, color="404040")
        celda.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.column_dimensions["A"].width = 26
    for j in range(2, ncols + 2):
        ws.column_dimensions[get_column_letter(j)].width = 12.5
    ws.freeze_panes = "B5" if origen_grupo else "B4"

    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:4" if origen_grupo else "1:3"
    ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.4, bottom=0.5)
    ws.print_options.horizontalCentered = True
    ws.oddFooter.center.text = f"&A — generado {date.today().isoformat()} — página &P de &N"


def _preparar_pivots(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict, dict | None]:
    df = df[df["POBLACION_OBJETIVO"].notna()].copy()
    df["col"] = df["VACUNA_DASHBOARD"].map(ETIQUETAS)
    df = df[df["col"].notna()].copy()
    df["comuna"] = df["COMUNA_CALCULO"].astype(str).str.strip()

    cols = [ETIQUETAS[k] for k in DISPLAY_ORDER if ETIQUETAS.get(k) in set(df["col"])]
    vac = df.pivot_table(index="comuna", columns="col",
                         values="VACUNAS_ADMINISTRADAS", aggfunc="sum")
    den = df.pivot_table(index="comuna", columns="col",
                         values="POBLACION_OBJETIVO", aggfunc="sum")
    vac = vac.reindex(columns=cols)
    den = den.reindex(columns=cols)
    orden = sorted(vac.index, key=_clave_orden)
    vac = vac.reindex(orden)
    den = den.reindex(orden)

    vac.loc[FILA_TOTAL] = vac.sum()
    den.loc[FILA_TOTAL] = den.sum()
    pct = (vac / den * 100).round(2)

    tipo_grupo = {ETIQUETAS[k]: VACUNA_META[k]["estrategia"]
                  for k in DISPLAY_ORDER if k in ETIQUETAS}
    origen_grupo = None
    if "ORIGEN" in df.columns:
        mapa = df.drop_duplicates("col").set_index("col")["ORIGEN"].to_dict()
        origen_grupo = {c: mapa[c] for c in cols if c in mapa}
    return pct, vac, den, tipo_grupo, origen_grupo


def _escribir_archivo(ruta: Path, pct, vac, den, tipo_grupo, origen_grupo,
                      anio: int, subtitulo: str) -> Path:
    fila_ini = 5 if origen_grupo else 4
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Cobertura %"
    _escribir_tabla(
        ws1, pct,
        f"COBERTURA VACUNAS PROGRAMÁTICAS {anio} ({subtitulo}) — Región Metropolitana (%)",
        '0.00"%"', tipo_grupo, origen_grupo,
    )
    last = fila_ini + len(pct.index) - 1
    end_col = get_column_letter(1 + len(pct.columns))
    ws1.conditional_formatting.add(
        f"B{fila_ini}:{end_col}{last}",
        ColorScaleRule(start_type="num", start_value=0, start_color="F8696B",
                       mid_type="num", mid_value=80, mid_color="FFEB84",
                       end_type="num", end_value=100, end_color="63BE7B"),
    )
    ws2 = wb.create_sheet("Vacunados")
    _escribir_tabla(
        ws2, vac,
        f"VACUNADOS PROGRAMÁTICAS {anio} ({subtitulo}) — Región Metropolitana",
        "#,##0", tipo_grupo, origen_grupo,
    )
    ws3 = wb.create_sheet("Población objetivo")
    _escribir_tabla(
        ws3, den,
        f"POBLACIÓN OBJETIVO PROGRAMÁTICAS {anio} ({subtitulo}) — Región Metropolitana",
        "#,##0", tipo_grupo, origen_grupo,
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    print(f"Excel -> {ruta.name} | comunas: {len(pct.index) - 1} | "
          f"vacunas: {len(pct.columns)} | vacunados: {int(vac.loc[FILA_TOTAL].sum()):,}")
    return ruta


def _escribir_informe_final(ruta: Path, local: pd.DataFrame, anio: int) -> Path:
    pct, vac, den, tipo_grupo, origen_grupo = _preparar_pivots(local)

    df = local[local["POBLACION_OBJETIVO"].notna()].copy()
    df["vacuna_nombre"] = df["VACUNA_DASHBOARD"].map(
        lambda k: VACUNA_META.get(k, {}).get("vacuna", k))
    df["dosis_nombre"] = df["VACUNA_DASHBOARD"].map(
        lambda k: VACUNA_META.get(k, {}).get("dosis", ""))
    res = (df.groupby(["VACUNA_DASHBOARD", "vacuna_nombre", "dosis_nombre", "ORIGEN"],
                      as_index=False)
           .agg(vacunados=("VACUNAS_ADMINISTRADAS", "sum"),
                poblacion=("POBLACION_OBJETIVO", "sum")))
    orden = {k: i for i, k in enumerate(DISPLAY_ORDER)}
    res = res.sort_values("VACUNA_DASHBOARD", key=lambda s: s.map(orden))
    res["cobertura"] = (res["vacunados"] / res["poblacion"].replace(0, pd.NA) * 100).round(2)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ncols = 6
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    _estilo_header(ws.cell(
        1, 1,
        f"INFORME FINAL — COBERTURAS VACUNAS PROGRAMÁTICAS {anio} — REGIÓN METROPOLITANA",
    ), size=13)
    ws.row_dimensions[1].height = 24
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    sub = ws.cell(2, 1, "Mezcla aprobada: cálculo propio (Usuario, base Mixta) + "
                        "resultados publicados por MINSAL, sin recalcular")
    sub.font = Font(italic=True, name="Arial", size=10)
    sub.alignment = Alignment(horizontal="left", vertical="center")

    encabezados = ["Vacuna", "Dosis", "Origen", "Vacunados",
                   "Población objetivo", "Cobertura (%)"]
    for j, h in enumerate(encabezados, 1):
        _estilo_header(ws.cell(3, j, h), bg="2E75B6")
    ws.row_dimensions[3].height = 20

    fila_ini = 4
    for i, (_, r) in enumerate(res.iterrows()):
        row = fila_ini + i
        ws.cell(row, 1, r["vacuna_nombre"]).font = Font(name="Arial", size=10)
        ws.cell(row, 2, r["dosis_nombre"]).font = Font(name="Arial", size=10)
        c_or = ws.cell(row, 3, r["ORIGEN"])
        c_or.font = Font(name="Arial", size=10, bold=True)
        c_or.fill = PatternFill("solid", start_color=COLOR_ORIGEN.get(r["ORIGEN"], "F2F2F2"))
        c_or.alignment = Alignment(horizontal="center")
        c_vac = ws.cell(row, 4, int(r["vacunados"]))
        c_vac.number_format = "#,##0"
        c_pob = ws.cell(row, 5, int(r["poblacion"]))
        c_pob.number_format = "#,##0"
        c_pct = ws.cell(row, 6, float(r["cobertura"]))
        c_pct.number_format = '0.00"%"'
        for j in range(1, ncols + 1):
            celda = ws.cell(row, j)
            celda.border = _borde_fino()
            if j >= 4:
                celda.alignment = Alignment(horizontal="center", vertical="center")
                celda.font = Font(name="Arial", size=10)
    fila_fin = fila_ini + len(res) - 1
    ws.conditional_formatting.add(
        f"F{fila_ini}:F{fila_fin}",
        ColorScaleRule(start_type="num", start_value=0, start_color="F8696B",
                       mid_type="num", mid_value=80, mid_color="FFEB84",
                       end_type="num", end_value=100, end_color="63BE7B"),
    )

    row_tot = fila_fin + 1
    ws.cell(row_tot, 1, "TOTAL REGIÓN METROPOLITANA")
    tot_vac = int(res["vacunados"].sum())
    tot_pob = int(res["poblacion"].sum())
    ws.cell(row_tot, 4, tot_vac)
    ws.cell(row_tot, 5, tot_pob)
    ws.cell(row_tot, 6, round(tot_vac / tot_pob * 100, 2))
    for j in range(1, ncols + 1):
        celda = ws.cell(row_tot, j)
        celda.font = Font(bold=True, name="Arial", size=10, color="FFFFFF")
        celda.fill = PatternFill("solid", start_color="1F4E79")
        celda.border = _borde_fino()
        if j >= 4:
            celda.alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row_tot, 4).number_format = "#,##0"
    ws.cell(row_tot, 5).number_format = "#,##0"
    ws.cell(row_tot, 6).number_format = '0.00"%"'

    notas = [
        LEYENDA_ORIGEN,
        f"Criterio por vacuna en data/prioridad_final_{anio}.csv "
        "(prioridad Usuario / MINSAL / Eliminar del cálculo).",
        "Vacunas eliminadas del cálculo (8): Hexavalente 1ª dosis, 2ª dosis y refuerzo; "
        "Meningocócica recombinante 1ª dosis, 2ª dosis y refuerzo; "
        "Neumocócica conjugada 1ª dosis y 2ª dosis.",
    ]
    for k, texto in enumerate(notas):
        row = row_tot + 2 + k
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        c = ws.cell(row, 1, texto)
        c.font = Font(italic=True, name="Arial", size=9, color="404040")
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 15
    ws.freeze_panes = "A4"
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.oddFooter.center.text = f"&A — generado {date.today().isoformat()} — página &P de &N"

    ws2 = wb.create_sheet("Cobertura %")
    _escribir_tabla(
        ws2, pct,
        f"COBERTURA VACUNAS PROGRAMÁTICAS {anio} (INFORME FINAL: USUARIO + MINSAL) — Región Metropolitana (%)",
        '0.00"%"', tipo_grupo, origen_grupo,
    )
    ws2.conditional_formatting.add(
        f"B5:{get_column_letter(1 + len(pct.columns))}{4 + len(pct.index)}",
        ColorScaleRule(start_type="num", start_value=0, start_color="F8696B",
                       mid_type="num", mid_value=80, mid_color="FFEB84",
                       end_type="num", end_value=100, end_color="63BE7B"),
    )
    ws3 = wb.create_sheet("Vacunados")
    _escribir_tabla(
        ws3, vac,
        f"VACUNADOS PROGRAMÁTICAS {anio} (INFORME FINAL: USUARIO + MINSAL) — Región Metropolitana",
        "#,##0", tipo_grupo, origen_grupo,
    )
    ws4 = wb.create_sheet("Población objetivo")
    _escribir_tabla(
        ws4, den,
        f"POBLACIÓN OBJETIVO PROGRAMÁTICAS {anio} (INFORME FINAL: USUARIO + MINSAL) — Región Metropolitana",
        "#,##0", tipo_grupo, origen_grupo,
    )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    print(f"Excel -> {ruta.name} | resumen: {len(res)} vacuna-dosis | "
          f"vacunados: {tot_vac:,} | población: {tot_pob:,}")
    return ruta


def exportar(anio: int = 2025, base: str = "SD",
             salida_dir: Path | None = None) -> list[Path]:
    cfg = cfgmod.get_config(anio)
    T = cfg.T
    salida_dir = salida_dir or cfgmod.OUTPUT_DIR
    sufijo = SUFIJOS_BASE.get(base, "SD")

    ruta_local = latest_dated_file_any(
        cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{T}_V7_{sufijo}.csv"
    )
    local = pd.read_csv(ruta_local, encoding="utf-8-sig")
    generados = []

    if base == "Final":
        generados.append(_escribir_archivo(
            salida_dir / f"coberturas_vacunas_{T}_FINAL_imprimible.xlsx",
            *_preparar_pivots(local),
            anio=anio, subtitulo="INFORME FINAL: CÁLCULO PROPIO (MIXTO) + MINSAL",
        ))
        generados.append(_escribir_informe_final(
            salida_dir / f"informe_final_coberturas_{T}.xlsx", local, anio=anio,
        ))
        return generados

    ruta_minsal = latest_dated_file_any(
        cfgmod.OUTPUT_DIR, f"coberturas_vacunas_{T}_V7_MINSAL.csv"
    )
    generados.append(_escribir_archivo(
        salida_dir / f"coberturas_vacunas_{T}_PROPIO_{base}_imprimible.xlsx",
        *_preparar_pivots(local),
        anio=anio, subtitulo=f"CÁLCULO PROPIO {base.upper()}",
    ))

    minsal = pd.read_csv(ruta_minsal, encoding="utf-8-sig")
    generados.append(_escribir_archivo(
        salida_dir / f"coberturas_vacunas_{T}_MINSAL_imprimible.xlsx",
        *_preparar_pivots(minsal),
        anio=anio, subtitulo="CORTE MINSAL",
    ))
    return generados


def main():
    ap = argparse.ArgumentParser(
        description="Excel imprimibles de coberturas (matriz comunas x vacunas)")
    ap.add_argument("--anio", type=int, default=2025)
    ap.add_argument("--base", choices=["SD", "CD", "Mixto", "Final"], default="SD",
                    help="Base local para el archivo PROPIO (default SD; Final = informe Usuario+MINSAL)")
    ap.add_argument("--salida-dir", type=Path, default=None)
    args = ap.parse_args()
    exportar(args.anio, args.base, args.salida_dir)


if __name__ == "__main__":
    main()
