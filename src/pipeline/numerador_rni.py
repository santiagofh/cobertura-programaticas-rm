"""Paso 1 del pipeline: numerador RNI (vacunas no-SRP) + unificacion con SRP.

Port fiel de 1_numerador_rni_vacunas_2025_V7.py parametrizado por año.
"""

import re
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config_programaticas as cfgmod

DOSIS_MAP = {
    "0.05 ml": "DOSIS_UNICA", "0.1 ml": "DOSIS_UNICA",
    "Única": "DOSIS_UNICA", "Única (no programática)": "DOSIS_UNICA",
    "Única (50 mg)": "DOSIS_UNICA",
    "1° Dosis": "1RA_DOSIS", "1° dosis": "1RA_DOSIS", "1º dosis": "1RA_DOSIS",
    "1°dosis": "1RA_DOSIS", "1ra dosis (programática)": "1RA_DOSIS",
    "2° Dosis": "2DA_DOSIS", "2° dosis": "2DA_DOSIS", "2º dosis": "2DA_DOSIS",
    "2°dosis": "2DA_DOSIS", "2da dosis (programatica)": "2DA_DOSIS",
    "3° Dosis": "3RA_DOSIS", "3° dosis": "3RA_DOSIS",
    "3º dosis, prematuros": "3RA_DOSIS",
    "4° Dosis": "4TA_DOSIS", "4° dosis": "4TA_DOSIS", "5° Dosis": "5TA_DOSIS",
    "1er Refuerzo": "REFUERZO", "1er refuerzo": "REFUERZO",
    "1er refuerzo (programática)": "REFUERZO",
    "1er refuerzo, 12 meses": "REFUERZO",
    "1°  Refuerzo": "REFUERZO", "1° Refuerzo": "REFUERZO", "Refuerzo": "REFUERZO",
}

COLUMNAS = [
    "RUN", "PASAPORTE", "OTRO", "ID_INMUNIZACION",
    "COD_COMUNA_OCURR", "COMUNA_OCURR",
    "COD_COMUNA_RESID", "COMUNA_RESIDENCIA",
    "NOMBRE_VACUNA", "CRITERIO_ELEGIBILIDAD", "DOSIS",
    "VACUNA_ADMINISTRADA", "REGISTRO_ELIMINADO",
    "SEXO", "FECHA_NACIMIENTO", "FECHA_INMUNIZACION", "SEMANA_GESTACIONAL",
]

CRITERIOS_ESCOLARES = {
    "1basico": ["1° básico (Est. De Salud)", "1° básico (Est. Educacional)"],
    "4basico": ["4º básico (Est. de Salud)", "4º básico (Est. Educacional)"],
    "5basico": ["5º básico", "5º básico (Est. de Salud)", "5º básico (Est. Educacional)"],
    "8basico": ["8° básico (Est. De Salud)", "8° básico (Est. Educacional)"],
}


def _normalizar_texto(serie):
    return (serie.fillna("").astype(str).str.upper().str.normalize("NFKD")
            .str.encode("ascii", errors="ignore").str.decode("ascii").str.upper()
            .str.replace(r"\s+", " ", regex=True).str.strip())


