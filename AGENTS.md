# Orden de ejecución obligatorio

NUNCA ejecutar scripts en paralelo. El orden es estricto y secuencial:

```
4) numerador_srp    → output/*base_numerador_rni_{T}_SRP_V7_nac.parquet
1) numerador_rni     → output/*base_numerador_rni_{T}_V7.csv + numerador_rni_{T}_V7_CD/SD
2) denominadores     → output/*denominador_*_{T}_V7.csv
3) coberturas        → output/*coberturas_vacunas_{T}_V7_CD/SD.csv/.xlsx
```

Reglas:
1. Ejecutar en orden 4 → 1 → 2 → 3.
2. Nunca en paralelo: el paso 1 consume el parquet que genera el paso 4.
3. El paso 3 depende de los numeradores (1) y denominadores (2).
4. Cada paso queda en `python programas_{T}.py` (wrapper) o `src/pipeline/*.py`.

## Variables de entorno (rutas externas; con valores por defecto locales)

```
RNI_PROGRAMATICAS_DIR  → carpeta RNI (por defecto ..\DATA 2026-10-09);
                         acepta Programaticas_{anio}.parquet o .csv (pasos 1 y 4)
RNI_PROGRAMATICAS_FALLBACK_DIR → respaldo para años ausentes (def. D:\DATA\RNI\PROGRAMATICAS)
RNI_SRP_DIR            → SRP{anio}_pais.csv / SRP_2021.csv   (paso 4)
NACIMIENTO_DIR         → NAC{anio}.csv                        (pasos 2 y 4)
ESTIMACIONES_CSV       → proyecciones INE por comuna          (paso 2)
```

Los CSV crudos (~2,5 GB) se cachean por chunks en `data/_rni_cache/Programaticas_{anio}.parquet` la primera vez que se leen.

## Fuente de datos 2025 — restricción a VACUNAS

El cálculo 2025 usa SOLO los datos de la carpeta hermana `..\DATA 2026-10-09`
(`Programaticas_2025/2026.csv`, cacheados el 13-10-2026 en `data/_rni_cache/`).
Al re-ejecutar el pipeline 2025, desactivar el respaldo externo:

```powershell
$env:RNI_PROGRAMATICAS_FALLBACK_DIR = ""   # evita leer D:\DATA\RNI\PROGRAMATICAS
```

Auxiliares que NO existen en VACUNAS y se mantienen desde `D:\DATA`:
- `RNI_SRP_DIR` = `D:\DATA\RNI\SRP` (CSV nacionales SRP, DEIS)
- `NACIMIENTO_DIR` = `D:\DATA\NACIMIENTO` (NAC crudos SRCeI)

## Decisión CD / SD — 2025 (aprobada; no re-debatir)

Regla: partir de **SD** (sin duplicados por persona-vacuna) y cambiar a
**CD** (con duplicados) solo si la diferencia comunal acumulada contra el
corte MINSAL baja a menos de la mitad (`SAE_CD < 0.5 × SAE_SD`).

- **CD (4 vacunas):** BCG, DTPA 8° BÁSICO, HEPATITIS A PEDIÁTRICA,
  MENINGOCOCICA RECOMBINANTE 2DA DOSIS.
- **SD:** todo el resto. SRP empata (misma data en ambas bases).
- Operacionaliza en la base Mixta: `python seleccionar_base_minsal.py` →
  `output/coberturas_vacunas_2025_V7_MIXTA.csv` (1.247 filas, 24 vacunas);
  usada por los scripts de comparación (el dashboard ya no expone el
  cálculo local: es espejo del corte MINSAL).

Evidencia (capacitación MINSAL 10-jun-2026, `Transcripcion reunion.txt`):
MINSAL **no deduplica** por persona ni por ID_INMUNIZACION; su único filtro
es "solo filas distintas" (elimina únicamente filas 100% idénticas; si cambia
cualquier variable, como la comuna, el registro se mantiene) — min. 36:30–37:47.
El equipo SEREMI verificó en la reunión que manteniendo duplicados (CD) las
escolares calzan exacto con MINSAL — min. 33:57–34:03.

## Informe FINAL 2025 — mezcla Usuario / MINSAL (aprobado)

Criterio único en `data/prioridad_final_2025.csv` (23 vacuna-dosis con
prioridad Usuario / MINSAL / Eliminar del calculo; espejo de la hoja
"Resumen" de `comparacion_programaticas_2025_vs_minsal_revisado.xlsx`).
Los Excel del informe usan SOLO esta mezcla:

- **Usuario** (cálculo propio, base Mixta, marca `**`): BCG, dTpa 1° básico,
  dTpa 8° básico, Hep A, Hep B, Hexavalente 3ª dosis, Meningocócica
  conjugada, Varicela 1ª dosis, VPH 4° básico.
