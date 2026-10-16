"""Lectura unificada de las bases RNI Programaticas (parquet o CSV).

Fuente principal: `RNI_PROGRAMATICAS_DIR` (por defecto la carpeta hermana
DATA 2026-10-09), que puede traer `Programaticas_{anio}.parquet` o
`Programaticas_{anio}.csv` (LATIN1, sep "|"). Los CSV se cachean una vez en
`data/_rni_cache/Programaticas_{anio}.parquet` (por chunks, para no cargar
~2,5 GB en memoria). Si un año no existe en la fuente principal se intenta
`RNI_PROGRAMATICAS_FALLBACK_DIR` (parquets historicos).
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .. import config_programaticas as cfgmod

# Union de columnas usadas por los pasos 1 y 4 (subconjunto de los CSV crudos).
CACHE_COLUMNS = [
    "RUN", "PASAPORTE", "OTRO", "ID_INMUNIZACION",
    "COD_COMUNA_OCURR", "COMUNA_OCURR", "COD_COMUNA_RESID", "COMUNA_RESIDENCIA",
    "NOMBRE_VACUNA", "CRITERIO_ELEGIBILIDAD", "DOSIS",
    "VACUNA_ADMINISTRADA", "REGISTRO_ELIMINADO",
    "SEXO", "FECHA_NACIMIENTO", "FECHA_INMUNIZACION", "SEMANA_GESTACIONAL",
]

CHUNKSIZE = 500_000


def _dir_usuable(ruta: Path | None) -> Path | None:
    if ruta is None:
        return None
    texto = str(ruta).strip()
    if texto in ("", "."):
        return None
    return ruta if ruta.exists() else None


def _cache_dir() -> Path:
    ruta = cfgmod.DATA_DIR / "_rni_cache"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _convertir_csv_a_parquet(csv_path: Path, parquet_path: Path) -> None:
    print(f"  [RNI] Convirtiendo {csv_path.name} a cache parquet (chunks de {CHUNKSIZE:,})...")
    writer = None
    n = 0
    try:
        for chunk in pd.read_csv(csv_path, encoding="LATIN1", sep="|",
                                 usecols=CACHE_COLUMNS, chunksize=CHUNKSIZE,
                                 low_memory=False):
            tabla = pa.Table.from_pandas(chunk, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(parquet_path, tabla.schema, compression="snappy")
            writer.write_table(tabla)
            n += len(chunk)
    finally:
        if writer is not None:
            writer.close()
    print(f"  [RNI] Cache listo: {parquet_path.name} ({n:,} filas)")


def resolver(anio: int) -> tuple[Path, str] | None:
    """Devuelve (ruta, formato) para el año, priorizando la fuente principal."""
    principal = _dir_usuable(cfgmod.RNI_PROGRAMATICAS_DIR)
    respaldo = _dir_usuable(cfgmod.RNI_PROGRAMATICAS_FALLBACK_DIR)
    candidatos = []
    for carpeta in (principal, respaldo):
        if carpeta is None:
            continue
        candidatos.append((carpeta / f"Programaticas_{anio}.parquet", "parquet"))
        candidatos.append((carpeta / f"Programaticas_{anio}.csv", "csv"))
    for ruta, formato in candidatos:
        if ruta.exists():
            return ruta, formato
    return None


def leer(anio: int, columns: list[str]) -> pd.DataFrame | None:
    """Lee las columnas pedidas del año; None si no existe la base."""
    fuente = resolver(anio)
    if fuente is None:
        return None
    ruta, formato = fuente
    if formato == "csv":
        cache = _cache_dir() / f"Programaticas_{anio}.parquet"
        if not cache.exists() or cache.stat().st_mtime < ruta.stat().st_mtime:
            _convertir_csv_a_parquet(ruta, cache)
        ruta = cache
    return pd.read_parquet(ruta, columns=columns)
