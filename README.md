# Coberturas Vacunas Programáticas RM — 2024 / 2025 / 2026

Dashboard unificado (Streamlit) + pipeline de cálculo, con un **núcleo común**
parametrizado por año. No modifica las carpetas originales
`Programaticas 2024 - Dashboard` ni `Programaticas 2025 - Dashboard`.

## Estructura

- `app.py`: dashboard Streamlit (selector de año 2025 / 2024).
- `src/config_programaticas.py`: configuración por año (cohortes derivadas de
  `T`, años de filtro NAC, modo de denominadores, fallbacks, textos).
- `src/dashboard_comun.py`: dashboard parametrizado por año.
- `src/minsal_comparacion.py`: cruce cálculo local vs corte MINSAL (resumen y
  detalle por comuna) para la pestaña comparativa del dashboard.
- `src/pipeline/`:
  - `numerador_srp.py`     → paso **4**
  - `numerador_rni.py`     → paso **1**
  - `denominadores.py`     → paso **2**
  - `coberturas.py`        → paso **3**
- `programas_2024.py`, `programas_2025.py`, `programas_2026.py`: wrappers.
- `convertir_minsal_programaticas.py`: copia el corte MINSAL (Región-Comuna) al
  esquema local → `output/coberturas_vacunas_AAAA_V7_MINSAL.csv`.
- `seleccionar_base_minsal.py`: elige la mejor base local (SD/CD) por vacuna
  contra el corte y genera `output/coberturas_vacunas_AAAA_V7_MIXTA.csv`.
- `seleccionar_base_final.py`: aplica el criterio aprobado
  `data/prioridad_final_2025.csv` (Usuario/MINSAL/Eliminar del cálculo) y
  genera `output/coberturas_vacunas_AAAA_V7_FINAL.csv` (+ `.xlsx`) con la
  columna `ORIGEN` — la base que usan el dashboard y el informe final.
- `comparar_minsal_programaticas.py`: genera
  `output/comparacion_programaticas_AAAA_vs_minsal.xlsx` (Resumen + Detalle,
  `--base CD/SD/MIXTA`).
- `exportar_excels_imprimibles.py`: Excel para imprimir (matriz comunas ×
  vacuna-dosis, formato estilo proyecto Influenza) del cálculo propio y del
  corte MINSAL.
- `INFORME_MINSAL_2025.md`: bitácora completa de la comparación con MINSAL.

## Dashboard

```bash
pip install -r requirements.txt
streamlit run app.py
```

El dashboard tiene selector de año **2025 / 2024** y muestra los resultados
oficiales de cada año, sin recalcular:

- **2025**: corte MINSAL (`output/coberturas_vacunas_2025_V7_MINSAL.csv`).
- **2024**: Informe Ejecutivo 2024 (`output/coberturas_vacunas_2024_V7_INFORME.csv`,
  generado con `python convertir_informe_2024.py`).

Debajo del selector de año hay un botón **Descargar Excel**: en 2025 baja
`output/coberturas_vacunas_2025_MINSAL.xlsx` (matriz del corte, 15 vacuna-dosis
visibles) y en 2024 el Informe Ejecutivo en Excel.

La vista Coberturas mantiene filtros por nivel, población, vacuna, dosis,
servicio de salud y comuna, y descarga de la tabla filtrada. Se mantienen
ocultas las 8 vacuna-dosis "Eliminar del cálculo".

Criterio del Informe Final (`data/prioridad_final_2025.csv`):

- `Usuario` (cálculo propio, base Mixta): BCG, dTpa 1° y 8° básico, Hep A,
  Hep B, Hexavalente 3ª dosis, Meningocócica conjugada, Varicela 1ª, VPH 4°.
- `MINSAL` (corte oficial): dTpa gestantes, Neumo polisacárida, Neumocócica
  refuerzo, SRP 1ª y 2ª, Varicela 2ª.
- `Eliminar del cálculo`: Hexavalente 1ª/2ª/refuerzo, Meningocócica
  recombinante 1ª/2ª/refuerzo, Neumocócica conjugada 1ª/2ª (y VPH 5° básico).

Requiere haber generado los CSV semilla:

```bash
python convertir_minsal_programaticas.py            # output/..._V7_MINSAL.csv
python convertir_informe_2024.py                    # output/..._2024_V7_INFORME.csv
python seleccionar_base_minsal.py                   # output/..._V7_MIXTA.csv
python seleccionar_base_final.py                    # output/..._V7_FINAL.csv
python comparar_minsal_programaticas.py             # Excel de comparación (base CD)
python comparar_minsal_programaticas.py --base MIXTA
```