- **MINSAL** (corte oficial sin recalcular, marca `*`): dTpa gestantes,
  Neumocócica polisacárida, Neumocócica conjugada refuerzo, SRP 1ª dosis,
  SRP 2ª dosis, Varicela 2ª dosis.
- **Eliminar del cálculo** (8): Hexavalente 1ª/2ª/refuerzo, Meningocócica
  recombinante 1ª/2ª/refuerzo, Neumocócica conjugada 1ª/2ª. VPH 5° básico
  también queda fuera (el criterio solo lista VPH 1ª dosis o única).

Operacionalización:
- `python seleccionar_base_final.py` →
  `output/coberturas_vacunas_2025_V7_FINAL.csv` (+ `.xlsx`), 15 vacuna-dosis
  × 52 comunas = **780 filas**, con columna `ORIGEN`.
- El imprimible/informe marca cada vacuna-dosis con `*` (MINSAL) o `**`
  (Usuario) y leyenda al pie; el dashboard ya no muestra esta mezcla.
- `python exportar_excels_imprimibles.py --base Final` →
  `coberturas_vacunas_2025_FINAL_imprimible.xlsx` (matriz con fila Origen)
  y `informe_final_coberturas_2025.xlsx` (Resumen + 3 matrices; para enviar).

Nota de trazabilidad: la columna "usuario" del comparativo revisado proviene
del numerador CD (script antiguo `comparar_minsal_2025.py`), por lo que puede
diferir en decenas de vacunados por comuna respecto de la base Mixta usada en
el informe (misma cobertura con ±0,1 pp).

## Cifras oficiales MINSAL — SRP RM 2024 (referencia)

- 1RA DOSIS: 64.725
- 2DA DOSIS: 54.868
- Fuente: reunión MINSAL 10-jun-2026 (DEIS/PNI).

## Dashboard — espejo de la fuente oficial (2024 / 2025)

`app.py` es un **reflejo de los resultados oficiales publicados, sin
recalcular** (selector de año 2025 / 2024; sin "Cálculo Final", sin pestaña
Comparativa). Mantiene ocultas las 8 vacuna-dosis "Eliminar del cálculo"
(Hexa 1ª/2ª/refuerzo, MenR 1ª/2ª/refuerzo, Neumo conj. 1ª/2ª).

- **2025** → corte MINSAL `CORTE MINSAL 2026-10-09\PROGRAMATICAS 2025`
  (`output/coberturas_vacunas_2025_V7_MINSAL.csv`, 23 combinaciones × 52 = 1.196 filas).
- **2024** → `2024 Cerrado\2026-06-17_..._Informe Ejecutivo 2024.xlsx`
  (corte 15-06-2026, 15 vacuna-dosis × 52 = 780 filas). Convertido con
  `python convertir_informe_2024.py` →
  `output/coberturas_vacunas_2024_V7_INFORME.csv` (ruta del Excel
  sobreescribible con `PROGRAMATICAS_INFORME_2024_XLSX`).
- Configuración por año en `src/config_programaticas.py`
  (`oficial_disponible`, `oficial_etiqueta`, `oficial_archivo`).
- Verificación del imprimible MINSAL contra los CSV del corte (3 hojas,
  52 comunas + TOTAL, 15 vacuna-dosis visibles, cuadre nacional y semilla):
  `python verificar_minsal_imprimible.py` → PASS.
- `src/minsal_comparacion.py` conserva el cruce local vs MINSAL para scripts
  (ya no se usa en el dashboard).
- `python exportar_excels_imprimibles.py [--base SD/CD/Mixto/Final]` sigue
  generando los imprimibles en `output/`:
  - `coberturas_vacunas_2025_PROPIO_{base}_imprimible.xlsx`
  - `coberturas_vacunas_2025_MINSAL_imprimible.xlsx`
  3 hojas (Cobertura % con semáforo, Vacunados, Población objetivo), matriz
  52 comunas + TOTAL REGIÓN METROPOLITANA, apaisado ajustado a 1 página de
  ancho. El archivo PROPIO trae 24 vacuna-dosis; el MINSAL las 15 visibles
  del dashboard (oculta las 8 "Eliminar del cálculo").

## Bancos de prueba

Las carpetas de calibración `SRP/` y `VARICELA/`, y los archivos auxiliares
(`ARCHIVO_NO_V5/`, PDFs, RAR) permanecen **solo** en las carpetas originales;
no se copian aquí. Excepción: `Transcripcion reunion.txt` y
`Reunión de Microsoft Teams.docx` (capacitación MINSAL 10-jun-2026) viven en
esta carpeta como evidencia de la metodología y de la decisión CD/SD.
