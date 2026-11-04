# 7. Rendimiento

Todas las mediciones de esta página se reproducen con `python ci.py rendimiento`. Corrida de
referencia: Windows 10, Python 3.13.7, Intel de 6 núcleos lógicos. Los valores absolutos
cambian según la máquina; lo que se controla en el CI son **valores relativos** (ver
[criterios](#criterios-del-ci)).

## Benchmarks (pytest-benchmark)

Dataset: 10 000 usuarios, 5 000 ítems, 15 ítems por usuario; 20 consultas por ronda.

| Benchmark | Mediana | Por unidad |
|---|---:|---:|
| `recomendar_baseline` (20 consultas) | 146 ms | 7,3 ms/consulta |
| `recomendar_optimizado_sin_cache` (20 consultas, caché vacío) | 22 ms | 1,1 ms/consulta |
| `recomendar_optimizado_con_cache` (1000 consultas) | 0,27 ms | 0,3 µs/consulta |
| `construir_indice_invertido` | 43 ms | se paga una vez |
| `puntaje_similitud` (2000 pares) | 1,1 ms | 0,55 µs/par |
| `procesar_historial_en_memoria` (100 000 eventos) | 26 ms | — |
| `leer_archivo_por_lotes` (100 000 eventos) | 90 ms | — |
| `calibracion` (carga fija de referencia) | 17 ms | — |

**Speedup** de la versión optimizada frente a la baseline: **5,7x a 6,7x** según la corrida
(mínimo exigido por el CI: 3x). Con caché, una consulta repetida es ~25 000 veces más rápida.

Los benchmarks más amplios del segundo parcial siguen disponibles:

| Script | Mide | Resultado de referencia |
|---|---|---|
| `python benchmark.py` | baseline / optimizado / caché / concurrencia, 15 000 usuarios | ver `salida_benchmark.txt` |
| `python benchmark_archivos.py` | E/S de 2 M eventos (20 MiB) | escritura por lotes **5,2x** más rápida; lectura en paralelo **1,7x** |

## Profiling de CPU

Dos herramientas complementarias sobre la carga de `perfilar.py` (80 consultas baseline +
80 optimizadas sobre 15 000 usuarios):

| Herramienta | Tipo | Reporte |
|---|---|---|
| cProfile (`scripts/perfilar_cpu.py`) | Determinista: cuenta cada llamada | `reportes/perfil_cpu.txt`, `.json`, `.prof` (abrir con `snakeviz`) |
| pyinstrument | Por muestreo: bajo overhead, árbol de llamadas | `reportes/pyinstrument.html` |
| py-spy (manual) | Muestreo externo, sin modificar el código | `py-spy record -o perfil.svg -- python perfilar.py` |

Top por tiempo propio (cProfile):

| Tiempo propio | Llamadas | Función |
|---:|---:|---|
| 1,06 s | 1 287 227 | `similitud.py:puntaje_similitud` |
| 0,38 s | 80 | `naive.py:recomendar` |
| 0,19 s | 1 652 099 | `len` (built-in) |
| 0,11 s | 1 | `optimizado.py:__init__` (índice invertido) |
| 0,09 s | 87 509 | `optimizado.py:similitud` |

**Lectura**: casi todo el costo está en la similitud. La baseline la llama ~1,2 M veces (una
por usuario y consulta); el índice invertido la reduce a ~87 000 llamadas (solo candidatos),
que es exactamente de donde sale el speedup.

## Complejidad temporal

| Operación | Baseline | Optimizado |
|---|---|---|
| Recomendar (primera vez) | O(n·m + n log n) | O(c·m + c log k + i log N) |
| Recomendar (repetida) | igual | O(1) caché |
| Similitud entre dos usuarios | O(m) | O(m), O(1) memoizada |
| Actualizar un usuario | O(1) | O(m) (índice incremental) |
| Construir el índice | — | O(n·m) una vez |
| Procesar historial | O(E) | O(E) |
| Leer archivo en streaming | O(E) tiempo, **O(lote)** memoria | — |
| Leer archivo en paralelo | O(E / p) por worker + combinación | — |

*n* usuarios · *m* ítems por usuario · *c* candidatos · *k* vecinos · *i* ítems de los vecinos ·
*N* = `top_n` · *E* eventos · *p* procesos.

## Consumo de memoria

`scripts/medir_memoria.py` mide el **pico** con `tracemalloc` (máximo de 3 repeticiones):

| Escenario | Pico | Límite del CI |
|---|---:|---:|
| Construir el índice invertido (15 000 usuarios) | 14,6 MiB | 19,0 MiB |
| 100 consultas con caché | 34,7 MiB | 45,1 MiB |
| Recorrer un CSV de 300 000 eventos en streaming | 12,4 MiB | 16,1 MiB |
| Construir perfiles desde ese CSV | 45,1 MiB | 58,6 MiB |

El streaming queda acotado por el tamaño del lote (50 000 eventos): con 2 M eventos
(`benchmark_archivos.py`) el recorrido sigue en ~12 MiB, mientras que `readlines()` llega a
277 MiB.

## Criterios del CI

| Control | Criterio de rechazo | Por qué así |
|---|---|---|
| `benchmark-regresion` | Un benchmark **normalizado** empeora > 50 % respecto de `benchmarks/linea_base.json` | Normalizar por `calibracion` quita la mayor parte de la diferencia de hardware; el 50 % absorbe el ruido de los runners compartidos (en la misma máquina se observaron variaciones de hasta 22 %) |
| `benchmark-regresion` | Speedup optimizado/baseline < 3x en la misma corrida | Comparación dentro de la misma máquina: independiente del hardware |
| `memoria` | Un pico supera su límite (`benchmarks/limites_memoria.json`, medido × 1,3) | tracemalloc cuenta asignaciones de Python: es casi determinista con la misma versión de Python |
| Profiling | Solo falla si no se puede generar | Es diagnóstico; se revisa cuando el benchmark detecta una regresión |

Para actualizar la línea base cuando una mejora o un cambio intencional la invalida, ver
[Mantenimiento](mantenimiento.md#actualizar-lineas-base).
