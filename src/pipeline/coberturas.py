"""Paso 3 del pipeline: calculo de coberturas CD y SD por año.

Port fiel de 3_calcular_coberturas_2025_V7.py (superconjunto: matricula
escolar y gestantes opcionales con omision via INFO), parametrizado por año.
"""

from datetime import date
from glob import glob
from pathlib import Path

import pandas as pd

from .. import config_programaticas as cfgmod


def latest_dated_file(dir_path: Path, base_name: str) -> Path:
    candidates = sorted(glob(str(dir_path / f"????-??-??_{base_name}")))
    if candidates:
        return Path(candidates[-1])
    legacy = dir_path / base_name
    if legacy.exists():
        return legacy
    raise FileNotFoundError(f"No se encontro archivo para {base_name} en {dir_path}")


def latest_dated_file_any(dir_path: Path, *base_names: str) -> Path:
    for base_name in base_names:
        try:
            return latest_dated_file(dir_path, base_name)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"No se encontro archivo para {base_names} en {dir_path}")


def _cargar_denominadores(cfg, DIR_OUTPUT: Path, DIR_DATA: Path):
    T = cfg.T
    ruta_denominador = latest_dated_file_any(DIR_OUTPUT, *cfg.fallback_nac)
    ruta_denom_65 = latest_dated_file_any(DIR_OUTPUT, *cfg.fallback_65)

    ruta_matricula = None
    try:
        ruta_matricula = latest_dated_file_any(DIR_OUTPUT, *cfg.fallback_mat)
    except FileNotFoundError:
        print(f"INFO: matrícula escolar {T} no disponible - vacunas escolares se omiten")

    denominador_wide = pd.read_csv(ruta_denominador, encoding="utf-8-sig")
    denom_65 = pd.read_csv(ruta_denom_65, encoding="utf-8-sig")
    matricula = pd.read_csv(ruta_matricula, encoding="utf-8-sig") if ruta_matricula is not None else None

    denom_gestantes = None
    try:
        ruta_gestantes = latest_dated_file_any(DIR_OUTPUT, *cfg.fallback_gest)
        print("Cargando denominador gestantes...")
        denom_gestantes = pd.read_csv(ruta_gestantes, encoding="utf-8-sig")
    except FileNotFoundError:
        try:
            ruta_gestantes = latest_dated_file(DIR_DATA, f"denominador_gestantes_{T}.csv")
            print("Cargando denominador gestantes (fallback data)...")
            denom_gestantes = pd.read_csv(ruta_gestantes, encoding="utf-8-sig")
        except FileNotFoundError:
            print(f"INFO: denominador_gestantes_{T}.csv no encontrado - dTpa gestantes se omite")

    return denominador_wide, denom_65, matricula, denom_gestantes


def _construir_denominador_long(denominador_wide, denom_65, matricula, denom_gestantes):
    cols_cohorte = [c for c in denominador_wide.columns if c not in ("COMUNA_N", "COMUNA")]
    denominador_long = denominador_wide.melt(
        id_vars=["COMUNA_N", "COMUNA"], value_vars=cols_cohorte,
        var_name="CLAVE_DEN", value_name="POBLACION_OBJETIVO",
    )[["COMUNA_N", "CLAVE_DEN", "POBLACION_OBJETIVO"]]

    denom_65_long = (
        denom_65.assign(CLAVE_DEN="Neumococica_Polisacarida_65")
        .rename(columns={"Neumococica_Polisacarida_65": "POBLACION_OBJETIVO"})
        [["COMUNA_N", "CLAVE_DEN", "POBLACION_OBJETIVO"]]
    )
    partes = [denominador_long, denom_65_long]

    if matricula is not None:
        cols_matricula = ["dTpa_1basico", "VPH_4basico", "dTpa_8basico"]
        if "VPH_5basico" in matricula.columns:
            cols_matricula.append("VPH_5basico")
        matricula_long = matricula.melt(
            id_vars=["COMUNA_N", "COMUNA"], value_vars=cols_matricula,
            var_name="CLAVE_DEN", value_name="POBLACION_OBJETIVO",
        )[["COMUNA_N", "CLAVE_DEN", "POBLACION_OBJETIVO"]]
        partes.append(matricula_long)

    if denom_gestantes is not None:
        denom_gest_long = (
            denom_gestantes.assign(CLAVE_DEN="dTpa_Gestantes")
            .rename(columns={"GESTANTES_ESTIMADAS": "POBLACION_OBJETIVO"})
            [["COMUNA_N", "CLAVE_DEN", "POBLACION_OBJETIVO"]]
        )
        partes.append(denom_gest_long)

    denominador_long = pd.concat(partes, ignore_index=True)
    denominador_long["COMUNA_N"] = pd.to_numeric(denominador_long["COMUNA_N"], errors="coerce").astype("Int64")
    denominador_long["POBLACION_OBJETIVO"] = pd.to_numeric(denominador_long["POBLACION_OBJETIVO"], errors="coerce")
    return denominador_long


