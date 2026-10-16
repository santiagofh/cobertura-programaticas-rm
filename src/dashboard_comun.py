"""Dashboard comun de coberturas de vacunas programaticas, parametrizado por año.

Espejo de la fuente oficial publicada (sin recalcular):
  - 2025: corte MINSAL 2026-10-09        -> coberturas_vacunas_2025_V7_MINSAL.csv
  - 2024: Informe Ejecutivo 2024 (cierre) -> coberturas_vacunas_2024_V7_INFORME.csv
"""

from io import BytesIO
from pathlib import Path
from glob import glob

import pandas as pd
import streamlit as st

from . import config_programaticas as cfgmod

VACUNA_META = {
    "VACUNA BCG": {"vacuna": "BCG", "dosis": "Dosis única", "grupo": "Recién nacidos", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA HEPATITIS B RN": {"vacuna": "Hepatitis B RN", "dosis": "Dosis única", "grupo": "Recién nacidos", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA HEXAVALENTE 1RA DOSIS": {"vacuna": "Hexavalente", "dosis": "1ra dosis", "grupo": "2 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS": {"vacuna": "Neumocócica conjugada", "dosis": "1ra dosis", "grupo": "2 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS": {"vacuna": "Meningocócica recombinante", "dosis": "1ra dosis", "grupo": "2 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA HEXAVALENTE 2DA DOSIS": {"vacuna": "Hexavalente", "dosis": "2da dosis", "grupo": "4 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS": {"vacuna": "Neumocócica conjugada", "dosis": "2da dosis", "grupo": "4 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS": {"vacuna": "Meningocócica recombinante", "dosis": "2da dosis", "grupo": "4 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA HEXAVALENTE 3RA DOSIS": {"vacuna": "Hexavalente", "dosis": "3ra dosis", "grupo": "6 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA MENINGOCOCICA CONJUGADA DOSIS UNICA": {"vacuna": "Meningocócica conjugada", "dosis": "Dosis única", "grupo": "12 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA SRP (TRIVIRICA) 1RA DOSIS": {"vacuna": "SRP (Trivirica)", "dosis": "1ra dosis", "grupo": "12 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA NEUMOCOCICA CONJUGADA REFUERZO": {"vacuna": "Neumocócica conjugada", "dosis": "Refuerzo", "grupo": "12 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA HEPATITIS A PEDIATRICA": {"vacuna": "Hepatitis A pediátrica", "dosis": "Dosis única", "grupo": "18 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA VARICELA 1RA DOSIS": {"vacuna": "Varicela", "dosis": "1ra dosis", "grupo": "18 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA HEXAVALENTE REFUERZO": {"vacuna": "Hexavalente", "dosis": "Refuerzo", "grupo": "18 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO": {"vacuna": "Meningocócica recombinante", "dosis": "Refuerzo", "grupo": "18 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA SRP (TRIVIRICA) 2DA DOSIS": {"vacuna": "SRP (Trivirica)", "dosis": "2da dosis", "grupo": "36 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA VARICELA 2DA DOSIS": {"vacuna": "Varicela", "dosis": "2da dosis", "grupo": "36 meses", "estrategia": "Infantil", "fuente": "SRCeI"},
    "VACUNA DTPA 1 BASICO": {"vacuna": "dTpa", "dosis": "1er básico", "grupo": "Escolar", "estrategia": "Escolar", "fuente": "Mineduc", "alerta": "En la salida final existen filas sin denominador para códigos de comuna fuera de RM; la vista principal las excluye por defecto."},
    "VACUNA VPH 4 BASICO": {"vacuna": "VPH", "dosis": "4to básico", "grupo": "Escolar", "estrategia": "Escolar", "fuente": "Mineduc", "alerta": "Verificar coexistencia de dosis única nonavalente y rezagados; la vista principal excluye filas sin denominador."},
    "VACUNA VPH 5 BASICO": {"vacuna": "VPH", "dosis": "5to básico", "grupo": "Escolar", "estrategia": "Escolar", "fuente": "Mineduc", "alerta": "Pendiente confirmación PNI; la vista principal excluye filas sin denominador."},
    "VACUNA DTPA 8 BASICO": {"vacuna": "dTpa", "dosis": "8vo básico", "grupo": "Escolar", "estrategia": "Escolar", "fuente": "Mineduc", "alerta": "En la salida final existen filas sin denominador para códigos de comuna fuera de RM; la vista principal las excluye por defecto."},
    "VACUNA NEUMOCOCICA POLISACARIDA": {"vacuna": "Neumocócica polisacárida", "dosis": "Dosis única", "grupo": "65 años", "estrategia": "Personas mayores", "fuente": "INE", "alerta": "Interpretar según metodología vigente del programa; revisar con equipo si se esperan rescates o definiciones especiales del numerador."},
    "VACUNA DTPA GESTANTES": {"vacuna": "dTpa gestantes", "dosis": "Dosis única", "grupo": "Gestantes", "estrategia": "Gestantes", "fuente": "Estimación gestantes", "alerta": "El denominador de gestantes depende de estimación específica del programa; conviene validar la lectura con el equipo técnico."},
}
DISPLAY_ORDER = list(VACUNA_META.keys())

VACUNAS_OCULTAS_DASHBOARD = {
    "VACUNA HEXAVALENTE 1RA DOSIS",
    "VACUNA HEXAVALENTE 2DA DOSIS",
    "VACUNA HEXAVALENTE REFUERZO",
    "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS",
    "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS",
    "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO",
    "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS",
    "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS",
}

COMUNA_TO_SS = {
    "Alhué": "Servicio de Salud Metropolitano Occidente",
    "Buin": "Servicio de Salud Metropolitano Sur",
    "Calera de Tango": "Servicio de Salud Metropolitano Sur",
    "Cerrillos": "Servicio de Salud Metropolitano Occidente",
    "Cerro Navia": "Servicio de Salud Metropolitano Occidente",
    "Colina": "Servicio de Salud Metropolitano Norte",
    "Conchalí": "Servicio de Salud Metropolitano Norte",
    "Curacaví": "Servicio de Salud Metropolitano Occidente",
    "El Bosque": "Servicio de Salud Metropolitano Sur",
    "El Monte": "Servicio de Salud Metropolitano Occidente",
    "Estación Central": "Servicio de Salud Metropolitano Central",
    "Huechuraba": "Servicio de Salud Metropolitano Norte",
    "Independencia": "Servicio de Salud Metropolitano Norte",
    "Isla de Maipo": "Servicio de Salud Metropolitano Occidente",
    "La Cisterna": "Servicio de Salud Metropolitano Sur",
    "La Florida": "Servicio de Salud Metropolitano Sur Oriente",
    "La Granja": "Servicio de Salud Metropolitano Sur",
    "La Pintana": "Servicio de Salud Metropolitano Sur Oriente",
    "La Reina": "Servicio de Salud Metropolitano Oriente",
    "Lampa": "Servicio de Salud Metropolitano Norte",
    "Las Condes": "Servicio de Salud Metropolitano Oriente",
    "Lo Barnechea": "Servicio de Salud Metropolitano Oriente",
    "Lo Espejo": "Servicio de Salud Metropolitano Sur",
    "Lo Prado": "Servicio de Salud Metropolitano Occidente",
    "Macul": "Servicio de Salud Metropolitano Oriente",
    "Maipú": "Servicio de Salud Metropolitano Central",
    "María Pinto": "Servicio de Salud Metropolitano Occidente",
    "Melipilla": "Servicio de Salud Metropolitano Occidente",
    "Ñuñoa": "Servicio de Salud Metropolitano Oriente",
    "Padre Hurtado": "Servicio de Salud Metropolitano Occidente",
    "Paine": "Servicio de Salud Metropolitano Sur",
    "Pedro Aguirre Cerda": "Servicio de Salud Metropolitano Sur",
    "Peñaflor": "Servicio de Salud Metropolitano Occidente",
    "Peñalolén": "Servicio de Salud Metropolitano Oriente",
    "Pirque": "Servicio de Salud Metropolitano Sur Oriente",
    "Providencia": "Servicio de Salud Metropolitano Oriente",
    "Pudahuel": "Servicio de Salud Metropolitano Occidente",
    "Puente Alto": "Servicio de Salud Metropolitano Sur Oriente",
    "Quilicura": "Servicio de Salud Metropolitano Norte",
    "Quinta Normal": "Servicio de Salud Metropolitano Occidente",
    "Recoleta": "Servicio de Salud Metropolitano Norte",
    "Renca": "Servicio de Salud Metropolitano Occidente",
    "San Bernardo": "Servicio de Salud Metropolitano Sur",
    "San Joaquín": "Servicio de Salud Metropolitano Sur",
    "San José de Maipo": "Servicio de Salud Metropolitano Sur Oriente",
    "San Miguel": "Servicio de Salud Metropolitano Sur",
    "San Pedro": "Servicio de Salud Metropolitano Occidente",
    "San Ramón": "Servicio de Salud Metropolitano Sur Oriente",
    "Santiago": "Servicio de Salud Metropolitano Central",
    "Talagante": "Servicio de Salud Metropolitano Occidente",
    "Tiltil": "Servicio de Salud Metropolitano Norte",
    "Vitacura": "Servicio de Salud Metropolitano Oriente",
}


def latest_dated_file(dir_path: Path, base_name: str) -> Path:
    candidates = sorted(glob(str(dir_path / f"????-??-??_{base_name}")))
    if candidates:
        return Path(candidates[-1])
    legacy = dir_path / base_name
    if legacy.exists():
        return legacy
    raise FileNotFoundError(f"No existe {base_name} en {dir_path}")


def latest_dated_file_any(dir_path: Path, *base_names: str) -> Path:
    for base_name in base_names:
        try:
            return latest_dated_file(dir_path, base_name)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"No existe ninguno de {base_names} en {dir_path}")


def _meta_df(anio: int) -> pd.DataFrame:
    cfg = cfgmod.get_config(anio)
    meta = {k: dict(v) for k, v in VACUNA_META.items()}
    for clave, texto in cfg.alertas.items():
        meta[clave]["alerta"] = texto
    return pd.DataFrame.from_dict(meta, orient="index").reset_index(names="VACUNA_DASHBOARD")


def enrich_metadata(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    meta = _meta_df(anio)
    out = df.merge(meta, on="VACUNA_DASHBOARD", how="left")
    out["vacuna"] = out["vacuna"].fillna(out["VACUNA_DASHBOARD"])
    for col in ["dosis", "grupo", "estrategia", "fuente", "alerta"]:
        out[col] = out[col].fillna("")
    out["VACUNA_DASHBOARD"] = pd.Categorical(out["VACUNA_DASHBOARD"], categories=DISPLAY_ORDER, ordered=True)
    return out.sort_values(["VACUNA_DASHBOARD"]).reset_index(drop=True)


def normalize_comuna_name(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().replace({
        "Nunoa": "Ñuñoa", "Ńuńoa": "Ñuñoa", "Nuñoa": "Ñuñoa", "Maipu": "Maipú",
        "Penalolen": "Peñalolén", "Penaflor": "Peñaflor", "Maria Pinto": "María Pinto",
        "Estacion Central": "Estación Central", "Alhue": "Alhué",
    })


def add_ss_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["comuna"] = normalize_comuna_name(out["comuna"])
    out["servicio_salud"] = out["comuna"].map(COMUNA_TO_SS)
    return out


def ruta_oficial(anio: int) -> Path:
    cfg = cfgmod.get_config(anio)
    if not cfg.oficial_disponible:
        raise ValueError(f"El año {anio} no tiene fuente oficial configurada en el dashboard.")
    return latest_dated_file_any(cfgmod.OUTPUT_DIR, cfg.oficial_archivo)


@st.cache_data(show_spinner=False)
def load_detail(anio: int) -> tuple[pd.DataFrame, Path]:
    path = ruta_oficial(anio)
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[~df["VACUNA_DASHBOARD"].isin(VACUNAS_OCULTAS_DASHBOARD)].copy()
    df = enrich_metadata(df, anio)
    comuna_source = next((c for c in ["COMUNA_CALCULO", "COMUNA_RESIDENCIA", "COMUNA"] if c in df.columns), None)
    if comuna_source is None:
        raise KeyError("No se encontró una columna de comuna esperada en el archivo de detalle.")
    df["comuna"] = df[comuna_source].astype(str).str.strip()
    df["valid_denom"] = df["POBLACION_OBJETIVO"].notna()
    df = add_ss_column(df)
    return df, path


@st.cache_data(show_spinner=False)
def load_regional(anio: int) -> tuple[pd.DataFrame, Path]:
    """Resumen regional reconstruido desde el detalle oficial, sin duplicar
    denominadores por vacuna (cuadra con la fila nacional publicada)."""
    detail, path = load_detail(anio)
    agg = {"VACUNAS_ADMINISTRADAS": ("VACUNAS_ADMINISTRADAS", "sum")}
    num = (detail.groupby(["VACUNA_DASHBOARD", "CLAVE_DENOMINADOR"], as_index=False)
           .agg(**agg))
    den = (detail.drop_duplicates(["CLAVE_DENOMINADOR", "COD_COMUNA_JOIN"])
           .groupby("CLAVE_DENOMINADOR", as_index=False)
           .agg(POBLACION_OBJETIVO=("POBLACION_OBJETIVO", "sum")))
    reg = num.merge(den, on="CLAVE_DENOMINADOR", how="left")
    reg["PORC_COBERTURA"] = (
        reg["VACUNAS_ADMINISTRADAS"] / reg["POBLACION_OBJETIVO"].replace(0, pd.NA) * 100
    ).round(1).fillna(0)
    reg = enrich_metadata(reg, anio)
    return reg, path


def style_percent_table(df: pd.DataFrame):
    pct_cols = [c for c in df.columns if "(%)" in str(c)]
    fmt = {c: "{:.1f}%" for c in pct_cols}
    for col in df.columns:
        if col in {"Vacunados", "Población objetivo", "Registros sin denominador"}:
            fmt[col] = "{:,.0f}"
    def pct_bold(col: pd.Series):
        return ["font-weight: 700" if col.name in pct_cols else "" for _ in col]
    return (df.style.format(fmt, na_rep="").apply(pct_bold, axis=0)
            .set_table_styles([{"selector": "th", "props": [("font-weight", "700")]}]))


def to_excel_bytes(df: pd.DataFrame, quality_df: pd.DataFrame | None = None) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="tabla_filtrada")
        if quality_df is not None and not quality_df.empty:
            quality_df.to_excel(writer, index=False, sheet_name="calidad_datos")
    buffer.seek(0)
    return buffer.getvalue()


def render_badge(texto: str):
    st.markdown(f'<div class="provisional-badge">{texto}</div>', unsafe_allow_html=True)


def render_dashboard(anio: int):
    cfg = cfgmod.get_config(anio)

    st.title("Dashboard Coberturas Vacunas Programáticas")
    render_badge(
        f"Reflejo de la fuente oficial — {cfg.oficial_etiqueta} — "
        "resultados publicados, sin recalcular"
    )

    detail_df, detail_path = load_detail(anio)
    regional_df, _ = load_regional(anio)
    valid_detail_df = detail_df[detail_df["valid_denom"]].copy()
    invalid_detail_df = detail_df[~detail_df["valid_denom"]].copy()

    st.caption(cfg.caption)
    render_coberturas(anio, cfg, detail_path,
                      regional_df, valid_detail_df, invalid_detail_df)


def render_coberturas(anio, cfg, detail_path,
                      regional_df, valid_detail_df, invalid_detail_df):
    with st.sidebar:
        st.header("Filtros")
        st.caption(f"Año: {cfg.T}")
        level = st.selectbox("Nivel", ["Regional", "Comuna"], index=0)
        strategy_options = ["Todas"] + sorted(regional_df["estrategia"].dropna().unique().tolist())
        strategy_choice = st.selectbox("Población / grupo", strategy_options, index=0)
        presentes = {str(v) for v in regional_df["VACUNA_DASHBOARD"].dropna().unique()}
        vaccine_options = ["Todas"] + list(dict.fromkeys(
            VACUNA_META[k]["vacuna"] for k in DISPLAY_ORDER if k in presentes))
        vaccine_choice = st.selectbox("Vacuna", vaccine_options, index=0)
        if vaccine_choice == "Todas":
            dose_choice = st.selectbox("Dosis", ["Todas"] + sorted(regional_df["dosis"].dropna().unique().tolist()), index=0)
        else:
            possible_doses = [d for d in regional_df.loc[regional_df["vacuna"] == vaccine_choice, "dosis"].dropna().unique().tolist() if d]
            if len(possible_doses) <= 1:
                dose_choice = possible_doses[0] if possible_doses else "Todas"
                if dose_choice != "Todas":
                    st.markdown(f"**Dosis:** {dose_choice}")
            else:
                dose_choice = st.selectbox("Dosis", ["Todas"] + sorted(possible_doses), index=0)
        show_only_pct = st.checkbox("Mostrar solo porcentajes", value=False)

    source_df = (regional_df if level == "Regional" else valid_detail_df).copy()
    if strategy_choice != "Todas":
        source_df = source_df[source_df["estrategia"] == strategy_choice]
    if vaccine_choice != "Todas":
        source_df = source_df[source_df["vacuna"] == vaccine_choice]
    if dose_choice != "Todas":
        source_df = source_df[source_df["dosis"] == dose_choice]

    if level == "Comuna":
        ss_options = sorted(source_df["servicio_salud"].dropna().unique().tolist())
        with st.sidebar:
            selected_ss = st.multiselect("Servicio de Salud", ss_options, default=ss_options)
        if ss_options:
            source_df = source_df[source_df["servicio_salud"].isin(selected_ss)]
        comuna_options = sorted(source_df["comuna"].dropna().unique().tolist())
        with st.sidebar:
            selected_comunas = st.multiselect("Comuna", comuna_options, default=comuna_options)
        if comuna_options:
            source_df = source_df[source_df["comuna"].isin(selected_comunas)]

    if source_df.empty:
        st.warning("No hay datos para la combinación de filtros seleccionada.")
        st.stop()

    metric_label = "Vacunas visibles" if level == "Regional" else "Registros visibles"
    coverage_mean = source_df["PORC_COBERTURA"].mean()
    coverage_max = source_df["PORC_COBERTURA"].max()
    coverage_total = (
        source_df["VACUNAS_ADMINISTRADAS"].sum()
        / source_df["POBLACION_OBJETIVO"].replace(0, pd.NA).sum() * 100
    ).round(1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cobertura total", f"{coverage_total:.1f}%")
    c2.metric(metric_label, f"{len(source_df):,}".replace(",", "."))
    c3.metric("Cobertura promedio", f"{coverage_mean:.1f}%")
    c4.metric("Cobertura máxima", f"{coverage_max:.1f}%")

    base_cols = ["vacuna", "dosis", "grupo", "fuente"]
    rename_map = {
        "servicio_salud": "Servicio de Salud", "vacuna": "Vacuna", "dosis": "Dosis",
        "grupo": "Población / cohorte", "fuente": "Fuente denominador", "comuna": "Comuna",
        "VACUNAS_ADMINISTRADAS": "Vacunados", "POBLACION_OBJETIVO": "Población objetivo",
        "PORC_COBERTURA": "Cobertura (%)",
    }
    if level == "Comuna":
        base_cols = ["servicio_salud", "comuna"] + base_cols
    display_cols = base_cols + ["VACUNAS_ADMINISTRADAS", "POBLACION_OBJETIVO", "PORC_COBERTURA"]
    display_df = source_df[display_cols].copy().rename(columns=rename_map)
    if show_only_pct:
        display_df = display_df[[rename_map[c] for c in base_cols] + ["Cobertura (%)"]]

    st.subheader("Tabla")
    st.dataframe(style_percent_table(display_df), use_container_width=True, hide_index=True)

    quality_summary = pd.DataFrame([{
        "Fuente": cfg.oficial_etiqueta,
        "Archivo": detail_path.name,
        "Registros válidos": int(valid_detail_df.shape[0]),
        "Registros sin denominador": int(invalid_detail_df.shape[0]),
        "Comunas válidas RM": int(valid_detail_df["comuna"].nunique()),
        "Servicios de Salud RM": int(valid_detail_df["servicio_salud"].nunique()),
    }])

    with st.expander("Metodología y calidad de datos"):
        st.markdown(
            f"- El dashboard es un **reflejo de la fuente oficial** "
            f"(**{cfg.oficial_etiqueta}**): vacunados, población objetivo y coberturas "
            "se muestran tal cual fueron publicados, sin recalcular.\n"
            "- Las coberturas regionales se reconstruyen sumando las comunas; cuadran con "
            "la fila nacional publicada (corte MINSAL 2025) y con la hoja "
            "`Resumen_Regional` del informe (2024).\n"
            "- Se mantienen ocultas 8 vacuna-dosis (Hexavalente 1ª/2ª/refuerzo, "
            "Meningocócica recombinante 1ª/2ª/refuerzo y Neumocócica conjugada 1ª/2ª), "
            "según la decisión del informe final.\n"
            "- En nivel comunal se muestra además el Servicio de Salud al que pertenece "
            "la comuna.\n"
        )
        st.dataframe(quality_summary, use_container_width=True, hide_index=True)
        if not invalid_detail_df.empty:
            invalid_sample = (
                invalid_detail_df[["comuna", "vacuna", "dosis", "COD_COMUNA_JOIN"]]
                .rename(columns={"comuna": "Comuna residencia", "vacuna": "Vacuna", "dosis": "Dosis",
                                 "COD_COMUNA_JOIN": "Código comuna join"})
                .drop_duplicates().sort_values(["Vacuna", "Comuna residencia"]).reset_index(drop=True)
            )
            st.markdown("**Muestra de registros excluidos por falta de denominador**")
            st.dataframe(invalid_sample, use_container_width=True, hide_index=True, height=240)

    st.download_button(
        "Descargar tabla filtrada (Excel)",
        data=to_excel_bytes(display_df, quality_summary),
        file_name=f"dashboard_programaticas_{cfg.T}_{level.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
