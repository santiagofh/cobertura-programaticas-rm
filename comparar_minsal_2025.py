"""Compara las coberturas Programáticas 2025 RM calculadas contra el corte MINSAL 2026-10-09.

Uso:
    python comparar_minsal_2025.py            # compara variante SD (por defecto)
    python comparar_minsal_2025.py --tipo CD

Genera output/comparacion_programaticas_2025_vs_minsal.xlsx (Resumen + Detalle).
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src import config_programaticas as cfgmod  # noqa: E402

CORTE_DIR = (
    BASE_DIR.parent / "CORTE MINSAL 2026-10-09" / "PROGRAMATICAS 2025"
)
SALIDA_XLSX = cfgmod.OUTPUT_DIR / "comparacion_programaticas_2025_vs_minsal.xlsx"

MAPA_VACUNAS = {
    "BCG": {"unica": "VACUNA BCG"},
    "HEP A": {"unica": "VACUNA HEPATITIS A PEDIATRICA"},
    "HEP B": {"unica": "VACUNA HEPATITIS B RN"},
    "HEXAVALENTE": {
        "1° dosis": "VACUNA HEXAVALENTE 1RA DOSIS",
        "2° dosis": "VACUNA HEXAVALENTE 2DA DOSIS",
        "3° dosis": "VACUNA HEXAVALENTE 3RA DOSIS",
        "refuerzo": "VACUNA HEXAVALENTE REFUERZO",
    },
    "MENINGO CONJUGADA": {"unica": "VACUNA MENINGOCOCICA CONJUGADA DOSIS UNICA"},
    "MENINGO RECO": {
        "1° dosis": "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS",
        "2° dosis": "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS",
        "refuerzo": "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO",
    },
    "NEUMO POLI": {"unica": "VACUNA NEUMOCOCICA POLISACARIDA"},
    "NEUMOCO": {
        "1° dosis": "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS",
        "2° dosis": "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS",
        "refuerzo": "VACUNA NEUMOCOCICA CONJUGADA REFUERZO",
    },
    "SRP TRIVIRICA": {
        "1° dosis": "VACUNA SRP (TRIVIRICA) 1RA DOSIS",
        "2° dosis": "VACUNA SRP (TRIVIRICA) 2DA DOSIS",
    },
    "VARICELA": {
        "1° dosis": "VACUNA VARICELA 1RA DOSIS",
        "2° dosis": "VACUNA VARICELA 2DA DOSIS",
    },
    "DTPA ESCOLAR": {
        "1° refuerzo": "VACUNA DTPA 1 BASICO",
        "2° refuerzo": "VACUNA DTPA 8 BASICO",
    },
    "DTPA GESTANTES": {"unica": "VACUNA DTPA GESTANTES"},
    "VPH": {"1° dosis o unica": "VACUNA VPH 4 BASICO"},
}

ORDEN_CLAVES = list(MAPA_VACUNAS)


def _norm(texto) -> str:
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


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


def _clave_desde_nombre(nombre: str):
    for clave in ORDEN_CLAVES:
        if clave in nombre:
            return clave
    return None


def _latest_dated(patron: str) -> Path | None:
    candidatos = sorted(cfgmod.OUTPUT_DIR.glob(f"????-??-??_{patron}"))
    if candidatos:
        return candidatos[-1]
    legacy = cfgmod.OUTPUT_DIR / patron
    return legacy if legacy.exists() else None


def main():
    ap = argparse.ArgumentParser(description="Comparacion Programaticas 2025 vs corte MINSAL")
    ap.add_argument("--tipo", choices=["SD", "CD"], default="SD")
    args = ap.parse_args()

    T = 2025
    ruta_cov = _latest_dated(f"coberturas_vacunas_{T}_V7_{args.tipo}.csv")
    ruta_num = _latest_dated(f"numerador_rni_{T}_V7_{args.tipo}.csv")
    if ruta_cov is None or ruta_num is None:
        raise FileNotFoundError("No se encontraron coberturas/numerador 2025 en output/")
    print(f"Coberturas usuario: {ruta_cov.name}")
    print(f"Numerador  usuario: {ruta_num.name}")

    cov = pd.read_csv(ruta_cov, encoding="utf-8-sig")
    cov["COD"] = pd.to_numeric(cov["COD_COMUNA_JOIN"], errors="coerce").astype("Int64")
    num = pd.read_csv(ruta_num, encoding="utf-8-sig")
    num["COD"] = pd.to_numeric(num["COD_COMUNA_JOIN"], errors="coerce").astype("Int64")

    usuario = pd.concat(
        [
            cov[["COD", "VACUNA_DASHBOARD", "VACUNAS_ADMINISTRADAS",
                 "POBLACION_OBJETIVO", "PORC_COBERTURA"]],
            num[["COD", "VACUNA_DASHBOARD", "VACUNAS_ADMINISTRADAS"]].assign(
                POBLACION_OBJETIVO=pd.NA, PORC_COBERTURA=pd.NA),
        ],
        ignore_index=True,
    )
    usuario = usuario.groupby(["COD", "VACUNA_DASHBOARD"], as_index=False).first()

    mapa_comuna = {_norm(k): v for k, v in cfgmod.COMUNA_MAP.items()}

    registros = []
    resumen = []
    for archivo in sorted(CORTE_DIR.glob("*.csv")):
        clave = _clave_desde_nombre(archivo.name)
        if clave is None:
            print(f"AVISO: sin mapeo de vacuna para {archivo.name}")
            continue
        minsal = pd.read_csv(archivo, encoding="utf-8-sig", dtype=str)
        col_comuna = "Comuna" if "Comuna" in minsal.columns else "Comuna de Ocurrencia"
        minsal["vacunados"] = _num_chileno(minsal["Vacunados"])
        minsal["poblacion"] = _num_chileno(minsal["Población"])
        minsal["pct"] = _pct_chileno(minsal["Cobertura"])
        minsal["dosis_norm"] = minsal["Dosis"].map(_norm)

        total = minsal[minsal["Región"].isna()]
        detalle = minsal[minsal["Región"] == "Metropolitana de Santiago"].copy()
        detalle["COD"] = detalle[col_comuna].map(lambda nombre: mapa_comuna.get(_norm(nombre)))
        sin_codigo = detalle[detalle["COD"].isna()][col_comuna].unique()
        if len(sin_codigo):
            print(f"AVISO {archivo.name}: comunas sin codigo -> {list(sin_codigo)}")

        for dosis_norm, vacuna in MAPA_VACUNAS[clave].items():
            filas_min = detalle[detalle["dosis_norm"] == dosis_norm]
            if filas_min.empty:
                continue
            usa = usuario[usuario["VACUNA_DASHBOARD"] == vacuna].rename(
                columns={"VACUNAS_ADMINISTRADAS": "usuario_vacunados",
                         "POBLACION_OBJETIVO": "usuario_poblacion",
                         "PORC_COBERTURA": "usuario_pct"})
            comp = filas_min.merge(usa, on="COD", how="left")
            comp["dif_vacunados"] = comp["vacunados"] - comp["usuario_vacunados"]
            comp["dif_poblacion"] = comp["poblacion"] - comp["usuario_poblacion"]
            comp["dif_pp"] = (comp["pct"] - comp["usuario_pct"]).round(2)
            comp["vacuna_minsal"] = clave
            comp["dosis_minsal"] = dosis_norm
            comp["vacuna_usuario"] = vacuna
            comp["comuna"] = comp[col_comuna].str.strip()
            registros.append(comp[[
                "vacuna_minsal", "dosis_minsal", "vacuna_usuario", "comuna", "COD",
                "vacunados", "usuario_vacunados", "dif_vacunados",
                "poblacion", "usuario_poblacion", "dif_poblacion",
                "pct", "usuario_pct", "dif_pp"]])

            fila_total = total[total["dosis_norm"] == dosis_norm]
            min_tot_vac = fila_total["vacunados"].iloc[0] if len(fila_total) else comp["vacunados"].sum()
            min_tot_pob = fila_total["poblacion"].iloc[0] if len(fila_total) else comp["poblacion"].sum()
            min_tot_pct = fila_total["pct"].iloc[0] if len(fila_total) else pd.NA
            usr_tot_vac = comp["usuario_vacunados"].sum()
            usr_tot_pob = comp["usuario_poblacion"].sum()
            usr_tot_pct = (usr_tot_vac / usr_tot_pob * 100) if usr_tot_pob and usr_tot_pob > 0 else pd.NA
            n_dif = int((comp["dif_vacunados"].fillna(0) != 0).sum())
            max_dif = comp["dif_vacunados"].abs().max()
            n_pp_ok = int((comp["dif_pp"].abs() <= 0.5).sum()) if comp["dif_pp"].notna().any() else 0
            n_pp = int(comp["dif_pp"].notna().sum())
            resumen.append({
                "vacuna": clave, "dosis": dosis_norm, "vacuna_usuario": vacuna,
                "minsal_vacunados": min_tot_vac, "usuario_vacunados": usr_tot_vac,
                "dif_vacunados": min_tot_vac - usr_tot_vac,
                "minsal_poblacion": min_tot_pob,
                "usuario_poblacion": usr_tot_pob if pd.notna(usr_tot_pob) else pd.NA,
                "minsal_pct": min_tot_pct,
                "usuario_pct": round(usr_tot_pct, 2) if pd.notna(usr_tot_pct) else pd.NA,
                "comunas_dif_vac": n_dif,
                "max_abs_dif_vac": max_dif,
                "comunas_pp_ok": n_pp_ok, "comunas_pp_total": n_pp,
            })

    detalle_df = pd.concat(registros, ignore_index=True)
    resumen_df = pd.DataFrame(resumen)

    with pd.ExcelWriter(SALIDA_XLSX, engine="openpyxl") as writer:
        resumen_df.to_excel(writer, sheet_name="Resumen", index=False)
        detalle_df.to_excel(writer, sheet_name="Detalle", index=False)

    print("=" * 110)
    print(f"PROGRAMATICAS {T} RM — usuario ({args.tipo}, DATA 2026-10-09) vs MINSAL (corte 2026-10-09)")
    print("=" * 110)
    vista = resumen_df.copy()
    vista["minsal_pct"] = pd.to_numeric(vista["minsal_pct"], errors="coerce")
    vista["usuario_pct"] = pd.to_numeric(vista["usuario_pct"], errors="coerce")
    vista["dif_%"] = (vista["minsal_pct"] - vista["usuario_pct"]).round(2)
    print(vista[["vacuna", "dosis", "minsal_vacunados", "usuario_vacunados", "dif_vacunados",
                 "minsal_pct", "usuario_pct", "dif_%", "comunas_dif_vac",
                 "max_abs_dif_vac", "comunas_pp_ok", "comunas_pp_total"]].to_string(index=False))
    print(f"\nGuardado: {SALIDA_XLSX}")


if __name__ == "__main__":
    main()
