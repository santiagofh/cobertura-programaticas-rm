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

## Variables de entorno (rutas externas, no versionadas)

```
RNI_PROGRAMATICAS_DIR  → parquet Programaticas_{anio}.parquet (pasos 1 y 4)
RNI_SRP_DIR            → SRP{anio}_pais.csv / SRP_2021.csv   (paso 4)
NACIMIENTO_DIR         → NAC{anio}.csv                        (pasos 2 y 4)
ESTIMACIONES_CSV       → proyecciones INE por comuna          (paso 2)
```

## Cifras oficiales MINSAL — SRP RM 2024 (referencia)

- 1RA DOSIS: 64.725
- 2DA DOSIS: 54.868
- Fuente: reunión MINSAL 10-jun-2026 (DEIS/PNI).

## Bancos de prueba

Las carpetas de calibración `SRP/` y `VARICELA/`, y los archivos auxiliares
(`ARCHIVO_NO_V5/`, PDFs, transcripciones, RAR) permanecen **solo** en las
carpetas originales; no se copian aquí.
