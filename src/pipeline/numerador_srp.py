"""Paso 4 del pipeline: numerador SRP (metodologia persona-level) por año.

Port fiel de 4_numerador_srp_2025_V7_nac.py parametrizado por año.
Genera, en el directorio de output:
    base_numerador_rni_{T}_SRP_V7_nac.parquet
    detalle_srp_{T}_V7_nac.csv
    numerador_rni_{T}_SRP_V7_nac.csv / .xlsx
"""

from collections import Counter
from datetime import date

import pandas as pd

from .. import config_programaticas as cfgmod

COL_SRP = [
    "RUN", "PASAPORTE", "OTRO", "ID_INMUNIZACION",
    "COD_COMUNA_RESID", "COMUNA_RESIDENCIA",
    "NOMBRE_VACUNA", "FECHA_NACIMIENTO", "FECHA_INMUNIZACION",
    "VACUNA_ADMINISTRADA", "REGISTRO_ELIMINADO",
    "CRITERIO_ELEGIBILIDAD", "DOSIS",
]
MISSING_TEXT = {"", "nan", "NaN", "None", "<NA>"}
CRITERIOS_SRP_VALIDOS = {"Vacunación Programática"}


def _clean_text(series):
    return series.astype("string").str.strip().replace({v: pd.NA for v in MISSING_TEXT})


def _filtrar_criterio_srp(df):
    criterio = _clean_text(df["CRITERIO_ELEGIBILIDAD"])
    return df[criterio.isin(CRITERIOS_SRP_VALIDOS)].copy()


