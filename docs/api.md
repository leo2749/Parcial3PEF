# 5. API y contratos

Hay dos contratos: la **API REST** (`api.py`) y la **API de Python** del paquete
`recommender`. La [referencia del código](referencia.md) se genera automáticamente desde los
docstrings, así que no se desactualiza.

## API REST

Iniciar con `uvicorn api:app --reload`. La documentación interactiva (OpenAPI/Swagger) queda en
`http://127.0.0.1:8000/docs`. Todas las entradas y salidas son JSON.

| Método y ruta | Entrada | Salida (200/201) | Errores |
|---|---|---|---|
| `GET /usuarios` | — | `{"<id>": [items...]}` | — |
| `PUT /usuarios` | `{"usuario_id": int, "items": [int, ...]}` (≥ 1 ítem) | 201 · `{"usuario_id", "items"}` | 422 entrada inválida |
| `POST /historial` | `[{"usuario_id": int, "item_id": int}, ...]` | `{"usuarios_afectados": [ids]}` | 422 |
| `POST /historial/archivo` | `{"ruta": str, "paralelo": bool = false}` | `{"usuarios_afectados": int, "total_usuarios": int}` | 403 ruta fuera de `MOTOR_DIR_DATOS` · 404 no existe · 422 |
| `GET /similitud/{a}/{b}` | ids en la ruta | `{"similitud": float}` en [0, 1] | 404 usuario no registrado |
| `GET /recomendaciones/{id}` | `top_n` (1–100, def. 10), `k_vecinos` (1–500, def. 20) | `{"usuario_id", "top_n", "items": [ids]}` | 404 · 422 parámetros fuera de rango |

### Semántica

- `PUT /usuarios` **reemplaza** las preferencias del usuario.
- `POST /historial` y `POST /historial/archivo` **suman** los ítems a los que el usuario ya tenía.
- Las líneas inválidas de un CSV se descartan sin abortar la carga.
- Cualquier modificación invalida los cachés; la siguiente consulta recalcula.

### Ejemplos

```bash
curl -X PUT http://127.0.0.1:8000/usuarios -H "Content-Type: application/json" \
     -d '{"usuario_id": 1, "items": [10, 11]}'
# 201 {"usuario_id":1,"items":[10,11]}

curl -X POST http://127.0.0.1:8000/historial -H "Content-Type: application/json" \
     -d '[{"usuario_id": 2, "item_id": 10}, {"usuario_id": 2, "item_id": 12}]'
# 200 {"usuarios_afectados":[2]}

curl http://127.0.0.1:8000/similitud/1/2
# 200 {"similitud":0.3333333333333333}

curl "http://127.0.0.1:8000/recomendaciones/1?top_n=5"
# 200 {"usuario_id":1,"top_n":5,"items":[12]}

curl "http://127.0.0.1:8000/recomendaciones/999"
# 404 {"detail":"Usuario 999 no registrado"}

curl -X POST http://127.0.0.1:8000/historial/archivo -H "Content-Type: application/json" \
     -d '{"ruta": "../../etc/passwd"}'
# 403 {"detail":"Ruta no permitida"}
```

## API de Python

```python
from recommender.optimizado import RecomendadorOptimizado
from recommender.historial import registrar_usuario, cargar_usuarios_desde_archivo

motor = RecomendadorOptimizado(usuarios={})
registrar_usuario(motor, 1, {10, 11, 12})
registrar_usuario(motor, 2, {11, 12, 13})
motor.similitud(1, 2)                 # 0.5
motor.recomendar(1, top_n=5)          # [13]
cargar_usuarios_desde_archivo(motor, "datos/historial.csv", paralelo=True)
```

### Contratos principales

| Función / método | Entradas | Salida | Excepciones |
|---|---|---|---|
| `RecomendadorOptimizado(usuarios)` | `dict[int, set[int]]` (se usa sin copiar) | instancia | — |
| `.actualizar_usuario(uid, items)` | id, set completo de ítems | `None` | — |
| `.similitud(a, b)` | ids registrados | `float` en [0, 1] | `KeyError` si alguno no existe |
| `.recomendar(uid, top_n=10, k_vecinos=20)` | id registrado | `list[int]`, del más al menos recomendado; vacía si no hay vecinos | `KeyError` si no existe |
| `RecomendadorNaive(usuarios).recomendar(...)` | ídem | **idéntica** a la optimizada | `KeyError` |
| `historial.procesar_historial(eventos)` | iterable de `(uid, item)` | `dict[int, set[int]]` | — |
| `historial.cargar_usuarios_desde_archivo(motor, ruta, paralelo=False)` | ruta CSV | cantidad de usuarios afectados | `FileNotFoundError` |
| `archivos.escribir_historial(ruta, eventos, tam_lote, tam_buffer)` | iterable (puede ser un generador) | cantidad escrita | `OSError` |
| `archivos.leer_historial_por_lotes(ruta, tam_lote)` | ruta CSV | generador de `list[(uid, item)]` | `FileNotFoundError` |
| `concurrente.recomendar_batch_concurrente(usuarios, ids, top_n, k, n_workers)` | perfiles e ids | `dict[uid, list[int]]` | `KeyError` en el worker |
| `api.resolver_ruta_segura(ruta, directorio)` | ruta del cliente | `Path` absoluta | `PermissionError` si sale del directorio |

### Formato de archivo de historial

CSV UTF-8, encabezado opcional `usuario_id,item_id`, una interacción por línea:

```text
usuario_id,item_id
1,10
1,11
2,10
```