def _build_comuna_map(*dfs):
    mapa = {}
    for d in dfs:
        if d is None or "COMUNA_N" not in d.columns or "COMUNA" not in d.columns:
            continue
        tmp = d[["COMUNA_N", "COMUNA"]].copy()
        tmp["COMUNA_N"] = pd.to_numeric(tmp["COMUNA_N"], errors="coerce")
        tmp = tmp.dropna(subset=["COMUNA_N", "COMUNA"])
        for _, row in tmp.iterrows():
            code = int(row["COMUNA_N"])
            name = str(row["COMUNA"]).strip()
            if not name:
                continue
            if code not in mapa or (mapa[code].isdigit() and not name.isdigit()):
                mapa[code] = name
    return mapa


def run(anio: int):
    cfg = cfgmod.get_config(anio)
    T = cfg.T
    RUN_DATE = date.today().isoformat()
    DIR_OUTPUT = cfgmod.OUTPUT_DIR
    DIR_DATA = cfgmod.DATA_DIR

    denominador_wide, denom_65, matricula, denom_gestantes = _cargar_denominadores(cfg, DIR_OUTPUT, DIR_DATA)
    denominador_long = _construir_denominador_long(denominador_wide, denom_65, matricula, denom_gestantes)
    comuna_map = _build_comuna_map(denominador_wide, denom_65, matricula, denom_gestantes)

    claves_omitidas = set()
    if matricula is None:
        claves_omitidas |= {"dTpa_1basico", "VPH_4basico", "VPH_5basico", "dTpa_8basico"}
    if denom_gestantes is None:
        claves_omitidas |= {"dTpa_Gestantes"}

    print(f"\nClaves en denominador V7: {sorted(denominador_long['CLAVE_DEN'].dropna().unique())}")

    def calcular_cobertura(tipo_base):
        nonlocal claves_omitidas
        ruta_numerador = latest_dated_file(DIR_OUTPUT, f"numerador_rni_{T}_V7_{tipo_base}.csv")
        print("\n" + "=" * 70)
        print(f"CALCULANDO COBERTURAS V7_{tipo_base}")
        print("=" * 70)
        print(f"Cargando numerador: {ruta_numerador.name}")
        numerador = pd.read_csv(ruta_numerador, encoding="utf-8-sig")
        numerador["CLAVE_DEN"] = numerador["CLAVE_DENOMINADOR"]
        numerador["COD_COMUNA_JOIN"] = pd.to_numeric(numerador["COD_COMUNA_JOIN"], errors="coerce").astype("Int64")

        if claves_omitidas:
            pendientes = sorted(set(numerador["CLAVE_DEN"].dropna().unique()) & claves_omitidas)
            if pendientes:
                afectadas = sorted(numerador.loc[numerador["CLAVE_DEN"].isin(pendientes), "VACUNA_DASHBOARD"].unique())
                print(f"INFO: vacunas sin denominador disponible {T} se omiten: {afectadas}")
                numerador = numerador[~numerador["CLAVE_DEN"].isin(claves_omitidas)].copy()

        claves_num = set(numerador["CLAVE_DEN"].dropna().unique())
        claves_den = set(denominador_long["CLAVE_DEN"].dropna().unique())
        sin_den = sorted(claves_num - claves_den)
        if sin_den:
            raise ValueError(f"Claves del numerador V7_{tipo_base} sin denominador: {sin_den}")
        print("OK Todas las claves del numerador tienen denominador")

        coberturas = numerador.merge(
            denominador_long[["COMUNA_N", "CLAVE_DEN", "POBLACION_OBJETIVO"]],
            left_on=["COD_COMUNA_JOIN", "CLAVE_DEN"], right_on=["COMUNA_N", "CLAVE_DEN"], how="left",
        ).drop(columns="COMUNA_N")

        sin_denom = coberturas[coberturas["POBLACION_OBJETIVO"].isna()]
        if not sin_denom.empty:
            detalle = sin_denom[["COD_COMUNA_JOIN", "VACUNA_DASHBOARD", "CLAVE_DENOMINADOR"]].drop_duplicates()
            raise ValueError(f"Registros sin denominador en V7_{tipo_base}:\n{detalle.to_string(index=False)}")

        coberturas["PORC_COBERTURA"] = (
            coberturas["VACUNAS_ADMINISTRADAS"] / coberturas["POBLACION_OBJETIVO"].replace(0, pd.NA) * 100
        ).round(1).fillna(0)

        coberturas = coberturas[[
            "COD_COMUNA_JOIN", "VACUNA_DASHBOARD", "CLAVE_DENOMINADOR",
            "VACUNAS_ADMINISTRADAS", "POBLACION_OBJETIVO", "PORC_COBERTURA",
        ]].sort_values(["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"]).reset_index(drop=True)
        coberturas.insert(1, "COMUNA_CALCULO", coberturas["COD_COMUNA_JOIN"].map(comuna_map))

        num_regional = (
            coberturas.groupby(["VACUNA_DASHBOARD", "CLAVE_DENOMINADOR"], as_index=False)
            .agg(VACUNAS_ADMINISTRADAS=("VACUNAS_ADMINISTRADAS", "sum"))
        )
        den_regional = (
            denominador_long.groupby("CLAVE_DEN", as_index=False)
            .agg(POBLACION_OBJETIVO=("POBLACION_OBJETIVO", "sum"))
            .rename(columns={"CLAVE_DEN": "CLAVE_DENOMINADOR"})
        )
        resumen_regional = num_regional.merge(den_regional, on="CLAVE_DENOMINADOR", how="left")
        resumen_regional["PORC_COBERTURA"] = (
            resumen_regional["VACUNAS_ADMINISTRADAS"] / resumen_regional["POBLACION_OBJETIVO"].replace(0, pd.NA) * 100
        ).round(1).fillna(0)

        print(resumen_regional[["VACUNA_DASHBOARD", "VACUNAS_ADMINISTRADAS",
                                "POBLACION_OBJETIVO", "PORC_COBERTURA"]].to_string(index=False))

        coberturas.to_csv(DIR_OUTPUT / f"{RUN_DATE}_coberturas_vacunas_{T}_V7_{tipo_base}.csv",
                          index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(DIR_OUTPUT / f"{RUN_DATE}_coberturas_vacunas_{T}_V7_{tipo_base}.xlsx",
                            engine="openpyxl") as writer:
            coberturas.to_excel(writer, sheet_name="Por_Comuna", index=False)
            resumen_regional.to_excel(writer, sheet_name="Resumen_Regional", index=False)
        print(f"\nOK Guardado V7_{tipo_base} para {T}")
        return coberturas, resumen_regional

    calcular_cobertura("CD")
    calcular_cobertura("SD")
    return True
