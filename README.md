# Motor de recomendaciones eficiente — Opción 2

Parcial de Programación Eficiente. Sistema de recomendación por filtrado
colaborativo (usuario-usuario), con foco en el análisis de eficiencia y no
en la sofisticación del modelo de recomendación en sí.

## Documentación y CI (trabajo de documentación externa + integración continua)

- **Documentación completa** (funcional, arquitectura, instalación, diseño, API, pruebas,
  rendimiento, seguridad y mantenimiento): carpeta [`docs/`](docs/index.md), con MkDocs
  Material. Vista local: `python -m mkdocs serve`. Se publica en GitHub Pages en cada push a `main`.
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) en cada push y PR a `main`, en 7 etapas.
- **Correr localmente los mismos controles que el CI**:

```bash
python -m pip install -r requirements-dev.txt   # versiones fijadas (lock)
python ci.py                                    # todos los controles, igual que el CI
python ci.py --listar                           # comando exacto de cada control
```

Detalle de cada control, herramienta y criterio: [`docs/calidad/controles.md`](docs/calidad/controles.md).

## Estructura

```text
recommender/
  similitud.py    -> Jaccard + puntuación Top-N compartida por todas las versiones
  naive.py        -> implementación BASELINE (línea base)
  optimizado.py   -> índice invertido, heap, memoización, caching con invalidación
  concurrente.py  -> recomendaciones en batch, secuencial vs. multiprocessing.Pool
  historial.py    -> registrar usuarios y procesar historiales (memoria o archivo)
  archivos.py     -> archivos grandes: batching, buffer y procesamiento en paralelo
  data_gen.py     -> datasets y eventos sintéticos
cli.py              -> interfaz de consola (menú interactivo)
api.py              -> API REST con FastAPI
demo.py             -> recorrido guionado de las 5 funcionalidades
benchmark.py        -> tiempos baseline/optimizado/caché/concurrencia + cProfile
benchmark_archivos.py -> escritura/lectura de archivos grandes (tiempo y memoria)
perfilar.py         -> carga de trabajo para py-spy / pyinstrument / SnakeViz
tests/              -> tests con pytest (unitarios, regresión e integración de la API)
docs/  mkdocs.yml   -> documentación con MkDocs (los .rst son la versión Sphinx anterior)
ci.py               -> orquestador de los controles de calidad (local = CI)
benchmarks/         -> benchmarks con pytest-benchmark, línea base y límites de memoria
scripts/            -> comparación de benchmarks, profiling y memoria para el CI
seguridad/          -> excepciones documentadas de los escáneres de seguridad
requirements/       -> dependencias declaradas (.in); requirements*.txt son el lock
.github/            -> workflows de GitHub Actions, CodeQL y Dependabot
calidad/            -> script de análisis y reportes (pylint, flake8, radon, cobertura)
perfiles/           -> salidas de los perfiladores (.prof, .svg, .html)
salida_benchmark*.txt -> salida real de la última corrida de cada benchmark
```

## Cómo correr

```bash
pip install -r requirements-dev.txt   # el motor en sí usa solo la librería estándar

python cli.py                      # menú interactivo
python demo.py                     # recorrido guionado
uvicorn api:app --reload           # API REST -> http://127.0.0.1:8000/docs
python benchmark.py                # rendimiento del motor
python benchmark_archivos.py       # rendimiento de archivos grandes (2M eventos)
python -m pytest --cov             # tests + cobertura
python calidad/analizar.py         # reportes de calidad en calidad/
python -m mkdocs serve             # documentación -> http://127.0.0.1:8000
python ci.py                       # todos los controles de calidad (igual que el CI)
```

## Funcionalidades de la consigna (Opción 2) y dónde están

| Funcionalidad | CLI | API REST | Código |
|---|---|---|---|
| Registrar usuarios y preferencias | opción 1 | `PUT /usuarios` | `historial.registrar_usuario()` |
| Procesar historiales de interacción | opciones 2 y 6 (archivo CSV) | `POST /historial`, `POST /historial/archivo` | `historial.cargar_usuarios_desde_historial()`, `cargar_usuarios_desde_archivo()` |
| Calcular similitudes | opción 3 | `GET /similitud/{a}/{b}` | `RecomendadorOptimizado.similitud()` |
| Generar recomendaciones | opción 4 | `GET /recomendaciones/{id}` | `RecomendadorOptimizado.recomendar()` |
| Obtener los Top N resultados | opción 4 (pide N) | `?top_n=N` | `similitud.top_items()` |

## Idea del sistema

Cada usuario tiene un conjunto de ítems que le gustaron (feedback implícito).
Para recomendar a un usuario se buscan usuarios "vecinos" con gustos
parecidos (similitud de Jaccard sobre los sets de ítems) y se sugieren los
ítems que tienen esos vecinos y el usuario todavía no tiene, priorizando por
similitud acumulada (Top-N).

---

## Segundo parcial: qué se agregó

### 1. Eliminación de código redundante y refactorización

| Antes | Después |
|---|---|
| `naive.py` y `optimizado.py` repetían el bucle que suma la similitud de los vecinos por ítem y el ordenamiento final | Una sola función `similitud.top_items()` que usan ambos |
| `puntaje_similitud` vivía en `naive.py` y la versión optimizada la importaba del baseline | Módulo propio `similitud.py`; la unión se calcula como `\|A\|+\|B\|-\|A∩B\|` sin construir el set |
| `optimizado.recomendar` calculaba la similitud de cada vecino dos veces (en el heap y al puntuar) | Se calcula una vez y se reutiliza el par `(vecino, similitud)` |
| `benchmark.py` tenía dos bloques de cProfile copiados; variable `rec_antes` sin usar | Función `perfilar()` reutilizable; la invalidación ahora se mide de verdad |
| `cli.py` con cadena de `if/elif` | Diccionario `OPCIONES` de despacho |
| Alias de tipo `Dict[int, Set[int]]` repetido en cada módulo | `Perfiles`, definido una sola vez en `similitud.py` |
| Desempates distintos en baseline y optimizado (resultados podían diferir) | Mismo criterio (similitud desc., id asc.): **resultados idénticos**, verificado en tests y en el benchmark |

