# Informe MINSAL 2025 — Programáticas e Influenza (RM)

Resumen de todo el trabajo realizado con el corte oficial
`VACUNAS\CORTE MINSAL 2026-10-09` (subcarpetas `PROGRAMATICAS 2025` e
`INFLUENZA 2025`), incluyendo conversiones, comparaciones contra los cálculos
locales y las opciones agregadas al dashboard de Programáticas.

---

## 1. Corte MINSAL recibido

- **Programáticas 2025** (`CORTE MINSAL 2026-10-09\PROGRAMATICAS 2025\`): 13 CSV
  por vacuna, 52 comunas RM + fila nacional por vacuna/dosis.
- **Influenza 2025** (`CORTE MINSAL 2026-10-09\INFLUENZA 2025\`): 1 CSV
  ("Tabla cruzada Región-Comuna") con 52 comunas: Total Población, Vacunados
  1° y única dosis, Avance de vacunación.
- Formato numérico chileno (`57.777`, `94,1%`), UTF-8 con BOM, espacios NBSP en
  algunos nombres de comuna (ej. "Pedro Aguirre Cerda").

---

## 2. Influenza 2025

### 2.1 Conversión del corte a Excel

Script `COBERTURA INFLUENZA\convertir_minsal_influenza.py` reutilizable:
`python convertir_minsal_influenza.py` genera, junto al CSV original,
**`cobertura_influenza_2025_rm_MINSAL.xlsx`** con el formato del proyecto
Influenza (3 hojas: `Cobertura %`, `Vacunados`, `Denominador`), 52 comunas +
fila TOTAL REGIÓN METROPOLITANA, semáforo de color y estilos idénticos al
Excel oficial del proyecto.

Cifras del corte: **3.046.290 vacunados / 3.854.709 población = 79,03 %**.

### 2.2 Comparación dashboard vs MINSAL

| Métrica | MINSAL | Dashboard | Diferencia |
|---|---:|---:|---:|
| Vacunados | 3.046.290 | 3.044.438 | **−1.852 (−0,06 %)** |
| Población | 3.854.709 | 3.854.709 | 0 (idéntica en 52/52 comunas) |
| Cobertura | 79,03 % | 78,98 % | −0,05 pp |

- 45 comunas con dashboard menor, 6 mayor, 1 igual (San José de Maipo).
- Rango: −174 (Santiago) a +68; todas las diferencias ≤ 0,14 pp.
- **Conclusión**: mismo universo poblacional y numerador prácticamente calcado;
  la brecha es de fecha de extracción/deduplicación, no metodológica.

---

## 3. Programáticas 2025

### 3.1 Insumos y recalculo local

Se incorporaron los insumos pendientes:

- `data\Población MINEDUC2025.xlsx` (hoja `2025RM`): matrícula 1°/4°/5°/8° básico.
- `data\Población programáticas2025.xlsx` (hoja `2025 RM`): se usa **solo la
  columna de gestantes 28+ semanas** (62.070). Las columnas "1 año" (61.065) y
  "18 meses" (93.667) **no** coinciden con MINSAL (61.381 y 64.775, que sí
  calzan con las cohortes NAC locales); "3 años" y "65 años" sí coinciden.

Cambios: `src/config_programaticas.py` (archivos/hojas por año) y
`src/pipeline/denominadores.py` (lector MINEDUC hoja RM + sección gestantes).
Ejecutado `python programas_2025.py --pasos 23`:

- Resultado: **24 vacunas × 52 comunas = 1.247 filas** (antes 19 vacunas / 988).
- Denominadores escolares/gestantes calzan exacto con MINSAL:
  84.039 / 97.480 / 95.830 / 97.909 y 62.070.

### 3.2 Fuente oficial en el dashboard (espejo)

- `convertir_minsal_programaticas.py` copia el corte al esquema local:
  **`output/coberturas_vacunas_2025_V7_MINSAL.csv`** (23 combinaciones × 52 =
  1.196 filas, coberturas publicadas sin recalcular, fila nacional usada para
  validar; cuadre OK en las 23).
- `convertir_informe_2024.py` convierte el cierre 2024
  (`2024 Cerrado\..._Informe Ejecutivo 2024.xlsx`, corte 15-06-2026) a
  **`output/coberturas_vacunas_2024_V7_INFORME.csv`** (15 vacuna-dosis × 52 =
  780 filas; cuadre OK contra `Resumen_Regional (final)`).
- Dashboard (`app.py`): selector de año **2025 / 2024**, espejo de la fuente
  oficial (sin recalcular), sin cálculo propio ni pestaña comparativa; badge
  con la etiqueta del corte y filtros/Servicio de Salud/descarga Excel igual
  que siempre. Se mantienen ocultas las 8 vacuna-dosis "Eliminar del cálculo".
- `python verificar_minsal_imprimible.py` → PASS: el imprimible
  `coberturas_vacunas_2025_MINSAL_imprimible.xlsx` es copia fiel del corte
  (3 hojas × 53 filas × 23 vacunas, 0 diferencias; cuadre nacional 23/23).

### 3.3 Comparación corte vs cálculo local

Regenerada con `comparar_minsal_programaticas.py` →
**`output/comparacion_programaticas_2025_vs_minsal.xlsx`** (Resumen 23 filas +
Detalle 1.196 filas, base CD). Totales de los 23 combos compartidos:

| Base | Vacunados | Diferencia vs MINSAL |
|---|---:|---:|
| MINSAL | 1.381.672 | — |
| Local SD (dashboard) | 1.380.462 | +1.210 |
| Local CD | 1.382.687 | −1.015 |
| **Local Mixto** | **1.382.348** | **−676** |

Denominadores: calzan exacto en 14/23 combos. Difieren RN (59.358 vs 58.239) y
cohortes 2M/4M/6M (59.148/59.223/59.418 vs 58.582/58.797/59.156), todas de
nacimientos NAC crudo.

### 3.4 Vacunas con mayor diferencia

| Vacuna | Dif nacional (MINSAL − local) | Peor comuna (dif) | Causa |
|---|---:|---|---|
| SRP 2ª dosis | −794 (SD=CD) | Santiago +679 (70,5 % vs 56,4 %) | dataset SRP distinto |
| HEP A pediátrica | +1.651 SD / −95 CD | Las Condes +376 (SD) | duplicados (CD calza) |
| NEUMO POLI (65) | +584 SD / +557 CD | Santiago +64; Estación Central +40 | corte distinto |
| SRP 1ª dosis | +238 (SD=CD) | Las Condes +74 | dataset SRP distinto |
| DTPA GESTANTES | +352 / +346 | La Florida +28; Santiago +27 | corte distinto |
| VARICELA 2ª dosis | −180 / −185 | Maipú −14; Santiago −13 | disperso |
| HEXAVALENTE 1ª | −109 / −121 | La Pintana −29 | disperso |
| NEUMOCÓCICA CONJ. 1ª/2ª/ref | −100 a −142 | disperso | local bajo MINSAL |
| VARICELA 1ª | −49 / −65 | disperso | disperso |

El resto (BCG, HepB, MEN RECO, MEN CONJ, HEXA 2ª/3ª/ref, VPH, DTPA escolar)
queda bajo ±60 y con la base elegida casi calcado.

### 3.5 Base Mixta (mejor base por vacuna)

Regla aprobada: partir de **SD** y cambiar a **CD** solo cuando la diferencia
comunal acumulada (SAE) contra MINSAL baja a menos de la mitad
(`SAE_CD < 0.5 × SAE_SD`).

- Vacunas que usan **CD**: BCG (SAE 2 vs 66), DTPA 8° básico (16 vs 52),
  Hepatitis A (95 vs 1.657), Meningocócica recombinante 2ª dosis (8 vs 24).
- Todo el resto usa **SD** (SRP empata: misma data en ambas bases).
- Evidencia en la capacitación MINSAL 10-jun-2026 (`Transcripcion reunion.txt`):
  MINSAL no deduplica por persona ni por ID_INMUNIZACION; su único filtro es
  "solo filas distintas" (filas 100% idénticas) — min. 36:30–37:47. Con
  duplicados (CD) las escolares calzan exacto con MINSAL — min. 33:57–34:03.
  Regenerada el 15-10-2026 con DATA 2026-10-09: misma lista CD y total Mixto
  −676 (sin cambios).
- Generado con `seleccionar_base_minsal.py` →
  **`output/coberturas_vacunas_2025_V7_MIXTA.csv`** (1.247 filas, 24 vacunas).
- Efecto: SAE total baja de ~9.778 (SD) a ~8.100 (Mixto); brecha nacional
  −676 (vs +1.210 SD / −1.015 CD).

---

## 4. Archivos y scripts creados/modificados

### Creados (Programáticas)

- `convertir_minsal_programaticas.py` — corte MINSAL → CSV semilla local.
- `convertir_informe_2024.py` — Informe Ejecutivo 2024 (Excel) → CSV semilla.
- `verificar_minsal_imprimible.py` — audita imprimible MINSAL vs corte oficial.
- `comparar_minsal_programaticas.py` — Excel de comparación (`--base CD/SD/MIXTA`).
- `seleccionar_base_minsal.py` — base Mixta por vacuna.
- `src/minsal_comparacion.py` — cruce local vs MINSAL para la pestaña
  **Comparativa vs MINSAL** del dashboard.
- `exportar_excels_imprimibles.py` — Excel para imprimir (matriz comunas ×
  vacuna-dosis estilo proyecto Influenza, 3 hojas + TOTAL RM).
- `output/coberturas_vacunas_2025_V7_MINSAL.csv` — semilla MINSAL (1.196 filas).
- `output/coberturas_vacunas_2024_V7_INFORME.csv` — semilla Informe 2024 (780 filas).
- `output/coberturas_vacunas_2025_V7_MIXTA.csv` — semilla Mixta (1.247 filas).
- `output/comparacion_programaticas_2025_vs_minsal.xlsx` — comparación.
- `output/coberturas_vacunas_2025_PROPIO_SD_imprimible.xlsx` — matriz
  imprimible del cálculo propio (24 vacuna-dosis).
- `output/coberturas_vacunas_2025_MINSAL_imprimible.xlsx` — matriz imprimible
  del corte MINSAL (15 vacuna-dosis visibles; oculta las 8 "Eliminar del cálculo").

### Modificados (Programáticas)

- `src/config_programaticas.py` — campos MINEDUC/programáticas y MINSAL por año.
- `src/pipeline/denominadores.py` — lector MINEDUC 2025 + denominador gestantes.
- `src/dashboard_comun.py` — selector Propio / Mixto / MINSAL (2025), badges y
  metodología.
- `README.md`, `data/LEEME.txt`.

### Creado (Influenza, otro proyecto)

- `COBERTURA INFLUENZA\convertir_minsal_influenza.py` y
  `CORTE MINSAL 2026-10-09\INFLUENZA 2025\cobertura_influenza_2025_rm_MINSAL.xlsx`.

## 5. Cómo reproducir

```bash
# Programáticas: semillas MINSAL, Informe 2024 y Mixta + comparación
python convertir_minsal_programaticas.py                  # output/..._V7_MINSAL.csv
python convertir_informe_2024.py                          # output/..._2024_V7_INFORME.csv
python seleccionar_base_minsal.py                         # output/..._V7_MIXTA.csv
python comparar_minsal_programaticas.py                   # comparación (base CD)
python comparar_minsal_programaticas.py --base MIXTA      # comparación con Mixto
python exportar_excels_imprimibles.py                     # Excel imprimibles (matriz)
python verificar_minsal_imprimible.py                     # audita imprimible vs corte

# Dashboard (espejo oficial 2024 / 2025)
streamlit run app.py        # selector de año; solo resultados oficiales
```

La carpeta del corte se puede cambiar con `--corte-dir` o la variable de
entorno `PROGRAMATICAS_MINSAL_DIR`.

## 6. Notas y pendientes

- Diferencias estructurales que no se resuelven eligiendo base: **SRP 1ª/2ª**
  (origen standalone SRP), **NEUMO POLI**, **DTPA gestantes**, **VARICELA 2ª**.
  Santiago y Las Condes concentran la brecha de SRP 2ª (~679 y ~522 registros).
- El pipeline local se ejecutó solo en los pasos 2→3 (los numeradores del
  13-10-2026 ya existían); orden estricto 4→1→2→3 respetado cuando corresponde.
- Cifras oficiales MINSAL de referencia para SRP RM 2024: 1ª dosis 64.725,
  2ª dosis 54.868 (reunión MINSAL 10-jun-2026).