def run(anio: int):
    cfg = cfgmod.get_config(anio)
    T = cfg.T
    RUN_DATE = date.today().isoformat()
    DIR_OUTPUT = cfgmod.OUTPUT_DIR
    DIR_OUTPUT.mkdir(parents=True, exist_ok=True)

    R_OLD = cfgmod.requerido(cfgmod.RNI_PROGRAMATICAS_DIR, "RNI_PROGRAMATICAS_DIR")
    DIR_SRP_CSV = cfgmod.requerido(cfgmod.RNI_SRP_DIR, "RNI_SRP_DIR")
    DIR_NAC = cfgmod.requerido(cfgmod.NACIMIENTO_DIR, "NACIMIENTO_DIR")

    def cargar_run_nac(anio_nac):
        ruta = DIR_NAC / str(anio_nac) / f"NAC{anio_nac}.csv"
        if not ruta.exists():
            print(f"  [NAC] {anio_nac}: archivo no encontrado — se omite filtro")
            return set()
        df = pd.read_csv(ruta, encoding="latin1", sep=";", usecols=["RUN"], dtype=str)
        s = set(df["RUN"].str.strip())
        del df
        print(f"  [NAC] {anio_nac}: {len(s):,} RUNs cargados ({ruta.name})")
        return s

    print("=" * 60)
    print("CARGANDO BASES DE NACIMIENTOS")
    print("=" * 60)
    nac_years = cfg.nac_filter_years
    RUNS_NAC = {y: cargar_run_nac(y) for y in nac_years}

    RUTAS_SRP_CSV = {
        2021: DIR_SRP_CSV / "SRP_2021.csv",
        2023: DIR_SRP_CSV / "SRP2023_pais.csv",
        2024: DIR_SRP_CSV / "SRP2024_pais.csv",
        2025: DIR_SRP_CSV / "SRP2025_pais.csv",
        2026: DIR_SRP_CSV / "SRP2026_pais.csv",
        # 2022 no tiene CSV
    }

    def cargar_srp_csv(anio_srp):
        ruta = RUTAS_SRP_CSV.get(anio_srp)
        if ruta is None or not ruta.exists():
            return pd.DataFrame(columns=COL_SRP), pd.Series(dtype="int64", name="CRITERIO_ELEGIBILIDAD")

        df_csv = pd.read_csv(
            ruta, encoding="latin1", sep="|",
            usecols=["RUN", "PASAPORTE", "OTRO", "ID_INMUNIZACION",
                     "COD_COMUNA_RESID", "COMUNA_RESIDENCIA",
                     "FECHA_NACIMIENTO", "FECHA_INMUNIZACION",
                     "VACUNA_ADMINISTRADA", "REGISTRO_ELIMINADO",
                     "CRITERIO_ELEGIBILIDAD", "DOSIS"],
            dtype=str, low_memory=False,
        )
        df_csv["NOMBRE_VACUNA"] = "SRP"
        for col in ["RUN", "PASAPORTE", "OTRO", "ID_INMUNIZACION", "COMUNA_RESIDENCIA",
                    "VACUNA_ADMINISTRADA", "REGISTRO_ELIMINADO", "CRITERIO_ELEGIBILIDAD"]:
            if col in df_csv.columns:
                df_csv[col] = _clean_text(df_csv[col])
        df_csv["COD_COMUNA_RESID"] = pd.to_numeric(df_csv["COD_COMUNA_RESID"], errors="coerce")
        df_csv["FECHA_NACIMIENTO"] = pd.to_datetime(df_csv["FECHA_NACIMIENTO"], errors="coerce")
        df_csv["FECHA_INMUNIZACION"] = pd.to_datetime(df_csv["FECHA_INMUNIZACION"], errors="coerce")
        df_csv = df_csv[
            (df_csv["VACUNA_ADMINISTRADA"].fillna("").str.upper() == "SI")
            & (df_csv["REGISTRO_ELIMINADO"].fillna("").str.upper() == "NO")
        ].copy()
        df_csv = df_csv[df_csv["FECHA_INMUNIZACION"].dt.year == anio_srp].copy()
        pre_csv = df_csv["CRITERIO_ELEGIBILIDAD"].value_counts(dropna=False)
        df_csv = _filtrar_criterio_srp(df_csv)
        return df_csv[COL_SRP].copy(), pre_csv

    print("=" * 60)
    print("CARGANDO SRP POR AÑO (2020-2026) — PARQUET + CSV")
    print("=" * 60)

    excluidos_por_criterio = Counter()
    lista = []
    for anio_srp in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
        ruta = R_OLD / f"Programaticas_{anio_srp}.parquet"
        if not ruta.exists():
            raise FileNotFoundError(f"No existe: {ruta}")

        df_a = pd.read_parquet(ruta, columns=COL_SRP)
        for col in ["RUN", "PASAPORTE", "OTRO", "ID_INMUNIZACION", "NOMBRE_VACUNA",
                    "COMUNA_RESIDENCIA", "VACUNA_ADMINISTRADA", "REGISTRO_ELIMINADO",
                    "CRITERIO_ELEGIBILIDAD"]:
            if col in df_a.columns:
                df_a[col] = _clean_text(df_a[col])
        df_a["COD_COMUNA_RESID"] = pd.to_numeric(df_a["COD_COMUNA_RESID"], errors="coerce")
        df_a["FECHA_NACIMIENTO"] = pd.to_datetime(df_a["FECHA_NACIMIENTO"], errors="coerce")
        df_a["FECHA_INMUNIZACION"] = pd.to_datetime(df_a["FECHA_INMUNIZACION"], errors="coerce")
        df_a = df_a[
            (df_a["VACUNA_ADMINISTRADA"].fillna("").str.upper() == "SI")
            & (df_a["REGISTRO_ELIMINADO"].fillna("").str.upper() == "NO")
        ].copy()
        df_a = df_a[df_a["FECHA_INMUNIZACION"].dt.year == anio_srp].copy()
        df_a["VAC"] = (
            df_a["NOMBRE_VACUNA"].fillna("").astype(str).str.upper()
            .str.replace(r"\(.*?\)", "", regex=True)
            .str.replace(r"\s+", " ", regex=True).str.strip()
        )
        n_srp_parquet = len(df_a[df_a["VAC"].str.contains("SRP|TRIVIR", na=False)])
        df_a = df_a[df_a["VAC"].str.contains("SRP|TRIVIR", na=False)].copy()

        pre_criterio = df_a["CRITERIO_ELEGIBILIDAD"].value_counts(dropna=False)
        df_a = _filtrar_criterio_srp(df_a)
        post_criterio = df_a["CRITERIO_ELEGIBILIDAD"].value_counts(dropna=False)
        diff_criterio = pre_criterio.sub(post_criterio, fill_value=0).astype(int)
        for k, v in diff_criterio[diff_criterio > 0].items():
            excluidos_por_criterio[k if not pd.isna(k) else "nan"] += v

        df_csv, pre_csv = cargar_srp_csv(anio_srp)
        n_csv = len(df_csv)
        post_csv = df_csv["CRITERIO_ELEGIBILIDAD"].value_counts(dropna=False)
        diff_csv = pre_csv.sub(post_csv, fill_value=0).astype(int)
        for k, v in diff_csv[diff_csv > 0].items():
            excluidos_por_criterio[k if not pd.isna(k) else "nan"] += v

        df_anio = pd.concat([df_a, df_csv], ignore_index=True)
        if n_csv > 0:
            print(f"[{anio_srp}] Parquet SRP {n_srp_parquet:,} + CSV {n_csv:,} = {len(df_anio):,}")
        else:
            print(f"[{anio_srp}] Parquet SRP {len(df_anio):,}")
        lista.append(df_anio)

    df = pd.concat(lista, ignore_index=True)
    del lista
    print(f"Total SRP: {len(df):,}")

    df["FECHA_NACIMIENTO"] = pd.to_datetime(df["FECHA_NACIMIENTO"], errors="coerce")
    df["FECHA_INMUNIZACION"] = pd.to_datetime(df["FECHA_INMUNIZACION"], errors="coerce")
    df["COD_COMUNA_RESID"] = pd.to_numeric(df["COD_COMUNA_RESID"], errors="coerce")

    df = df[df["DOSIS"].fillna("").str.upper() != "EPRO"].copy()
    print(f"Registros post excluir DOSIS=EPRO: {len(df):,}")

    n_antes = len(df)
    df = df.drop_duplicates(subset=COL_SRP, keep="first").copy()
    print(f"Duplicados eliminados       : {n_antes - len(df):,}")
    print(f"Registros SRP post-dedup    : {len(df):,}")
    df = df.drop(columns=["VAC"])

    df["IDENTIFICACION_FINAL"] = pd.NA
    m1 = df["RUN"].notna()
    m2 = df["PASAPORTE"].notna() & ~m1
    m3 = df["OTRO"].notna() & ~m1 & ~m2
    df.loc[m1, "IDENTIFICACION_FINAL"] = "R" + df.loc[m1, "RUN"]
    df.loc[m2, "IDENTIFICACION_FINAL"] = "P" + df.loc[m2, "PASAPORTE"]
    df.loc[m3, "IDENTIFICACION_FINAL"] = "O" + df.loc[m3, "OTRO"]
    df = df[df["IDENTIFICACION_FINAL"].notna()].copy()
    print(f"Personas con identificacion : {df['IDENTIFICACION_FINAL'].nunique():,}")

    print("\n" + "=" * 60)
    print("FILTRO POR BASE DE NACIMIENTOS")
    print("=" * 60)
    m_run = df["IDENTIFICACION_FINAL"].str.startswith("R")
    m_pasaporte = df["IDENTIFICACION_FINAL"].str.startswith("P")
    m_otro = df["IDENTIFICACION_FINAL"].str.startswith("O")
    anio_nac = df["FECHA_NACIMIENTO"].dt.year

    m_nac_old = m_run & (anio_nac == nac_years[0])
    m_nac_new = m_run & (anio_nac == nac_years[-1])
    m_otro_run = m_run & ~m_nac_old & ~m_nac_new

    print(f"Registros RUN     nacidos {nac_years[0]} : {m_nac_old.sum():,}")
    print(f"Registros RUN     nacidos {nac_years[-1]} : {m_nac_new.sum():,}")
    print(f"Registros RUN     otros años   : {m_otro_run.sum():,}")
    print(f"Registros PASAPORTE            : {m_pasaporte.sum():,}")
    print(f"Registros OTRO                 : {m_otro.sum():,}")

    df["_RUN_NUM"] = df.loc[m_nac_old | m_nac_new, "IDENTIFICACION_FINAL"].str[1:].str[:8]
    m_nac_old_ok = m_nac_old & df["_RUN_NUM"].isin(RUNS_NAC[nac_years[0]])
    m_nac_new_ok = m_nac_new & df["_RUN_NUM"].isin(RUNS_NAC[nac_years[-1]])
    caidos_old = m_nac_old.sum() - m_nac_old_ok.sum()
    caidos_new = m_nac_new.sum() - m_nac_new_ok.sum()
    m_keep = ~(m_nac_old | m_nac_new) | m_nac_old_ok | m_nac_new_ok
    df = df[m_keep].copy()
    df = df.drop(columns=["_RUN_NUM"])

    print(f"  RUNs {nac_years[0]} descartados (sin NAC) : {caidos_old:,}")
    print(f"  RUNs {nac_years[-1]} descartados (sin NAC) : {caidos_new:,}")
    print(f"  Total registros descartados      : {caidos_old + caidos_new:,}")
    print(f"  Personas unicas post filtro NAC  : {df['IDENTIFICACION_FINAL'].nunique():,}")
    print("=" * 60)

    total_dosis = df.groupby("IDENTIFICACION_FINAL").size().reset_index(name="TOTAL_DOSIS_SRP")
    primera_residencia = (
        df.sort_values("FECHA_INMUNIZACION").groupby("IDENTIFICACION_FINAL").head(1)[
            ["IDENTIFICACION_FINAL", "FECHA_NACIMIENTO", "FECHA_INMUNIZACION",
             "COD_COMUNA_RESID", "COMUNA_RESIDENCIA"]
        ].rename(columns={
            "FECHA_INMUNIZACION": "FECHA_INMUNIZACION_1RA",
            "COD_COMUNA_RESID": "COD_COMUNA_RESID_1RA",
            "COMUNA_RESIDENCIA": "COMUNA_RESIDENCIA_1RA",
        })
    )
    ultima_residencia = (
        df.sort_values("FECHA_INMUNIZACION").groupby("IDENTIFICACION_FINAL").tail(1)[
            ["IDENTIFICACION_FINAL", "FECHA_INMUNIZACION", "COD_COMUNA_RESID", "COMUNA_RESIDENCIA"]
        ].rename(columns={
            "FECHA_INMUNIZACION": "FECHA_INMUNIZACION_2DA",
            "COD_COMUNA_RESID": "COD_COMUNA_RESID_2DA",
            "COMUNA_RESIDENCIA": "COMUNA_RESIDENCIA_2DA",
        })
    )
    personas = (
        primera_residencia
        .merge(ultima_residencia, on="IDENTIFICACION_FINAL", how="left")
        .merge(total_dosis, on="IDENTIFICACION_FINAL", how="left")
    )

    print("\n" + "=" * 40)
    print("AUDITORIA SRP")
    print("=" * 40)
    print(f"Personas unicas SRP          : {personas['IDENTIFICACION_FINAL'].nunique():,}")
    print(f"Personas con >=1 dosis       : {(personas['TOTAL_DOSIS_SRP'] >= 1).sum():,}")
    print(f"Personas con >=2 dosis       : {(personas['TOTAL_DOSIS_SRP'] >= 2).sum():,}")

    cohorte_12m = personas[personas["FECHA_NACIMIENTO"].between(f"{T-1}-01-01", f"{T-1}-12-31")].copy()
    cohorte_36m = personas[personas["FECHA_NACIMIENTO"].between(f"{T-3}-01-01", f"{T-3}-12-31")].copy()
    print(f"Cohorte 12M (nacidos {T-1})        : {len(cohorte_12m):,}")
    print(f"Cohorte 36M (nacidos {T-3})        : {len(cohorte_36m):,}")

    srp_1 = cohorte_12m[cohorte_12m["TOTAL_DOSIS_SRP"] >= 1].copy()
    srp_1["VACUNA_DASHBOARD"] = "VACUNA SRP (TRIVIRICA) 1RA DOSIS"
    srp_1["CLAVE_DENOMINADOR"] = "Cohorte_12M"
    srp_1["COD_COMUNA_RESID"] = srp_1["COD_COMUNA_RESID_1RA"]
    srp_1["FECHA_INMUNIZACION"] = srp_1["FECHA_INMUNIZACION_1RA"]

    srp_2 = cohorte_36m[cohorte_36m["TOTAL_DOSIS_SRP"] >= 2].copy()
    srp_2["VACUNA_DASHBOARD"] = "VACUNA SRP (TRIVIRICA) 2DA DOSIS"
    srp_2["CLAVE_DENOMINADOR"] = "Cohorte_36M"
    srp_2["COD_COMUNA_RESID"] = srp_2["COD_COMUNA_RESID_2DA"]
    srp_2["FECHA_INMUNIZACION"] = srp_2["FECHA_INMUNIZACION_2DA"]

    base_final = pd.concat([srp_1, srp_2], ignore_index=True)
    for col in ["COD_COMUNA_RESID", "COD_COMUNA_RESID_1RA", "COD_COMUNA_RESID_2DA"]:
        base_final[col] = pd.to_numeric(base_final[col], errors="coerce")

    base_final = base_final[base_final["COD_COMUNA_RESID"].between(13000, 13999)].copy()
    print(f"\nBase final RM               : {len(base_final):,}")

    numerador = (
        base_final
        .groupby(["COD_COMUNA_RESID", "VACUNA_DASHBOARD", "CLAVE_DENOMINADOR"])
        .size().reset_index(name="VACUNAS_ADMINISTRADAS")
        .rename(columns={"COD_COMUNA_RESID": "COD_COMUNA_JOIN"})
        .sort_values(["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"])
        .reset_index(drop=True)
    )
    n1 = numerador[numerador["VACUNA_DASHBOARD"].str.contains("1RA", na=False)]["VACUNAS_ADMINISTRADAS"].sum()
    n2 = numerador[numerador["VACUNA_DASHBOARD"].str.contains("2DA", na=False)]["VACUNAS_ADMINISTRADAS"].sum()
    print(f"Numerador 1RA DOSIS         : {n1:,}")
    print(f"Numerador 2DA DOSIS         : {n2:,}")
    print(f"Total                       : {numerador['VACUNAS_ADMINISTRADAS'].sum():,}")
    print("=" * 60)

    base_final.to_parquet(DIR_OUTPUT / f"{RUN_DATE}_base_numerador_rni_{T}_SRP_V7_nac.parquet", index=False)
    base_final.to_csv(DIR_OUTPUT / f"{RUN_DATE}_detalle_srp_{T}_V7_nac.csv", index=False, encoding="utf-8-sig")
    numerador.to_csv(DIR_OUTPUT / f"{RUN_DATE}_numerador_rni_{T}_SRP_V7_nac.csv", index=False, encoding="utf-8-sig")
    numerador.to_excel(DIR_OUTPUT / f"{RUN_DATE}_numerador_rni_{T}_SRP_V7_nac.xlsx", index=False)
    print(f"\nExportado en {DIR_OUTPUT}")
    return numerador