**Bugs del primer parcial que aparecieron al escribir tests:**

1. El caché de recomendaciones usaba solo el usuario como clave: en `demo.py`, el
   "Top 1" devolvía 2 ítems porque reutilizaba el Top 5 cacheado. Ahora la clave
   es `(usuario, top_n, k_vecinos)`.
2. El caché solo se invalidaba si cambiaba **el propio** usuario. Si cambiaba un
   vecino, se devolvían recomendaciones viejas. Ahora se valida contra una
   versión global.
3. La memoización de similitud no se invalidaba nunca. Ahora cada entrada
   guarda la versión de ambos perfiles.

Cada uno tiene su test de regresión en `tests/test_recomendadores.py`.

### 2. Herramientas de perfilado (Python)

| Herramienta | Comando | Salida |
|---|---|---|
| **SnakeViz** (sobre cProfile) | `python benchmark.py` y luego `snakeviz perfiles/baseline.prof` | `perfiles/baseline.prof`, `optimizado.prof` |
| **py-spy** (muestreo, sin modificar el código) | `py-spy record -o perfiles/py_spy.svg -- python perfilar.py` | `perfiles/py_spy.svg` (flamegraph) |
| **pyinstrument** (herramienta general, en lugar de un APM) | `pyinstrument -r html -o perfiles/pyinstrument.html perfilar.py` | `perfiles/pyinstrument.html`, `.txt` |
| **tracemalloc** (memoria) | integrado en `benchmark_archivos.py` | pico de memoria por estrategia |

En la versión optimizada (la final del primer parcial, sobre la que se construye todo
este parcial), el costo está en la similitud con los candidatos (~44 %) y en construir
el índice invertido (~37 %, se paga una vez). Como referencia, en el baseline el ~66 %
se va en `puntaje_similitud`, llamado 1,2 millones de veces; el índice invertido lo baja
a ~87 mil llamadas.

### 3. Archivos grandes: batching, buffer y paralelismo

`recommender/archivos.py`, medido con `benchmark_archivos.py` (2 M eventos, 20 MiB, 6 núcleos):

| Estrategia | Tiempo | Pico de memoria |
|---|---|---|
| Escritura ingenua (flush por línea) | 10,7 s | — |
| Escritura por lotes de 50 000 + buffer 1 MiB | 2,1 s (**5,2x**) | — |
| Lectura ingenua (`readlines`) | 1,9 s | 277 MiB |
| Lectura por lotes (generador, streaming) | 2,2 s | 172 MiB (12 MiB solo los lotes) |
| Lectura en paralelo (rangos de bytes, 6 procesos) | 1,3 s (**1,7x**) | — |

- El **streaming** usa memoria constante (12 MiB recorriendo lotes) sin importar el tamaño del
  archivo; con `readlines` crece de forma lineal.
- El **paralelo** divide el archivo en rangos de bytes; cada worker descarta la línea
  cortada al inicio de su rango y procesa las que *empiezan* en él, así ninguna se pierde ni se
  duplica (está testeado con 1 a 1000 particiones). Con archivos chicos (100 000 eventos) es
  **más lento** (0,3x) por el costo de crear procesos en Windows.
- La escritura incluye el costo de generar los eventos (~1,5 s), así que la mejora real de E/S es mayor.

### 4. Legibilidad y mantenibilidad (PEP 8)

- Docstrings en estilo Google (`Args`, `Returns`, `Raises`, `Example`) en todos los módulos,
  clases y funciones públicas.
- Nombres descriptivos (`clave_vecino`, `top_items`, `pico_memoria`…), constantes en mayúsculas
  y type hints en todas las firmas.
- Imports ordenados, líneas de 100 caracteres como máximo, sin variables sin usar.

### 5. Documentación con Sphinx

`docs/`, con `autodoc` + `napoleon` + `viewcode`. Se genera con
`python -m sphinx -b html docs docs/_build/html` y se abre en `docs/_build/html/index.html`.
Los ejemplos `>>>` de los docstrings se ejecutan como tests (`--doctest-modules`).

### 6. Análisis de calidad

`python calidad/analizar.py` corre todo y guarda los reportes en `calidad/`:

| Métrica | Primer parcial | Segundo parcial |
|---|---|---|
| pylint | 8,68 / 10 | **10,00 / 10** |
| flake8 (PEP 8) | 15 avisos | **0** |
| radon, complejidad ciclomática promedio | A (3,70) | **A (2,73)** |
| Cobertura de tests | 0 % | **99 %** |

`calidad/pylint_antes.txt` y `flake8_antes.txt` conservan los reportes originales. Para
**SonarQube** está `sonar-project.properties`, que importa la cobertura (`coverage.xml`) y el
reporte de pylint (los pasos están en el mismo archivo).

### 7. Testing

51 tests con **pytest** en `tests/`: unitarios (similitud, archivos, historial), equivalencia
baseline = optimizado sobre un dataset con empates, regresión de los 3 bugs de caché,
concurrente = secuencial, e integración de la API con `TestClient`.

### 8. Framework: FastAPI

`api.py` expone las 5 funcionalidades por HTTP. FastAPI valida las entradas con Pydantic
(422 si `items` está vacío o `top_n` está fuera de rango) y genera documentación interactiva en
`/docs`. `crear_app(recomendador)` recibe el motor por parámetro para que cada test use una
instancia limpia.
