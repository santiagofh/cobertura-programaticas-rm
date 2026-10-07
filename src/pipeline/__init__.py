"""Pipeline de coberturas de vacunas programaticas RM.

Orden obligatorio (nunca en paralelo): 4 -> 1 -> 2 -> 3.
    4) numerador SRP
    1) numerador RNI no-SRP + unificacion
    2) denominadores
    3) calculo de coberturas CD / SD
"""

from .. import config_programaticas as cfgmod
from . import coberturas, denominadores, numerador_rni, numerador_srp


def run_pipeline(anio: int, pasos: str = "4123", solo_excel: bool = False):
    """Ejecuta el pipeline en orden estricto.

    pasos: subconjunto de "4123" a ejecutar (por defecto todos).
    solo_excel: si True, solo regenera el Excel del dashboard (no aplica al pipeline).
    """
    cfg = cfgmod.get_config(anio)
    print("#" * 70)
    print(f"# PIPELINE PROGRAMATICAS {cfg.T}  (orden 4 -> 1 -> 2 -> 3)")
    print("#" * 70)

    if "4" in pasos:
        print("\n>>> PASO 4: numerador SRP")
        numerador_srp.run(anio)
    if "1" in pasos:
        print("\n>>> PASO 1: numerador RNI (no-SRP) + unificacion")
        numerador_rni.run(anio)
    if "2" in pasos:
        print("\n>>> PASO 2: denominadores")
        denominadores.run(anio)
    if "3" in pasos:
        print("\n>>> PASO 3: calculo de coberturas CD / SD")
        coberturas.run(anio)

    print("\n" + "#" * 70)
    print(f"# PIPELINE {cfg.T} COMPLETADO")
    print("#" * 70)
