# 6. Pruebas

## Estrategia

| Nivel | Qué se prueba | Herramienta | Dónde |
|---|---|---|---|
| Unitarias | Similitud, orden de vecinos, Top-N, parseo y E/S de archivos, historiales | pytest | `tests/test_similitud.py`, `test_archivos.py`, `test_historial.py` |
| Equivalencia (oráculo) | La versión optimizada da **lo mismo** que la baseline en un dataset con empates | pytest + parametrización | `tests/test_recomendadores.py` |
| Regresión | Los 3 bugs de caché del primer parcial no vuelven | pytest | `tests/test_recomendadores.py` |
| Concurrencia | Batch concurrente = secuencial; paralelo por rangos = lectura secuencial | pytest | `tests/test_concurrente.py`, `test_archivos.py` |
| Integración | Endpoints HTTP, validación (422), errores (404) y seguridad (403) | `fastapi.testclient` | `tests/test_api.py` |
| Doctests | Los ejemplos `>>>` de los docstrings siguen siendo verdaderos | `--doctest-modules` | `recommender/*.py` |
| Rendimiento | Tiempo de operaciones representativas | pytest-benchmark | `benchmarks/` (ver [Rendimiento](rendimiento.md)) |

Principios:

- **Datos deterministas**: los datasets sintéticos usan semilla fija (`data_gen.py`), así que un
  fallo siempre se puede reproducir.
- **Oráculo de correctitud**: la baseline es simple y obviamente correcta; la versión
  optimizada se compara contra ella en 4 combinaciones de `top_n` y `k_vecinos`.
- **Aislamiento**: cada test crea su propio motor (`crear_app(recomendador)` recibe el motor por
  parámetro) y usa `tmp_path` para archivos.
- Los benchmarks están en una carpeta aparte (`benchmarks/`) para que `pytest` a secas siga
  siendo rápido.

## Casos de prueba destacados

| Caso | Verifica |
|---|---|
| `test_optimizado_equivale_al_baseline[top_n-k]` | RNF1: resultados idénticos en 22 usuarios × 4 configuraciones |
| `test_cache_distingue_top_n` | Regresión: pedir Top 1 después de Top 5 devolvía 2 ítems |
| `test_cache_se_invalida_si_cambia_un_vecino` | Regresión: el caché solo miraba la versión del propio usuario |
| `test_memo_de_similitud_se_invalida` | Regresión: la memoización nunca se invalidaba |
| `test_resultado_cacheado_no_se_puede_corromper_desde_afuera` | El caché devuelve copias |
| `test_rangos_procesan_cada_linea_una_sola_vez[1..1000]` | El corte por bytes no pierde ni duplica líneas |
| `test_lineas_invalidas_se_ignoran` | Robustez ante CSV con basura |
| `test_concurrente_equivale_a_secuencial` | `multiprocessing.Pool` da lo mismo que el bucle |
| `test_validacion_de_entrada_422`, `test_top_n_fuera_de_rango_422` | Contratos de la API |
| `test_cargar_archivo_rechaza_path_traversal`, `..._ruta_absoluta_externa` | Corrección de seguridad R1 |

## Ejecución

```bash
python -m pytest                    # rápido, sin cobertura
python ci.py pruebas                # igual que el CI: cobertura + umbral + reportes
python -m pytest -k cache -v        # filtrar por nombre
```

## Criterios de aprobación

| Criterio | Umbral | Configurado en |
|---|---|---|
| Pruebas fallidas | 0 | — |
| Cobertura de líneas (`recommender/` y `api.py`) | ≥ 90 % | `pyproject.toml` (`fail_under`) y `--cov-fail-under=90` |
| Versiones de Python | 3.11 y 3.13 | matriz del job `pruebas` |

## Resultados

Última corrida local (Windows 10, Python 3.13.7):

```text
55 passed in 3.5s

Name                         Stmts   Miss  Cover   Missing
api.py                          66      0   100%
recommender/archivos.py         99      1    99%   205
recommender/concurrente.py      17      3    82%   22, 26-29
recommender/data_gen.py         12      0   100%
recommender/historial.py        22      0   100%
recommender/naive.py            10      0   100%
recommender/optimizado.py       46      0   100%
recommender/similitud.py        22      0   100%
TOTAL                          294      4    99%
```

Las líneas sin cubrir de `concurrente.py` sí se ejecutan, pero **dentro de los procesos
worker**, que coverage no mide por defecto. La línea 205 de `archivos.py` es un corte defensivo
ante fin de archivo inesperado.

Cada corrida del CI publica `reportes/pytest.xml` (JUnit), `reportes/coverage.xml` y el
reporte HTML de cobertura (`reportes/cobertura_html/`) como artefactos.