def _nombre_archivo_seguro(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", errors="ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").upper()
    return texto[:120] or "SIN_NOMBRE"


def _archivar_archivos_previos(carpeta, patron, carpeta_archivo):
    carpeta_archivo.mkdir(parents=True, exist_ok=True)
    for archivo in carpeta.glob(patron):
        destino = carpeta_archivo / archivo.name
        if destino.exists():
            i = 1
            while True:
                destino = carpeta_archivo / f"{archivo.stem}__archivado_{i}{archivo.suffix}"
                if not destino.exists():
                    break
                i += 1
        archivo.replace(destino)


def run(anio: int):
    cfg = cfgmod.get_config(anio)
    T = cfg.T
    RUN_DATE = date.today().isoformat()
    DIR_OUTPUT = cfgmod.OUTPUT_DIR
    DIR_OUTPUT.mkdir(exist_ok=True)
    DIR_DETALLE_VACUNAS = DIR_OUTPUT / "DETALLE_VACUNAS"
    DIR_DETALLE_VACUNAS.mkdir(exist_ok=True)
    DIR_DETALLE_VACUNAS_BRUTO = DIR_OUTPUT / "DETALLE_VACUNAS_BRUTO"
    DIR_DETALLE_VACUNAS_BRUTO.mkdir(exist_ok=True)
    DIR_ARCHIVO_DETALLE = DIR_OUTPUT / "ARCHIVO_NO_V7" / "DETALLE_VACUNAS_PRE_UNIFICADO"
    DIR_ARCHIVO_DETALLE.mkdir(parents=True, exist_ok=True)

    RUTA_BASE_RNI = cfgmod.requerido(cfgmod.RNI_PROGRAMATICAS_DIR, "RNI_PROGRAMATICAS_DIR")
    RUTAS_ANIOS = {
        T: RUTA_BASE_RNI / f"Programaticas_{T}.parquet",
        T + 1: RUTA_BASE_RNI / f"Programaticas_{T+1}.parquet",
        T + 2: RUTA_BASE_RNI / f"Programaticas_{T+2}.parquet",
    }

    RUTAS_FALTANTES = [ruta for ruta in RUTAS_ANIOS.values() if not ruta.exists()]
    if RUTAS_FALTANTES:
        faltantes = "\n  - ".join(str(ruta) for ruta in RUTAS_FALTANTES)
        if cfg.strict_parquet:
            raise FileNotFoundError(f"Faltan archivos Parquet esperados:\n  - {faltantes}")
        print("=" * 55)
        print(f"ADVERTENCIA (ejecucion provisoria {T}):")
        print(f"  Faltan archivos Parquet esperados:\n  - {faltantes}")
        print("  Se continua SOLO con los anos disponibles.")
        print("=" * 55)

    COHORTES = cfgmod.cohortes(T)
    COHORTES_ESCOLAR = cfgmod.cohortes_escolar(T)

    lista_df = []
    print("=" * 55)
    print(f"  CARGANDO PARQUET {T}-{T+2} [V7]")
    print("=" * 55)
    for anio_parq, ruta in RUTAS_ANIOS.items():
        if not ruta.exists():
            continue
        print(f"  [{anio_parq}] Cargando...")
        df_anio = pd.read_parquet(ruta, columns=COLUMNAS)
        for col in ["COD_COMUNA_RESID", "COD_COMUNA_OCURR"]:
            df_anio[col] = pd.to_numeric(df_anio[col], errors="coerce")
        df_anio = df_anio[
            (df_anio["VACUNA_ADMINISTRADA"].astype(str).str.strip().str.upper() == "SI")
            & (df_anio["REGISTRO_ELIMINADO"].astype(str).str.strip().str.upper() == "NO")
        ].copy()
        df_anio = df_anio[
            (df_anio["COD_COMUNA_RESID"].between(13000, 13999)
             | df_anio["COD_COMUNA_OCURR"].between(13000, 13999))
        ].copy()
        lista_df.append(df_anio)

    df = pd.concat(lista_df, ignore_index=True)
    print(f"  Registros RM: {len(df):,}")

    df["FECHA_NACIMIENTO"] = pd.to_datetime(df["FECHA_NACIMIENTO"], errors="coerce")
    df["FECHA_INMUNIZACION"] = pd.to_datetime(df["FECHA_INMUNIZACION"], errors="coerce")
    df["AÑO INMUNIZACION"] = df["FECHA_INMUNIZACION"].dt.year
    df = df[df["FECHA_INMUNIZACION"].dt.year.isin([T, T + 1, T + 2])].copy()

    df["DOSIS_NORM"] = df["DOSIS"].map(DOSIS_MAP)

    df["VAC"] = (df["NOMBRE_VACUNA"].str.upper().str.replace(r"\(.*?\)", "", regex=True)
                 .str.replace("_MATERNIDAD", "", regex=False)
                 .str.replace(r"\s+", " ", regex=True).str.strip())

    def exportar_detalle_dashboard_por_vacuna(df_detalle):
        _archivar_archivos_previos(
            DIR_DETALLE_VACUNAS,
            f"{RUN_DATE}_BASE_DETALLE_VACUNAS_V7_*.csv",
            DIR_ARCHIVO_DETALLE,
        )
        sort_cols = [c for c in ["VACUNA_DASHBOARD", "COD_COMUNA_JOIN", "IDENTIFICACION_FINAL",
                                 "FECHA_INMUNIZACION", "ID_INMUNIZACION"] if c in df_detalle.columns]
        for vacuna, base_vacuna in df_detalle.sort_values(sort_cols).groupby("VACUNA_DASHBOARD", sort=True):
            detalle = base_vacuna.copy()
            detalle.insert(0, "VERSION_PROCESO", "V7")
            detalle.insert(1, "TIPO_DETALLE", "DASHBOARD_UNICO_CON_MARCA_DUPLICADO")
            detalle.insert(2, "RUN_DATE_PROCESO", RUN_DATE)
            nombre = f"{RUN_DATE}_BASE_DETALLE_VACUNAS_V7_{_nombre_archivo_seguro(vacuna)}.csv"
            detalle.to_csv(DIR_DETALLE_VACUNAS / nombre, index=False, encoding="utf-8-sig")

    def exportar_detalle_bruto_por_filtro_vacuna(df_bruto):
        _archivar_archivos_previos(
            DIR_DETALLE_VACUNAS_BRUTO,
            f"{RUN_DATE}_BASE_DETALLE_VACUNAS_BRUTO_V7_*.csv",
            DIR_OUTPUT / "ARCHIVO_NO_V7" / "DETALLE_VACUNAS_BRUTO_PREVIO",
        )
        vac = df_bruto["VAC"].fillna("")
        filtros_bruto = [
            ("VACUNA BCG", "VAC contiene BCG", vac.str.contains("BCG", na=False)),
            ("VACUNA HEPATITIS B RN", "VAC contiene HEPATITIS B y no ADULTO/DIALIZADOS/A-B",
             vac.str.contains("HEPATITIS B", na=False) & ~vac.str.contains("ADULTO|DIALIZADOS|A-B", na=False)),
            ("VACUNA HEXAVALENTE", "VAC contiene HEXAVALENTE", vac.str.contains("HEXAVALENTE", na=False)),
            ("VACUNA NEUMOCOCICA CONJUGADA", "VAC contiene NEUMOC y CONJUGADA, y no POLISACARIDA",
             vac.str.contains("NEUMOC", na=False) & vac.str.contains("CONJUGADA", na=False)
             & ~vac.str.contains("POLISACARIDA|POLISACÁRIDA", na=False)),
            ("VACUNA MENINGOCOCICA RECOMBINANTE", "VAC contiene BEXSERO", vac.str.contains("BEXSERO", na=False)),
            ("VACUNA MENINGOCOCICA CONJUGADA", "VAC contiene MENQUADFI|NIMENRIX|MENVEO|MENACTRA",
             vac.str.contains("MENQUADFI|NIMENRIX|MENVEO|MENACTRA", na=False)),
            ("VACUNA SRP TRIVIRICA", "VAC contiene SRP|TRIVIR", vac.str.contains("SRP|TRIVIR", na=False)),
            ("VACUNA HEPATITIS A PEDIATRICA", "VAC contiene HEPATITIS A y no ADULTO/A-B",
             vac.str.contains("HEPATITIS A", na=False) & ~vac.str.contains("ADULTO|A-B", na=False)),
            ("VACUNA VARICELA", "VAC contiene VARICELA", vac.str.contains("VARICELA", na=False)),
            ("VACUNA NEUMOCOCICA POLISACARIDA", "VAC contiene POLISACARIDA|POLISACARIDA con acento",
             vac.str.contains("POLISACARIDA|POLISACÁRIDA", na=False)),
            ("VACUNA DTPA TDPA", "VAC contiene DTPA|TDPA", vac.str.contains("DTPA|TDPA", na=False)),
            ("VACUNA VPH", "VAC contiene VPH|PAPILOMA|GARDASIL|CERVARIX|SILGARD",
             vac.str.contains("VPH|PAPILOMA|GARDASIL|CERVARIX|SILGARD", na=False)),
        ]
        sort_cols = [c for c in ["VAC", "NOMBRE_VACUNA", "COD_COMUNA_RESID", "COD_COMUNA_OCURR",
                                 "FECHA_INMUNIZACION", "ID_INMUNIZACION"] if c in df_bruto.columns]
        for etiqueta, filtro_descripcion, mascara in filtros_bruto:
            detalle = df_bruto.loc[mascara].sort_values(sort_cols).copy()
            if detalle.empty:
                continue
            detalle.insert(0, "VERSION_PROCESO", "V7")
            detalle.insert(1, "TIPO_DETALLE", "BRUTO_POR_FILTRO_VAC_SIN_COHORTE_DOSIS_CORTE")
            detalle.insert(2, "RUN_DATE_PROCESO", RUN_DATE)
            detalle.insert(3, "VACUNA_BRUTO", etiqueta)
            detalle.insert(4, "FILTRO_BRUTO_VAC", filtro_descripcion)
            nombre = f"{RUN_DATE}_BASE_DETALLE_VACUNAS_BRUTO_V7_{_nombre_archivo_seguro(etiqueta)}.csv"
            detalle.to_csv(DIR_DETALLE_VACUNAS_BRUTO / nombre, index=False, encoding="utf-8-sig")

    exportar_detalle_bruto_por_filtro_vacuna(df)

    df["CRITERIO_NORM"] = _normalizar_texto(df["CRITERIO_ELEGIBILIDAD"])
    df["SEXO_NORM"] = _normalizar_texto(df["SEXO"])
    df["SEMANA_GESTACIONAL_NUM"] = pd.to_numeric(df["SEMANA_GESTACIONAL"], errors="coerce")

    def en_cohorte(clave):
        i, f = COHORTES[clave]
        return df["FECHA_NACIMIENTO"].between(i, f)

    def en_cohorte_escolar(grado):
        i, f = COHORTES_ESCOLAR[grado]
        return df["FECHA_NACIMIENTO"].between(i, f)

    def en_anio_t():
        return df["FECHA_INMUNIZACION"].dt.year.isin([T, T + 1, T + 2])

    def en_seguimiento_t_t2():
        return df["FECHA_INMUNIZACION"].dt.year.isin([T, T + 1, T + 2])

    df["CLAVE_DENOMINADOR"] = None
    df["VACUNA_DASHBOARD"] = None
    df["COD_COMUNA_JOIN"] = pd.NA

    def asignar(mascara, clave, etiqueta):
        mascara = mascara.fillna(False)
        mf = mascara & df["VACUNA_DASHBOARD"].isna()
        df.loc[mf, "CLAVE_DENOMINADOR"] = clave
        df.loc[mf, "VACUNA_DASHBOARD"] = etiqueta
        df.loc[mf, "COD_COMUNA_JOIN"] = df.loc[mf, "COD_COMUNA_RESID"]

    def asignar_escolar(mascara, clave, etiqueta):
        mascara = mascara.fillna(False)
        mf = mascara & df["VACUNA_DASHBOARD"].isna()
        df.loc[mf, "CLAVE_DENOMINADOR"] = clave
        df.loc[mf, "VACUNA_DASHBOARD"] = etiqueta
        df.loc[mf, "COD_COMUNA_JOIN"] = df.loc[mf, "COD_COMUNA_OCURR"]

    CRITERIOS_ESCOLARES_NORM = {c: set(_normalizar_texto(pd.Series(v))) for c, v in CRITERIOS_ESCOLARES.items()}

    def criterio_escolar(clave):
        return df["CRITERIO_NORM"].isin(CRITERIOS_ESCOLARES_NORM[clave])

    criterio_embarazada = (df["CRITERIO_NORM"].str.contains(r"\bEMBARAZADAS?\b|\bGESTANTE\b", na=False)
                           | (df["SEMANA_GESTACIONAL_NUM"] >= 28))
    vac = df["VAC"]
    neumo_conj = vac.str.contains("NEUMOC") & vac.str.contains("CONJUGADA") & ~vac.str.contains("POLISACARIDA|POLISACÁRIDA")

    asignar(vac.str.contains("BCG") & en_cohorte("RN") & en_seguimiento_t_t2(), "BCG_RN", "VACUNA BCG")
    asignar(vac.str.contains("HEPATITIS B") & ~vac.str.contains("ADULTO|DIALIZADOS|A-B") & en_cohorte("RN") & en_anio_t(), "HepB_RN", "VACUNA HEPATITIS B RN")
    asignar(vac.str.contains("HEXAVALENTE") & (df["DOSIS_NORM"] == "1RA_DOSIS") & en_cohorte("2M") & en_seguimiento_t_t2(), "Cohorte_2M", "VACUNA HEXAVALENTE 1RA DOSIS")
    asignar(vac.str.contains("HEXAVALENTE") & (df["DOSIS_NORM"] == "2DA_DOSIS") & en_cohorte("4M") & en_seguimiento_t_t2(), "Cohorte_4M", "VACUNA HEXAVALENTE 2DA DOSIS")
    asignar(vac.str.contains("HEXAVALENTE") & (df["DOSIS_NORM"] == "3RA_DOSIS") & en_cohorte("6M") & en_seguimiento_t_t2(), "Hexavalente_3d_6m", "VACUNA HEXAVALENTE 3RA DOSIS")
    asignar(vac.str.contains("HEXAVALENTE") & (df["DOSIS_NORM"] == "REFUERZO") & en_cohorte("18M") & en_seguimiento_t_t2(), "Hexavalente_ref_18m", "VACUNA HEXAVALENTE REFUERZO")
    asignar(neumo_conj & (df["DOSIS_NORM"] == "1RA_DOSIS") & en_cohorte("2M") & en_seguimiento_t_t2(), "Cohorte_2M", "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS")
    asignar(neumo_conj & (df["DOSIS_NORM"] == "2DA_DOSIS") & en_cohorte("4M") & en_seguimiento_t_t2(), "Cohorte_4M", "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS")
    asignar(neumo_conj & (df["DOSIS_NORM"] == "REFUERZO") & en_cohorte("12M") & en_seguimiento_t_t2(), "Cohorte_12M", "VACUNA NEUMOCOCICA CONJUGADA REFUERZO")
    asignar(vac.str.contains("BEXSERO") & (df["DOSIS_NORM"] == "1RA_DOSIS") & en_cohorte("2M") & en_seguimiento_t_t2(), "Cohorte_2M", "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS")
    asignar(vac.str.contains("BEXSERO") & (df["DOSIS_NORM"] == "2DA_DOSIS") & en_cohorte("4M") & en_seguimiento_t_t2(), "Cohorte_4M", "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS")
    asignar(vac.str.contains("BEXSERO") & (df["DOSIS_NORM"] == "REFUERZO") & en_cohorte("18M") & en_seguimiento_t_t2(), "Cohorte_18M", "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO")
    asignar(vac.str.contains("MENQUADFI|NIMENRIX|MENVEO|MENACTRA") & (df["DOSIS_NORM"].isin(["DOSIS_UNICA", "REFUERZO"]) & en_cohorte("12M") & en_seguimiento_t_t2()), "Cohorte_12M", "VACUNA MENINGOCOCICA CONJUGADA DOSIS UNICA")
    asignar(vac.str.contains("HEPATITIS A") & ~vac.str.contains("ADULTO|A-B") & (df["DOSIS_NORM"].isin(["DOSIS_UNICA", "1RA_DOSIS", "2DA_DOSIS"])) & en_cohorte("18M") & en_seguimiento_t_t2(), "Cohorte_18M", "VACUNA HEPATITIS A PEDIATRICA")
    asignar(vac.str.contains("VARICELA") & (df["DOSIS_NORM"].isin(["1RA_DOSIS", "DOSIS_UNICA"])) & en_cohorte("18M") & en_seguimiento_t_t2(), "Cohorte_18M", "VACUNA VARICELA 1RA DOSIS")
    asignar(vac.str.contains("VARICELA") & (df["DOSIS_NORM"].isin(["2DA_DOSIS", "DOSIS_UNICA"])) & en_cohorte("36M") & en_seguimiento_t_t2(), "Cohorte_36M", "VACUNA VARICELA 2DA DOSIS")
    asignar(vac.str.contains("POLISACARIDA|POLISACÁRIDA") & (df["FECHA_NACIMIENTO"].dt.year == T - 65) & en_seguimiento_t_t2(), "Neumococica_Polisacarida_65", "VACUNA NEUMOCOCICA POLISACARIDA")
    asignar_escolar(vac.str.contains("DTPA|TDPA", case=False) & criterio_escolar("1basico") & (df["FECHA_INMUNIZACION"].dt.year == T), "dTpa_1basico", "VACUNA DTPA 1 BASICO")
    asignar_escolar(vac.str.contains("DTPA|TDPA", case=False) & criterio_escolar("8basico") & (df["FECHA_INMUNIZACION"].dt.year == T), "dTpa_8basico", "VACUNA DTPA 8 BASICO")
    asignar_escolar(vac.str.contains("VPH|PAPILOMA|GARDASIL|CERVARIX|SILGARD", case=False) & criterio_escolar("4basico") & (df["FECHA_INMUNIZACION"].dt.year == T), "VPH_4basico", "VACUNA VPH 4 BASICO")
    asignar_escolar(vac.str.contains("VPH|PAPILOMA|GARDASIL|CERVARIX|SILGARD", case=False) & criterio_escolar("5basico") & (df["FECHA_INMUNIZACION"].dt.year == T), "VPH_5basico", "VACUNA VPH 5 BASICO")
    asignar(vac.str.contains("DTPA|TDPA", case=False) & (df["FECHA_INMUNIZACION"].dt.year == T) & criterio_embarazada, "dTpa_Gestantes", "VACUNA DTPA GESTANTES")

    print("\n" + "=" * 60)
    print("CARGANDO SRP V7 DESDE ARCHIVO STANDALONE")
    print("=" * 60)
    ruta_srp_base = DIR_OUTPUT / f"{RUN_DATE}_base_numerador_rni_{T}_SRP_V7_nac.parquet"
    if not ruta_srp_base.exists():
        raise FileNotFoundError(
            f"No existe base SRP V7: {ruta_srp_base}\n"
            f"Ejecute primero el paso 4 (numerador_srp.py) para {T}"
        )
    srp_v7 = pd.read_parquet(ruta_srp_base)
    print(f"  Base SRP V7 cargada: {len(srp_v7):,}")

    df_no_srp = df[df["VACUNA_DASHBOARD"].notna()].copy()
    for col in ["RUN", "PASAPORTE", "OTRO"]:
        df_no_srp[col] = df_no_srp[col].astype(str).str.strip().replace(["nan", "NaN", "None", "<NA>", ""], pd.NA)
    df_no_srp["IDENTIFICACION_FINAL"] = pd.NA
    mask_run = df_no_srp["RUN"].notna()
    mask_pas = df_no_srp["PASAPORTE"].notna() & ~mask_run
    mask_otro = df_no_srp["OTRO"].notna() & ~mask_run & ~mask_pas
    df_no_srp.loc[mask_run, "IDENTIFICACION_FINAL"] = "R" + df_no_srp.loc[mask_run, "RUN"]
    df_no_srp.loc[mask_pas, "IDENTIFICACION_FINAL"] = "P" + df_no_srp.loc[mask_pas, "PASAPORTE"]
    df_no_srp.loc[mask_otro, "IDENTIFICACION_FINAL"] = "O" + df_no_srp.loc[mask_otro, "OTRO"]
    vacunas_rn = df_no_srp["VACUNA_DASHBOARD"].isin(["VACUNA BCG", "VACUNA HEPATITIS B RN"])
    mask_idinm = df_no_srp["IDENTIFICACION_FINAL"].isna() & vacunas_rn & df_no_srp["ID_INMUNIZACION"].notna()
    df_no_srp.loc[mask_idinm, "IDENTIFICACION_FINAL"] = "I" + df_no_srp.loc[mask_idinm, "ID_INMUNIZACION"].astype(str)
    df_no_srp = df_no_srp[df_no_srp["IDENTIFICACION_FINAL"].notna()].copy()
    df_no_srp["COD_COMUNA_JOIN"] = pd.to_numeric(df_no_srp["COD_COMUNA_JOIN"], errors="coerce").astype("Int64")
    df_no_srp = df_no_srp[df_no_srp["COD_COMUNA_JOIN"].between(13000, 13999)].copy()

    srp_v7 = srp_v7.rename(columns={"COD_COMUNA_RESID": "COD_COMUNA_JOIN"})
    srp_v7["COD_COMUNA_JOIN"] = pd.to_numeric(srp_v7["COD_COMUNA_JOIN"], errors="coerce").astype("Int64")

    df_final = pd.concat([df_no_srp, srp_v7], ignore_index=True)
    print(f"\nBase unificada V7 : {len(df_final):,}")

    cols_duplicado = ["IDENTIFICACION_FINAL", "VACUNA_DASHBOARD"]
    dup_por_persona = df_final.duplicated(cols_duplicado, keep=False)
    dup_por_id_inm = df_final["ID_INMUNIZACION"].notna() & df_final["ID_INMUNIZACION"].duplicated(keep=False)
    orden_sd = df_final.sort_values(["IDENTIFICACION_FINAL", "VACUNA_DASHBOARD", "FECHA_INMUNIZACION"])
    idx_eliminar_sd = orden_sd[orden_sd.duplicated(cols_duplicado, keep="first")].index

    df_final["DUPLICADO_POR_ID_INMUNIZACION"] = dup_por_id_inm
    df_final["DUPLICADO_POR_IDENTIFICACION_PERSONA"] = dup_por_persona
    df_final["DUPLICADO_ELIMINAR_SD"] = df_final.index.isin(idx_eliminar_sd)
    df_final["DUPLICADO"] = np.where(
        df_final["DUPLICADO_POR_ID_INMUNIZACION"] | df_final["DUPLICADO_POR_IDENTIFICACION_PERSONA"], "SI", "NO")
    df_final["DUPLICADO_CRITERIO"] = np.select(
        [df_final["DUPLICADO_POR_ID_INMUNIZACION"] & df_final["DUPLICADO_POR_IDENTIFICACION_PERSONA"],
         df_final["DUPLICADO_POR_ID_INMUNIZACION"],
         df_final["DUPLICADO_POR_IDENTIFICACION_PERSONA"]],
        ["ID_INMUNIZACION + IDENTIFICACION_PERSONA", "ID_INMUNIZACION", "IDENTIFICACION_PERSONA"],
        default="NO_DUPLICADO",
    )
    df_final["DUPLICADO_CRITERIO_ELIMINACION_SD"] = np.where(
        df_final["DUPLICADO_ELIMINAR_SD"], "IDENTIFICACION_PERSONA", "NO_ELIMINADO")

    df_cd = df_final.copy()
    df_sd = df_final[~df_final["DUPLICADO_ELIMINAR_SD"]].copy()
    print(f"\nBase unica V7 clasificada : {len(df_final):,}")
    print(f"  CD conserva             : {len(df_cd):,}")
    print(f"  SD conserva             : {len(df_sd):,}")

    duplicados = df_final[df_final["DUPLICADO"] == "SI"].copy()
    if not duplicados.empty:
        duplicados.to_csv(DIR_OUTPUT / f"{RUN_DATE}_duplicados_marcados_programaticas_{T}_V7.csv", index=False, encoding="utf-8-sig")
        duplicados.to_excel(DIR_OUTPUT / f"{RUN_DATE}_duplicados_marcados_programaticas_{T}_V7.xlsx", index=False)

    df_final.to_csv(DIR_OUTPUT / f"{RUN_DATE}_base_numerador_rni_{T}_V7.csv", index=False, encoding="utf-8-sig")
    df_final.to_parquet(DIR_OUTPUT / f"{RUN_DATE}_base_numerador_rni_{T}_V7.parquet", index=False)
    exportar_detalle_dashboard_por_vacuna(df_final)

    def construir_numerador(base):
        return (
            base.groupby(["COD_COMUNA_JOIN", "VACUNA_DASHBOARD", "CLAVE_DENOMINADOR"])
            .size().reset_index(name="VACUNAS_ADMINISTRADAS")
            .sort_values(["COD_COMUNA_JOIN", "VACUNA_DASHBOARD"]).reset_index(drop=True)
        )

    numerador_cd = construir_numerador(df_cd)
    numerador_sd = construir_numerador(df_sd)

    numerador_cd.to_csv(DIR_OUTPUT / f"{RUN_DATE}_numerador_rni_{T}_V7_CD.csv", index=False, encoding="utf-8-sig")
    numerador_cd.to_excel(DIR_OUTPUT / f"{RUN_DATE}_numerador_rni_{T}_V7_CD.xlsx", index=False)
    numerador_sd.to_csv(DIR_OUTPUT / f"{RUN_DATE}_numerador_rni_{T}_V7_SD.csv", index=False, encoding="utf-8-sig")
    numerador_sd.to_excel(DIR_OUTPUT / f"{RUN_DATE}_numerador_rni_{T}_V7_SD.xlsx", index=False)
    print(f"  Numerador CD: {numerador_cd['VACUNAS_ADMINISTRADAS'].sum():,}")
    print(f"  Numerador SD: {numerador_sd['VACUNAS_ADMINISTRADAS'].sum():,}")
    return df_final