La carpeta del corte se puede cambiar con `--corte-dir` o la variable de entorno
`PROGRAMATICAS_MINSAL_DIR`.

## Excel imprimibles

```bash
python exportar_excels_imprimibles.py               # base SD (default)
python exportar_excels_imprimibles.py --base Mixto
python exportar_excels_imprimibles.py --base Final  # informe final
```

Genera en `output/` planillas listas para imprimir (3 hojas cada una:
`Cobertura %` con semáforo, `Vacunados` y `Población objetivo`; 52 comunas +
TOTAL REGIÓN METROPOLITANA; apaisado, ajustado a 1 página de ancho):

- `coberturas_vacunas_2025_PROPIO_SD_imprimible.xlsx` (24 vacuna-dosis).
- `coberturas_vacunas_2025_MINSAL.xlsx` (15 vacuna-dosis visibles; oculta las 8
  "Eliminar del cálculo"; es el Excel que descarga el dashboard).

Con `--base Final` genera además:

- `coberturas_vacunas_2025_FINAL_imprimible.xlsx` (15 vacuna-dosis del informe,
  con fila **Origen** y encabezados marcados `*`/`**`).
- `informe_final_coberturas_2025.xlsx` — **Excel final para enviar**: hoja
  `Resumen` (vacuna, dosis, origen, vacunados, población objetivo y cobertura
  regional con semáforo) + las 3 matrices comunales.

## Pipeline (orden estricto 4 → 1 → 2 → 3, nunca en paralelo)

La fuente RNI por defecto es `..\DATA 2026-10-09` (`Programaticas_{anio}.csv` o
`.parquet`); los CSV se cachean a parquet por chunks en `data/_rni_cache/`.
Rutas sobreescribibles por variables de entorno:

```powershell
setx RNI_PROGRAMATICAS_DIR "D:\DATA\RNI\PROGRAMATICAS"   # opcional (acepta parquet o csv)
setx RNI_SRP_DIR           "D:\DATA\RNI\SRP"
setx NACIMIENTO_DIR        "D:\DATA\NACIMIENTO"
# opcionales: ESTIMACIONES_CSV, PROGRAMATICAS_DATA_DIR, PROGRAMATICAS_OUTPUT_DIR
```

```bash
python programas_2025.py            # pipeline completo del año
python programas_2024.py --pasos 23 # solo pasos 2 y 3
```

## Diferencias metodológicas respetadas por año

- **2024**: denominadores **reciclados** desde versiones previas validadas
  (las fuentes crudas de nacimientos no estaban disponibles originalmente).
- **2025 / 2026**: denominadores calculados desde **NAC crudos** (SRCeI).
- **2025** agrega además matrícula MINEDUC (`data/Población MINEDUC2025.xlsx`,
  hoja `2025RM`) y gestantes (`data/Población programáticas2025.xlsx`, hoja
  `2025 RM`, solo columna de embarazadas 28+ semanas).
- Cohortes infantiles, escolares y años de filtro NAC se derivan de `T`.

## Validación

El núcleo unificado se validó contra los scripts originales ejecutados con los
mismos datos:

- 2025: coberturas CD/SD idénticas (988 filas, 0 diferencias).
- 2025 con insumos completos (NAC + MINEDUC + gestantes): 24 vacunas × 52
  comunas (1.247 filas). Los denominadores escolares y de gestantes calzan
  exactos con el corte MINSAL (84.039 / 97.909 / 95.830 / 97.480 / 62.070).
- 2024: coberturas CD/SD idénticas (1248 filas, 0 diferencias) y
  `Resumen_Regional` idéntico, comparando contra los scripts originales 2024
  (bajo pandas 2.x, ya que el script original 2024 no corre en pandas 3.x).

El núcleo unificado incorpora el arreglo de tipado para pandas 3.x.

## Agregar 2026

1. Asegurar `Programaticas_2026/2027/2028.parquet` y `SRP2026_pais.csv`.
2. Colocar `data/Poblacion Escolar 2026.xlsx` y `data/denominador_gestantes_2026.csv`
   cuando estén disponibles.
3. `python programas_2026.py` y verificar `output/coberturas_vacunas_2026_V7_SD.csv`.
