# Coberturas Vacunas Programáticas RM — 2024 / 2025 / 2026

Dashboard unificado (Streamlit) + pipeline de cálculo, con un **núcleo común**
parametrizado por año. No modifica las carpetas originales
`Programaticas 2024 - Dashboard` ni `Programaticas 2025 - Dashboard`.

## Estructura

- `app.py`: dashboard único con selector de Año (2024/2025/2026).
- `src/config_programaticas.py`: configuración por año (cohortes derivadas de
  `T`, años de filtro NAC, modo de denominadores, fallbacks, textos).
- `src/dashboard_comun.py`: dashboard parametrizado por año.
- `src/pipeline/`:
  - `numerador_srp.py`     → paso **4**
  - `numerador_rni.py`     → paso **1**
  - `denominadores.py`     → paso **2**
  - `coberturas.py`        → paso **3**
- `programas_2024.py`, `programas_2025.py`, `programas_2026.py`: wrappers.

## Dashboard

```bash
pip install -r requirements.txt
streamlit run app.py
```

Elegir 2024 / 2025 / 2026 en la barra lateral. Los CSV semilla
`output/coberturas_vacunas_AAAA_V7_SD/CD.csv` ya están incluidos.

## Pipeline (orden estricto 4 → 1 → 2 → 3, nunca en paralelo)

Rutas externas por variables de entorno (no se versionan rutas locales):

```powershell
setx RNI_PROGRAMATICAS_DIR "D:\DATA\RNI\PROGRAMATICAS"
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
- Cohortes infantiles, escolares y años de filtro NAC se derivan de `T`.

## Validación

El núcleo unificado se validó contra los scripts originales ejecutados con los
mismos datos:

- 2025: coberturas CD/SD idénticas (988 filas, 0 diferencias).
- 2024: coberturas CD/SD idénticas (1248 filas, 0 diferencias) y
  `Resumen_Regional` idéntico, comparando contra los scripts originales 2024
  (bajo pandas 2.x, ya que el script original 2024 no corre en pandas 3.x).

El núcleo unificado incorpora el arreglo de tipado para pandas 3.x.

## Agregar 2026

1. Asegurar `Programaticas_2026/2027/2028.parquet` y `SRP2026_pais.csv`.
2. Colocar `data/Poblacion Escolar 2026.xlsx` y `data/denominador_gestantes_2026.csv`
   cuando estén disponibles.
3. `python programas_2026.py` y verificar `output/coberturas_vacunas_2026_V7_SD.csv`.
