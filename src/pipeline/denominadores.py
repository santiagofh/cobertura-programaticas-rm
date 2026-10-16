"""Paso 2 del pipeline: denominadores por año.

Port fiel de 2_denominadores_2025_V7.py (modo NAC crudos) + el modo
"reciclar denominadores previos" del script 2024, seleccionado por
config.nac_raw (False = reciclar).
"""

import unicodedata
from datetime import date
from glob import glob
from pathlib import Path

import pandas as pd

from .. import config_programaticas as cfgmod


def _normalizar_texto(valor) -> str:
    """Minúsculas, sin acentos y con espacios colapsados (admite NBSP)."""
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return " ".join(texto.replace("\xa0", " ").split()).lower()


def _mapa_comunas_norm() -> dict:
    return {_normalizar_texto(k): v for k, v in cfgmod.COMUNA_MAP.items()}


def _buscar_fila_header(df: pd.DataFrame, objetivo: str = "comuna") -> int:
    for i in range(min(15, len(df))):
        if _normalizar_texto(df.iloc[i, 0]) == objetivo:
            return i
    raise ValueError(f"No se encontró fila de encabezado con '{objetivo}' en el Excel.")


def _leer_matricula_mineduc(ruta: Path, hoja: str) -> pd.DataFrame:
    """Lee el layout MINEDUC RM (hoja con 'Comuna' + 1°/4°/5°/8° básico)."""
    df_esc = pd.read_excel(ruta, sheet_name=hoja, header=None)
    hdr = _buscar_fila_header(df_esc)
    data = df_esc.iloc[hdr + 1:, [0, 1, 2, 3, 4]].copy()
    data.columns = ["COMUNA", "dTpa_1basico", "VPH_4basico", "VPH_5basico", "dTpa_8basico"]
    return data.dropna(subset=["COMUNA"])


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


def _reciclar_desde_previos(DIR_OUTPUT: Path, RUN_DATE: str, T: int) -> list:
    """Reproduce generar_v7_desde_denominadores_previos() de 2024."""
    pares = [
        (f"denominador_nacimientos_{T}", f"denominador_nacimientos_{T}_V7"),
        (f"denominador_neumococica_65_{T}", f"denominador_neumococica_65_{T}_V7"),
        (f"denominador_matricula_escolar_{T}", f"denominador_matricula_escolar_{T}_V7"),
    ]
    print("\nINFO: Fuentes crudas de nacimientos no disponibles; se genera V7 desde denominadores previos validados.")
    generados = []
    for origen_base, destino_base in pares:
        origen = latest_dated_file_any(
            DIR_OUTPUT,
            f"{origen_base}_V6.csv",
            f"{origen_base}_V5_1.csv",
            f"{origen_base}_V5.csv",
            f"{origen_base}_V3_CD.csv",
        )
        df_origen = pd.read_csv(origen, encoding="utf-8-sig")
        nombre_csv = f"{RUN_DATE}_{destino_base}.csv"
        df_origen.to_csv(DIR_OUTPUT / nombre_csv, index=False, encoding="utf-8-sig")
        df_origen.to_excel(DIR_OUTPUT / f"{RUN_DATE}_{destino_base}.xlsx", index=False)
        generados.append(nombre_csv)
        print(f"  {origen.name} -> {nombre_csv}")
    print("\nOK denominadores V7 generados desde salidas previas.")
    return generados


