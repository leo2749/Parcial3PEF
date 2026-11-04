# 1. Descripción funcional

## Problema que resuelve

Una plataforma con muchos usuarios e ítems (productos, canciones, películas) necesita sugerir a
cada usuario ítems que probablemente le interesen, a partir de lo que **otros usuarios con
gustos parecidos** ya consumieron. El reto no es el modelo de recomendación en sí, sino hacerlo
**rápido y con poca memoria** cuando crecen la cantidad de usuarios y el tamaño de los
historiales de interacción.

El sistema:

1. Mantiene, para cada usuario, el conjunto de ítems que le gustaron (*feedback implícito*).
2. Mide qué tan parecidos son dos usuarios con la **similitud de Jaccard**:
   `|A ∩ B| / |A ∪ B|`, un valor entre 0 (nada en común) y 1 (idénticos).
3. Para recomendar a un usuario, toma sus `k` vecinos más parecidos y le sugiere los ítems que
   ellos tienen y él no, ordenados por similitud acumulada (**Top-N**).

## Alcance

**Incluye:**

- Motor de recomendación en Python puro (sin dependencias externas) con dos implementaciones:
  una *baseline* deliberadamente simple y una *optimizada*, que dan resultados idénticos.
- Carga de historiales desde memoria o desde archivos CSV grandes (streaming por lotes o en
  paralelo con varios procesos).
- Cálculo de recomendaciones en *batch*, secuencial o concurrente.
- Tres interfaces: menú de consola (`cli.py`), API REST (`api.py`, FastAPI) y recorrido
  guionado (`demo.py`).
- Herramientas de medición: benchmarks, profiling de CPU y medición de memoria.

**No incluye (fuera de alcance):**

- Persistencia: los perfiles viven en memoria; al reiniciar el proceso se pierden.
- Autenticación y autorización de la API (pensada para uso local o detrás de un gateway).
- Feedback explícito (puntajes de 1 a 5), filtrado basado en contenido o modelos de ML.
- Despliegue productivo (contenedores, escalado horizontal).

## Requisitos funcionales

| Id | Requisito | CLI | API REST | Código |
|---|---|---|---|---|
| RF1 | Registrar usuarios y sus preferencias | opción 1 | `PUT /usuarios` | `historial.registrar_usuario()` |
| RF2 | Procesar historiales de interacción (memoria o archivo CSV) | opciones 2 y 6 | `POST /historial`, `POST /historial/archivo` | `historial.cargar_usuarios_desde_historial()`, `cargar_usuarios_desde_archivo()` |
| RF3 | Calcular la similitud entre dos usuarios | opción 3 | `GET /similitud/{a}/{b}` | `RecomendadorOptimizado.similitud()` |
| RF4 | Generar recomendaciones para un usuario | opción 4 | `GET /recomendaciones/{id}` | `RecomendadorOptimizado.recomendar()` |
| RF5 | Obtener los Top N resultados | opción 4 (pide N) | `?top_n=N` | `similitud.top_items()` |
| RF6 | Listar usuarios registrados | opción 5 | `GET /usuarios` | `RecomendadorOptimizado.usuarios` |

## Requisitos no funcionales

| Id | Requisito | Cómo se verifica |
|---|---|---|
| RNF1 | La versión optimizada da **exactamente** el mismo resultado que la baseline | `tests/test_recomendadores.py` (equivalencia sobre 800 usuarios con empates) |
| RNF2 | La versión optimizada es al menos **3x** más rápida que la baseline | Control `benchmark-regresion` del CI |
| RNF3 | Sin regresiones de rendimiento mayores al 50 % respecto de la línea base | Control `benchmark-regresion` del CI |
| RNF4 | Leer un historial en streaming usa memoria acotada, independiente del tamaño del archivo | Control `memoria` (escenario `leer_archivo_streaming_lotes`) |
| RNF5 | Cobertura de pruebas ≥ 90 % | Control `pytest` (`--cov-fail-under=90`) |
| RNF6 | Sin vulnerabilidades conocidas en dependencias ni secretos en el repositorio | Controles `pip-audit` y `gitleaks` |
| RNF7 | La API valida entradas y no lee archivos fuera del directorio de datos | Tests de `tests/test_api.py` (422 y 403) |
| RNF8 | Compatible con Python 3.11 a 3.13 | Matriz de versiones del job de pruebas |

## Glosario

Perfil
:   Conjunto de ítems que le gustaron a un usuario: `{usuario_id: set(items)}`.

Vecino
:   Usuario con similitud mayor que cero con el usuario objetivo.

Candidato
:   Usuario que comparte al menos un ítem con el objetivo (solo ellos pueden ser vecinos).

Historial
:   Secuencia de eventos `(usuario_id, item_id)`, por ejemplo un log de clics o compras.
