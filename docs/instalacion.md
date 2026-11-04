# 3. Instalación y ejecución

## Requisitos previos

| Herramienta | Versión | Para qué | Obligatoria |
|---|---|---|---|
| Python | 3.11 a 3.13 | Todo el proyecto | Sí |
| Git | cualquiera reciente | Clonar y contribuir | Sí |
| Node.js (incluye `npx`) | 18 o superior | `markdownlint-cli2` (lint de la documentación) | Solo para el control de docs |
| gitleaks | 8.30.1 | Detección de secretos | Solo para el control de secretos |
| lychee | 0.24.2 | Validación de enlaces | Solo para el control de enlaces |

Si falta una herramienta opcional, `python ci.py` marca ese control como **OMITIDO** y sigue; el
CI siempre las instala y corre en modo `--estricto`.

## Instalación

=== "Windows (PowerShell)"

    ```powershell
    git clone https://github.com/<usuario>/<repositorio>.git
    cd <repositorio>
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements-dev.txt
    ```

=== "Linux / macOS"

    ```bash
    git clone https://github.com/<usuario>/<repositorio>.git
    cd <repositorio>
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements-dev.txt
    ```

- `requirements.txt` tiene solo lo necesario para **ejecutar** la API (FastAPI, Uvicorn y sus
  dependencias). El motor en sí usa solo la librería estándar.
- `requirements-dev.txt` agrega las herramientas de pruebas, calidad, seguridad, profiling y
  documentación. **Todas las versiones están fijadas** (incluidas las transitivas), así que la
  instalación es reproducible: local y CI usan exactamente los mismos paquetes.

### Herramientas externas (opcionales en local)

| Herramienta | Windows | Linux / macOS |
|---|---|---|
| gitleaks | `winget install Gitleaks.Gitleaks` o `choco install gitleaks` | `brew install gitleaks` o binario de las *releases* |
| lychee | `scoop install lychee` o binario de las *releases* | `brew install lychee` o binario de las *releases* |
| markdownlint-cli2 | lo descarga `npx` automáticamente | ídem |

## Configuración

| Variable / archivo | Valor por defecto | Efecto |
|---|---|---|
| `MOTOR_DIR_DATOS` | `./datos` | Único directorio desde el que `POST /historial/archivo` puede leer CSV. Ver [Seguridad](seguridad.md#r1-lectura-de-archivos-arbitrarios-desde-la-api). |
| `pyproject.toml` | — | Configuración de pytest, coverage, Ruff, mypy, pylint y Bandit |
| `benchmarks/linea_base.json` | — | Línea base de rendimiento contra la que compara el CI |
| `benchmarks/limites_memoria.json` | — | Límites de memoria que controla el CI |
| `seguridad/pip-audit-ignore.txt` | vacío | Excepciones documentadas de vulnerabilidades |

## Ejecución

```bash
python cli.py                       # menú interactivo
python demo.py                      # recorrido guionado de las funcionalidades
uvicorn api:app --reload            # API REST -> http://127.0.0.1:8000/docs
python benchmark.py                 # comparación baseline / optimizado / caché / concurrencia
python benchmark_archivos.py        # archivos grandes (2 M eventos; acepta otra cantidad)
python -m mkdocs serve              # esta documentación -> http://127.0.0.1:8000
```

Para que la API cargue un archivo, copiarlo a `datos/` y enviar la ruta **relativa**:

```bash
curl -X POST http://127.0.0.1:8000/historial/archivo \
     -H "Content-Type: application/json" \
     -d '{"ruta": "historial.csv", "paralelo": true}'
```

## Controles de calidad

```bash
python ci.py                        # todas las etapas, igual que el CI
python ci.py estatico pruebas       # solo algunas
python ci.py --listar               # ver cada comando
```

El detalle de cada control está en la [Matriz de controles](calidad/controles.md).