def run(anio: int):
    cfg = cfgmod.get_config(anio)
    T = cfg.T
    RUN_DATE = date.today().isoformat()
    DIR_OUTPUT = cfgmod.OUTPUT_DIR
    DIR_OUTPUT.mkdir(exist_ok=True)

    if not cfg.nac_raw:
        return _reciclar_desde_previos(DIR_OUTPUT, RUN_DATE, T)

    RUTA_BASE_NAC = cfgmod.requerido(cfgmod.NACIMIENTO_DIR, "NACIMIENTO_DIR")
    RUTA_INE = cfgmod.requerido(cfgmod.ESTIMACIONES_CSV, "ESTIMACIONES_CSV")
    RUTA_POB_ESC = cfgmod.DATA_DIR / cfg.pob_esc_nombre
    RUTA_POB_PROG = cfgmod.DATA_DIR / cfg.pob_prog_nombre if cfg.pob_prog_nombre else None

    RUTAS_NAC = {y: RUTA_BASE_NAC / str(y) / f"NAC{y}.csv" for y in range(T - 3, T + 1)}

    if any(not ruta.exists() for ruta in RUTAS_NAC.values()):
        faltantes = "\n".join(f"  - {ruta}" for ruta in RUTAS_NAC.values() if not ruta.exists())
        raise FileNotFoundError(
            f"Faltan archivos crudos de nacimientos (SRCeI) para {T}:\n{faltantes}\n"
            f"NO se reutilizan denominadores previos: las cohortes {T} difieren de años anteriores."
        )

    COHORTES_NAC = cfgmod.cohortes_nac(T)

    # ═══ A) DENOMINADOR NACIMIENTOS ═══
    print("\n" + "=" * 65)
    print("A) DENOMINADOR NACIMIENTOS")
    print("=" * 65)
    dfs_nac = []
    for anio_nac, ruta in RUTAS_NAC.items():
        print(f"  Cargando {anio_nac}...")
        df_n = pd.read_csv(ruta, encoding="LATIN1", sep=";", low_memory=False,
                           usecols=["DIA_NAC", "MES_NAC", "ANO_NAC", "COMUNA_N", "COMUNA"])
        df_n["COMUNA_N"] = pd.to_numeric(df_n["COMUNA_N"], errors="coerce")
        df_n = df_n[df_n["COMUNA_N"].between(13000, 13999)]
        dfs_nac.append(df_n)

    nac = pd.concat(dfs_nac, ignore_index=True)
    nac["FECHA_NAC"] = pd.to_datetime(
        dict(year=nac["ANO_NAC"], month=nac["MES_NAC"], day=nac["DIA_NAC"]), errors="coerce")
    nac = nac.dropna(subset=["FECHA_NAC", "COMUNA_N"])
    nac["COMUNA_N"] = nac["COMUNA_N"].astype(int)
    print(f"  Total registros válidos RM: {len(nac):,}")

    comunas = (nac[["COMUNA_N", "COMUNA"]].drop_duplicates().sort_values("COMUNA_N").reset_index(drop=True))
    for clave, (inicio, fin, _, _) in COHORTES_NAC.items():
        mascara = nac["FECHA_NAC"].between(pd.Timestamp(inicio), pd.Timestamp(fin))
        conteo = nac[mascara].groupby("COMUNA_N").size().rename(clave)
        comunas = comunas.merge(conteo, on="COMUNA_N", how="left")
        comunas[clave] = comunas[clave].fillna(0).astype(int)

    print("\n  TOTALES REGIONALES:")
    for clave, (ini, fin, vacs, desc) in COHORTES_NAC.items():
        print(f"  {desc}: {comunas[clave].sum():,}")

    comunas.to_csv(DIR_OUTPUT / f"{RUN_DATE}_denominador_nacimientos_{T}_V7.csv", index=False, encoding="utf-8-sig")
    col_rename = {k: v[3] for k, v in COHORTES_NAC.items()}
    comunas.rename(columns=col_rename).to_excel(DIR_OUTPUT / f"{RUN_DATE}_denominador_nacimientos_{T}_V7.xlsx", index=False)
    print(f"\n  OK denominador_nacimientos_{T}.csv guardado ({len(comunas)} comunas)")

    # ═══ B) DENOMINADOR INE 65 AÑOS ═══
    print("\n" + "=" * 65)
    print("B) DENOMINADOR INE 65 AÑOS")
    print("=" * 65)
    df_ine = pd.read_csv(RUTA_INE, encoding="latin1", sep=";", low_memory=False)
    col_region = [c for c in df_ine.columns if "Region" in c and "Nombre" not in c]
    col_comuna = [c for c in df_ine.columns if "Comuna" in c and "Nombre" not in c]
    if col_region:
        df_ine = df_ine[df_ine[col_region[0]] == 13]
    elif col_comuna:
        df_ine = df_ine[df_ine[col_comuna[0]].astype(str).str.startswith("13")]
    df_ine = df_ine[df_ine["Edad"] == 65].copy()

    col_pob = f"Poblacion {T}"
    if col_pob not in df_ine.columns:
        raise ValueError(f"Columna '{col_pob}' no encontrada en INE.")
    denom_65 = (
        df_ine.groupby(["Comuna", "Nombre Comuna"])[col_pob].sum().reset_index()
        .rename(columns={col_pob: "Neumococica_Polisacarida_65", "Nombre Comuna": "COMUNA",
                         "Comuna": "COMUNA_N_INE"})
    )
    denom_65["Neumococica_Polisacarida_65"] = denom_65["Neumococica_Polisacarida_65"].astype(int)
    denom_65["COMUNA_N"] = pd.to_numeric(denom_65["COMUNA_N_INE"], errors="coerce").astype("Int64")
    denom_65 = denom_65[["COMUNA_N", "COMUNA", "Neumococica_Polisacarida_65"]]
    print(f"  Total RM 65 años: {denom_65['Neumococica_Polisacarida_65'].sum():,}")
    denom_65.to_csv(DIR_OUTPUT / f"{RUN_DATE}_denominador_neumococica_65_{T}_V7.csv", index=False, encoding="utf-8-sig")
    denom_65.to_excel(DIR_OUTPUT / f"{RUN_DATE}_denominador_neumococica_65_{T}_V7.xlsx", index=False)
    print(f"  OK denominador_neumococica_65_{T}.csv guardado ({len(denom_65)} comunas)")

    COMUNA_MAP = cfgmod.COMUNA_MAP

    # ═══ C) DENOMINADOR MATRÍCULA ESCOLAR ═══
    print("\n" + "=" * 65)
    print(f"C) DENOMINADOR MATRÍCULA ESCOLAR (Población Escolar {T})")
    print("=" * 65)
    mat_csv = None
    if RUTA_POB_ESC.exists():
        if cfg.pob_esc_hoja:
            data = _leer_matricula_mineduc(RUTA_POB_ESC, cfg.pob_esc_hoja)
        else:
            df_esc = pd.read_excel(RUTA_POB_ESC, header=None)
            data = df_esc.iloc[6:58, [0, 1, 2, 3, 4]].copy()
            data.columns = ["COMUNA", "dTpa_1basico", "VPH_4basico", "VPH_5basico", "dTpa_8basico"]
        data = data.dropna(subset=["COMUNA"])
        data["COMUNA"] = data["COMUNA"].astype(str).str.strip()
        for col in ["dTpa_1basico", "VPH_4basico", "VPH_5basico", "dTpa_8basico"]:
            data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
        mapa_norm = _mapa_comunas_norm()
        data["COMUNA_N"] = data["COMUNA"].map(_normalizar_texto).map(mapa_norm)
        unmapped = data[data["COMUNA_N"].isna()]["COMUNA"].unique()
        if len(unmapped):
            print(f"  AVISO Comunas sin mapear: {unmapped}")
        data = data.dropna(subset=["COMUNA_N"])
        data["COMUNA_N"] = data["COMUNA_N"].astype(int)
        mat_wide = data[["COMUNA_N", "COMUNA", "dTpa_1basico", "VPH_4basico", "VPH_5basico", "dTpa_8basico"]]
        mat_wide = mat_wide.sort_values("COMUNA_N").reset_index(drop=True)
        print(f"  dTpa 1° básico   : {mat_wide['dTpa_1basico'].sum():,}")
        print(f"  VPH  4° básico   : {mat_wide['VPH_4basico'].sum():,}")
        print(f"  VPH  5° básico   : {mat_wide['VPH_5basico'].sum():,}")
        print(f"  dTpa 8° básico   : {mat_wide['dTpa_8basico'].sum():,}")
        mat_csv = f"{RUN_DATE}_denominador_matricula_escolar_{T}_V7.csv"
        mat_wide.to_csv(DIR_OUTPUT / mat_csv, index=False, encoding="utf-8-sig")
        mat_wide.to_excel(DIR_OUTPUT / f"{RUN_DATE}_denominador_matricula_escolar_{T}_V7.xlsx", index=False)
        print(f"  OK denominador_matricula_escolar_{T}.csv guardado ({len(mat_wide)} comunas)")
    else:
        print(f"  AVISO: NO EXISTE {RUTA_POB_ESC.name} — matrícula escolar OMITIDA (pendiente MINEDUC {T}).")
        print("  Vacunas escolares (dTpa 1°/8°, VPH 4°/5°) quedan sin denominador.")

    # ═══ D) DENOMINADOR GESTANTES ═══
    print("\n" + "=" * 65)
    print(f"D) DENOMINADOR GESTANTES (Población programáticas {T})")
    print("=" * 65)
    gest_csv = None
    if RUTA_POB_PROG is not None and RUTA_POB_PROG.exists():
        df_prog = pd.read_excel(RUTA_POB_PROG, sheet_name=cfg.pob_prog_hoja, header=None)
        hdr = _buscar_fila_header(df_prog)
        col_gest = None
        for j, valor in enumerate(df_prog.iloc[hdr]):
            if "barazadas" in _normalizar_texto(valor):
                col_gest = j
                break
        if col_gest is None:
            raise ValueError(f"No se encontró columna de gestantes en {RUTA_POB_PROG.name}.")
        gestantes = df_prog.iloc[hdr + 1:, [0, col_gest]].copy()
        gestantes.columns = ["COMUNA", "GESTANTES_ESTIMADAS"]
        gestantes = gestantes.dropna(subset=["COMUNA"])
        gestantes["COMUNA"] = gestantes["COMUNA"].astype(str).str.strip()
        gestantes["GESTANTES_ESTIMADAS"] = (
            pd.to_numeric(gestantes["GESTANTES_ESTIMADAS"], errors="coerce").fillna(0).astype(int)
        )
        mapa_norm = _mapa_comunas_norm()
        gestantes["COMUNA_N"] = gestantes["COMUNA"].map(_normalizar_texto).map(mapa_norm)
        unmapped = gestantes[gestantes["COMUNA_N"].isna()]["COMUNA"].unique()
        if len(unmapped):
            print(f"  AVISO Comunas sin mapear: {unmapped}")
        gestantes = gestantes.dropna(subset=["COMUNA_N"])
        gestantes["COMUNA_N"] = gestantes["COMUNA_N"].astype(int)
        gestantes = (gestantes[["COMUNA_N", "COMUNA", "GESTANTES_ESTIMADAS"]]
                     .sort_values("COMUNA_N").reset_index(drop=True))
        print(f"  Gestantes RM (28+ semanas): {gestantes['GESTANTES_ESTIMADAS'].sum():,}")
        gest_csv = f"{RUN_DATE}_denominador_gestantes_{T}_V7.csv"
        gestantes.to_csv(DIR_OUTPUT / gest_csv, index=False, encoding="utf-8-sig")
        gestantes.to_excel(DIR_OUTPUT / f"{RUN_DATE}_denominador_gestantes_{T}_V7.xlsx", index=False)
        print(f"  OK denominador_gestantes_{T}.csv guardado ({len(gestantes)} comunas)")
    else:
        nombre = RUTA_POB_PROG.name if RUTA_POB_PROG is not None else "sin configurar"
        print(f"  AVISO: NO EXISTE {nombre} — dTpa gestantes queda sin denominador.")

    print("\n" + "=" * 65)
    print("OK TODOS LOS DENOMINADORES GUARDADOS EN: output/")
    print("=" * 65)
    return [
        f"{RUN_DATE}_denominador_nacimientos_{T}_V7.csv",
        f"{RUN_DATE}_denominador_neumococica_65_{T}_V7.csv",
        mat_csv,
        gest_csv,
    ]
