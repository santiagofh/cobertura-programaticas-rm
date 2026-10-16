"""Dashboard unico Coberturas Vacunas Programaticas RM 2024 / 2025 / 2026."""
from pathlib import Path

import streamlit as st

from src.dashboard_comun import render_dashboard

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Dashboard Programáticas RM",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #F6FAFD 0%, #FFFFFF 14%, #FFFFFF 100%); }
    .stApp h1, .stApp h2, .stApp h3 { color: #006FB3; font-weight: 700; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

logo_path = BASE_DIR / "assets" / "seremi_sidebar_logo.svg"
icon_path = BASE_DIR / "assets" / "seremi_sidebar_icon.svg"
if logo_path.exists() and icon_path.exists():
    st.logo(str(logo_path), size="large", icon_image=str(icon_path))

with st.sidebar:
    st.header("Campaña")
    anio = st.selectbox(
        "Año",
        [2025, 2024],
        index=0,
        format_func=lambda x: f"Año {x}",
        key="selector_anio",
    )

try:
    render_dashboard(anio)
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo cargar el dashboard para {anio}: {exc}")
    st.stop()
