"""Configuracion por año del calculo de coberturas de vacunas programaticas RM.

Cada año conserva su metodologia original:
  - 2024: denominadores reciclados desde versiones previas validadas
          (data/nacimientos no disponible originalmente).
  - 2025/2026: denominadores calculados desde NAC crudos (SRCeI).

Rutas externas configurables por variables de entorno (con valores por defecto
locales): RNI_PROGRAMATICAS_DIR (por defecto DATA 2026-10-09), 
RNI_PROGRAMATICAS_FALLBACK_DIR, RNI_SRP_DIR, NACIMIENTO_DIR,
ESTIMACIONES_CSV, PROGRAMATICAS_OUTPUT_DIR, PROGRAMATICAS_DATA_DIR.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PROGRAMATICAS_DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.environ.get("PROGRAMATICAS_OUTPUT_DIR", BASE_DIR / "output"))

# Fuente RNI por defecto: export en la carpeta hermana DATA 2026-10-09
# (Programaticas_{anio}.csv o .parquet). Se puede sobreescribir por entorno.
RNI_PROGRAMATICAS_DEFAULT = BASE_DIR.parent / "DATA 2026-10-09"
RNI_PROGRAMATICAS_DIR = Path(
    os.environ.get("RNI_PROGRAMATICAS_DIR", str(RNI_PROGRAMATICAS_DEFAULT))
)
# Respaldo solo para años ausentes en la fuente principal (parquets historicos).
RNI_PROGRAMATICAS_FALLBACK_DIR = Path(
    os.environ.get("RNI_PROGRAMATICAS_FALLBACK_DIR", r"D:\DATA\RNI\PROGRAMATICAS")
)
RNI_SRP_DIR = Path(os.environ.get("RNI_SRP_DIR", r"D:\DATA\RNI\SRP"))
NACIMIENTO_DIR = Path(os.environ.get("NACIMIENTO_DIR", r"D:\DATA\NACIMIENTO"))
ESTIMACIONES_CSV = Path(
    os.environ.get(
        "ESTIMACIONES_CSV",
        DATA_DIR / "estimaciones-y-proyecciones-2002-2035-comunas(Est. y Proy. de Pob.csv",
    )
)


def requerido(valor, nombre: str) -> Path:
    """Valida una ruta/config requerida por el pipeline y entrega un error claro."""
    if valor is None or str(valor) == "" or str(valor) == ".":
        raise ValueError(
            f"Falta configurar {nombre}. Defínelo como variable de entorno "
            f"(ej: setx {nombre} \"D:\\ruta\\...\")."
        )
    ruta = Path(valor)
    if not ruta.exists():
        raise FileNotFoundError(f"{nombre} no existe: {ruta}")
    return ruta

# Comunas RM nombre -> codigo (identico en todos los años).
COMUNA_MAP = {
    "Santiago": 13101, "Cerrillos": 13102, "Cerro Navia": 13103,
    "Conchalí": 13104, "El Bosque": 13105, "Estación Central": 13106,
    "Huechuraba": 13107, "Independencia": 13108, "La Cisterna": 13109,
    "La Florida": 13110, "La Granja": 13111, "La Pintana": 13112,
    "La Reina": 13113, "Las Condes": 13114, "Lo Barnechea": 13115,
    "Lo Espejo": 13116, "Lo Prado": 13117, "Macul": 13118,
    "Maipú": 13119, "Ñuñoa": 13120, "Pedro Aguirre Cerda": 13121,
    "Peñalolén": 13122, "Providencia": 13123, "Pudahuel": 13124,
    "Quilicura": 13125, "Quinta Normal": 13126, "Recoleta": 13127,
    "Renca": 13128, "San Joaquín": 13129, "San Miguel": 13130,
    "San Ramón": 13131, "Vitacura": 13132,
    "Puente Alto": 13201, "Pirque": 13202, "San José de Maipo": 13203,
    "Colina": 13301, "Lampa": 13302, "Tiltil": 13303,
    "San Bernardo": 13401, "Buin": 13402, "Calera De Tango": 13403,
    "Paine": 13404,
    "Melipilla": 13501, "Alhué": 13502, "Curacavi": 13503,
    "María Pinto": 13504, "San Pedro": 13505,
    "Talagante": 13601, "El Monte": 13602, "Isla De Maipo": 13603,
    "Padre Hurtado": 13604, "Peñaflor": 13605,
}


def cohortes(T: int) -> dict:
    return {
        "RN": (f"{T}-01-01", f"{T}-12-31"),
        "2M": (f"{T-1}-11-01", f"{T}-10-31"),
        "4M": (f"{T-1}-09-01", f"{T}-08-31"),
        "6M": (f"{T-1}-07-01", f"{T}-06-30"),
        "12M": (f"{T-1}-01-01", f"{T-1}-12-31"),
        "18M": (f"{T-2}-07-01", f"{T-1}-06-30"),
        "36M": (f"{T-3}-01-01", f"{T-3}-12-31"),
    }


def cohortes_escolar(T: int) -> dict:
    return {
        "1basico": (f"{T-8}-07-01", f"{T-6}-06-30"),
        "4basico": (f"{T-10}-01-01", f"{T-9}-06-30"),
        "5basico": (f"{T-11}-01-01", f"{T-10}-06-30"),
        "8basico": (f"{T-15}-07-01", f"{T-13}-06-30"),
    }


def cohortes_nac(T: int) -> dict:
    return {
        "BCG_RN": (f"{T}-01-01", f"{T}-12-31", ["VACUNA BCG"], f"Nacidos vivos Ene–Dic {T} (RN)"),
        "HepB_RN": (f"{T}-01-01", f"{T}-12-31", ["VACUNA HEPATITIS B RN"], f"Nacidos vivos Ene–Dic {T} (RN)"),
        "Cohorte_2M": (
            f"{T-1}-11-01", f"{T}-10-31",
            ["VACUNA HEXAVALENTE 1RA DOSIS", "VACUNA NEUMOCOCICA CONJUGADA 1RA DOSIS",
             "VACUNA MENINGOCOCICA RECOMBINANTE 1RA DOSIS"],
            f"Nacidos vivos Nov {T-1} – Oct {T} (2 meses)",
        ),
        "Cohorte_4M": (
            f"{T-1}-09-01", f"{T}-08-31",
            ["VACUNA HEXAVALENTE 2DA DOSIS", "VACUNA NEUMOCOCICA CONJUGADA 2DA DOSIS",
             "VACUNA MENINGOCOCICA RECOMBINANTE 2DA DOSIS"],
            f"Nacidos vivos Sep {T-1} – Ago {T} (4 meses)",
        ),
        "Hexavalente_3d_6m": (
            f"{T-1}-07-01", f"{T}-06-30",
            ["VACUNA HEXAVALENTE 3RA DOSIS"],
            f"Nacidos vivos Jul {T-1} – Jun {T} (6 meses)",
        ),
        "Cohorte_12M": (
            f"{T-1}-01-01", f"{T-1}-12-31",
            ["VACUNA SRP (TRIVIRICA) 1RA DOSIS", "VACUNA NEUMOCOCICA CONJUGADA REFUERZO",
             "VACUNA MENINGOCOCICA CONJUGADA DOSIS UNICA"],
            f"Nacidos vivos Ene–Dic {T-1} (12 meses)",
        ),
        "Cohorte_18M": (
            f"{T-2}-07-01", f"{T-1}-06-30",
            ["VACUNA VARICELA 1RA DOSIS", "VACUNA HEPATITIS A PEDIATRICA",
             "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO"],
            f"Nacidos vivos Jul {T-2} – Jun {T-1} (18 meses)",
        ),
        "Cohorte_36M": (
            f"{T-3}-01-01", f"{T-3}-12-31",
            ["VACUNA SRP (TRIVIRICA) 2DA DOSIS", "VACUNA VARICELA 2DA DOSIS"],
            f"Nacidos vivos Ene–Dic {T-3} (36 meses)",
        ),
        "Hexavalente_ref_18m": (
            f"{T-2}-07-01", f"{T-1}-06-30",
            ["VACUNA HEXAVALENTE REFUERZO"],
            f"Nacidos vivos Jul {T-2} – Jun {T-1} (18 meses — ref Hexa)",
        ),
    }


ALERTAS_2024 = {
    "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO":
        "Cobertura regional muy baja en 2024; la documentación sugiere revisar la clasificación del refuerzo en RNI.",
    "VACUNA VPH 4 BASICO":
        "En 2024 coexisten dosis única nonavalente y rezagados; la vista principal excluye filas sin denominador.",
    "VACUNA VPH 5 BASICO":
        "Aplica solo en 2024 por transición de esquema; la vista principal excluye filas sin denominador.",
}
ALERTAS_2025 = {
    "VACUNA MENINGOCOCICA RECOMBINANTE REFUERZO":
        "Monitorear cobertura; en 2024 fue muy baja y la documentación sugiere revisar la clasificación del refuerzo en RNI.",
    "VACUNA VPH 4 BASICO":
        "Verificar coexistencia de dosis única nonavalente y rezagados; la vista principal excluye filas sin denominador.",
    "VACUNA VPH 5 BASICO":
        "Pendiente confirmación PNI para 2025 (en 2024 aplicó por transición de esquema); la vista principal excluye filas sin denominador.",
}


@dataclass
class ConfigAnio:
    T: int
    page_title: str
    caption: str
    # Paso 1
    strict_parquet: bool
    # Paso 2
    nac_raw: bool              # True: NAC crudos; False: reciclar denominadores previos (2024)
    pob_esc_nombre: str
    pob_esc_hoja: str | None = None          # hoja del Excel MINEDUC (None = layout legacy header=None)
    pob_prog_nombre: str | None = None       # Excel de poblaciones programáticas (gestantes)
    pob_prog_hoja: str | None = None
    # Paso 3 (fallbacks)
    fallback_nac: list = field(default_factory=list)
    fallback_65: list = field(default_factory=list)
    fallback_mat: list = field(default_factory=list)
    fallback_gest: list = field(default_factory=list)
    # Dashboard
    alertas: dict = field(default_factory=dict)
    # Dashboard espejo: fuente oficial publicada (sin recalcular)
    oficial_disponible: bool = False
    oficial_etiqueta: str = ""
    oficial_archivo: str = ""
    # Dashboard: Excel descargable desde la barra lateral (bajo el selector de año)
    descarga_xlsx: str = ""

    @property
    def nac_filter_years(self) -> list:
        return [self.T - 3, self.T - 1]


def _fallbacks(T: int, legacy_v3: bool) -> dict:
    v3 = ["_V3_CD"] if legacy_v3 else []
    return {
        "fallback_nac": [f"denominador_nacimientos_{T}{s}.csv" for s in ["_V7", "_V6", "_V5"] + v3],
        "fallback_65": [f"denominador_neumococica_65_{T}{s}.csv" for s in ["_V7", "_V6", "_V5"] + v3],
        "fallback_mat": [f"denominador_matricula_escolar_{T}{s}.csv" for s in ["_V7", "_V6", "_V5"] + v3],
        "fallback_gest": [f"denominador_gestantes_{T}{s}.csv"
                          for s in ["_V7", "_V6", "_V5", "_V3_CD", "_V3_SD"]],
    }


CONFIGS = {
    2024: ConfigAnio(
        T=2024,
        page_title="Dashboard Programáticas 2024",
        caption="Año 2024. Informe Ejecutivo 2024 (corte 15-06-2026).",
        strict_parquet=True,
        nac_raw=False,
        pob_esc_nombre="Poblacion Escolar 2024.xlsx",
        alertas=ALERTAS_2024,
        oficial_disponible=True,
        oficial_etiqueta="Informe Ejecutivo 2024 (corte 15-06-2026)",
        oficial_archivo="coberturas_vacunas_2024_V7_INFORME.csv",
        descarga_xlsx=str(
            BASE_DIR / "2024 Cerrado"
            / "2026-06-17_coberturas_vacunas_Programaticas_2024_V7_Informe Ejecutivo 2024.xlsx"
        ),
        **_fallbacks(2024, legacy_v3=True),
    ),
    2025: ConfigAnio(
        T=2025,
        page_title="Dashboard Programáticas 2025",
        caption="Año 2025. Corte MINSAL 2026-10-09.",
        strict_parquet=False,
        nac_raw=True,
        pob_esc_nombre="Población MINEDUC2025.xlsx",
        pob_esc_hoja="2025RM",
        pob_prog_nombre="Población programáticas2025.xlsx",
        pob_prog_hoja="2025 RM",
        alertas=ALERTAS_2025,
        oficial_disponible=True,
        oficial_etiqueta="Corte MINSAL 2026-10-09",
        oficial_archivo="coberturas_vacunas_2025_V7_MINSAL.csv",
        descarga_xlsx=str(OUTPUT_DIR / "coberturas_vacunas_2025_MINSAL.xlsx"),
        **_fallbacks(2025, legacy_v3=False),
    ),
    2026: ConfigAnio(
        T=2026,
        page_title="Dashboard Programáticas 2026",
        caption="Año 2026. Datos provisorios; revisar insumos (parquet RNI, MINEDUC, gestantes) al actualizar.",
        strict_parquet=False,
        nac_raw=True,
        pob_esc_nombre="Poblacion Escolar 2026.xlsx",
        # TODO: revisar textos de alerta para 2026 cuando existan antecedentes.
        alertas=ALERTAS_2025,
        **_fallbacks(2026, legacy_v3=False),
    ),
}


def get_config(anio: int) -> ConfigAnio:
    if anio not in CONFIGS:
        raise ValueError(f"Año no soportado: {anio}. Opciones: {sorted(CONFIGS)}")
    return CONFIGS[anio]
