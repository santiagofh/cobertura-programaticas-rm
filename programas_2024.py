"""Pipeline completo coberturas programaticas 2024.

Ejecuta en orden estricto 4 -> 1 -> 2 -> 3 (nunca en paralelo).
Rutas externas via variables de entorno (ver README).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import run_pipeline

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Pipeline coberturas programaticas 2024")
    p.add_argument("--pasos", default="4123",
                   help="Subconjunto de pasos a ejecutar, ej: '4' o '23'. Orden interno 4->1->2->3.")
    a = p.parse_args()
    run_pipeline(2024, pasos=a.pasos)
