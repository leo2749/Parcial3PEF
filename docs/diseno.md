# 4. Diseño técnico

## Estructuras de datos

| Estructura | Tipo | Dónde | Por qué |
|---|---|---|---|
| Perfiles | `dict[int, set[int]]` | `similitud.Perfiles` | Intersección de sets en O(min(\|A\|, \|B\|)); pertenencia en O(1) |
| Índice invertido | `dict[int, set[int]]` (ítem → usuarios) | `RecomendadorOptimizado.item_a_usuarios` | Obtiene solo los **candidatos** (usuarios que comparten algún ítem) sin recorrer a todos |
| Versiones de perfil | `dict[int, int]` + contador global | `RecomendadorOptimizado.version`, `_version_global` | Invalidar cachés en O(1), sin recorrerlos |
| Memo de similitud | `dict[(menor, mayor), (v_menor, v_mayor, sim)]` | `_cache_similitud` | La similitud es simétrica: una sola entrada por par |
| Caché de recomendaciones | `dict[(uid, top_n, k), (v_global, lista)]` | `_cache_recs` | Consultas repetidas en O(1) |
| Lote de E/S | `list[str]` / `list[tuple[int, int]]` | `archivos.py` | Memoria O(tamaño de lote), no O(archivo) |

## Algoritmos importantes

### Recomendación (versión optimizada)

```text
recomendar(u, top_n, k):
    si (u, top_n, k) está en caché con la versión global actual -> devolver copia
    candidatos = ⋃ item_a_usuarios[i] para i en perfil(u), sin u      # O(m · grado)
    pares      = [(c, similitud_memoizada(u, c)) para c en candidatos] # O(c · m)
    vecinos    = heapq.nlargest(k, pares, clave=(sim, -id))            # O(c log k)
    resultado  = top_items(vecinos, perfil(u), top_n)                  # O(i log n)
    guardar en caché con la versión global
```

Con *n* usuarios, *m* ítems por usuario, *c* candidatos (c ≤ n), *i* ítems de los vecinos:

| Paso | Baseline | Optimizado |
|---|---|---|
| Elegir con quién comparar | todos: O(n) | candidatos por índice: O(c), c ≪ n en datos dispersos |
| Similitudes | O(n · m) | O(c · m), y O(1) si están memoizadas |
| Elegir k vecinos | `sort` completo: O(n log n) | heap: O(c log k) |
| Top-N ítems | `heapq.nlargest`: O(i log N) | igual (función compartida) |
| Consulta repetida | recalcula todo | O(1) desde el caché |

### Desempate determinista

Ambas implementaciones ordenan vecinos por **(similitud desc., id asc.)** con la misma función
`clave_vecino`, y los ítems por **(puntaje desc., id asc.)** en `top_items`. Por eso dan
resultados **idénticos**, lo que permite usar la baseline como oráculo en los tests.

### Invalidación de cachés por versiones

Cada `actualizar_usuario` incrementa la versión del usuario y la **versión global**:

- Una entrada del memo de similitud es válida solo si las versiones de **ambos** usuarios
  coinciden con las guardadas.
- Una recomendación cacheada es válida solo si la versión global no cambió, porque cualquier
  cambio (del usuario **o de un vecino**) puede alterarla.

No hace falta recorrer ni vaciar los cachés: las entradas viejas se detectan al leerlas.

### Procesamiento paralelo de archivos por rangos de bytes

1. Se divide el archivo en *p* rangos `[inicio, fin)` de igual tamaño (`dividir_en_rangos`).
2. Cada worker retrocede un byte desde `inicio` y descarta hasta el fin de esa línea: así cada
   línea la procesa **exactamente un** worker (el que contiene su primer byte).
3. Los perfiles parciales se combinan con unión de sets (`combinar_perfiles`).

Está probado con 1 a 1000 particiones sobre el mismo archivo.

## Decisiones de implementación

| Decisión | Alternativas consideradas | Motivo |
|---|---|---|
| Similitud de Jaccard sobre sets | Coseno, Pearson | El feedback es implícito (gustó / no): Jaccard es natural y barato |
| Calcular `\|A ∪ B\|` como `\|A\| + \|B\| − \|A ∩ B\|` | Construir el set unión | Evita crear un set por comparación |
| `heapq.nlargest` en vez de `sort` | Ordenar todo | k ≪ c: O(c log k) |
| Caché con versión global | Invalidar solo al usuario cambiado | Era un bug: el cambio de un vecino dejaba recomendaciones viejas |
| `multiprocessing` en vez de hilos | `threading` | Trabajo de CPU en Python puro: el GIL anula a los hilos |
| Un recomendador por worker (`initializer`) | Enviar los perfiles con cada tarea | El índice se construye una vez por proceso |
| Lectura en streaming con generadores | `readlines()` | Memoria constante independientemente del tamaño del archivo |
| Inyección del motor en `crear_app()` | Variable global | Cada test usa una instancia limpia |
| Python puro en el motor | NumPy / SciPy sparse | Requisito didáctico: medir el efecto de estructuras y algoritmos |
| Directorio de datos permitido en la API | Aceptar cualquier ruta | Corrige un *path traversal* (ver [Seguridad](seguridad.md)) |
