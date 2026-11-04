# Matriz de controles

Cada control tiene una **herramienta**, un **comando reproducible**, un **reporte** y un
**criterio de aprobación o rechazo**. Todos los comandos están definidos en un solo lugar,
`ci.py`, que usan tanto el CI como los desarrolladores. Así lo que pasa en local pasa en el
CI, y al revés.

## Matriz

| Control | Qué verifica | Herramienta | Comando (dentro de `ci.py`) | Reporte en `reportes/` | Rechaza si… |
|---|---|---|---|---|---|
| Pruebas automatizadas | Correctitud y comportamiento esperado | pytest (+ doctests) | `pytest --cov ... --junitxml=reportes/pytest.xml` | `pytest.txt`, `pytest.xml` | ≥ 1 prueba falla |
| Cobertura | % de líneas ejecutadas por las pruebas | coverage.py vía pytest-cov | `--cov-fail-under=90` | `coverage.xml`, `cobertura_html/` | cobertura < 90 % |
| Análisis estático | Errores potenciales, estilo, imports, malas prácticas | Ruff (E, W, F, I, B, UP, SIM, C4, N, S, PL, RUF) | `ruff check .` | `ruff.txt` | cualquier hallazgo |
| | Mantenibilidad, diseño, docstrings | pylint | `pylint ... --fail-under=9.5` | `pylint.txt` | puntaje < 9,5 / 10 |
| Tipado estático | Inconsistencias en tipos y contratos | mypy `--strict` | `mypy` (configurado en `pyproject.toml`) | `mypy.txt`, `mypy.xml` | cualquier error |
| Complejidad | Complejidad ciclomática | Radon (reporte) + Xenon (umbral) | `xenon --max-absolute B --max-modules A --max-average A` | `radon.txt`, `xenon.txt` | una función > B (CC > 10), un módulo > A o promedio > A |
| | Tamaño de las funciones | Lizard | `lizard -C 10 -L 100 -T nloc=50 -a 6 -w` | `lizard.txt` | CC > 10, > 50 líneas de código, > 100 líneas totales o > 6 parámetros |
| Vulnerabilidades (código) | Patrones inseguros | Bandit (+ reglas `S` de Ruff, CodeQL) | `bandit --severity-level high --confidence-level medium` | `bandit.txt`, `.json`, `.sarif` | severidad alta con confianza ≥ media |
| Secretos | Credenciales en el código o el historial | gitleaks | `gitleaks git . --config .gitleaks.toml` | `gitleaks.txt`, `.sarif` | cualquier hallazgo |
| Vulnerabilidades (dependencias) | CVE/GHSA en las versiones fijadas | pip-audit | `pip-audit -r requirements-dev.txt --no-deps` | `pip-audit.txt`, `.json` | cualquier vulnerabilidad no exceptuada |
| Dependencias | Versiones reproducibles y consistentes | uv (lock) + pip check + Dependabot | `ci.py lock` + `git diff --exit-code`; `pip check` | log del job 2; `pip-check.txt` | lock desincronizado o conflicto |
| Documentación | El sitio se construye sin advertencias | MkDocs `--strict` | `mkdocs build --strict -d site` | `mkdocs.txt`, `site/` | cualquier advertencia (enlace interno roto, página huérfana) |
| | Estilo del Markdown | markdownlint-cli2 | `npx markdownlint-cli2@0.23.3` | `markdownlint.txt` | cualquier regla violada |
| | Enlaces externos válidos | lychee | `lychee --config lychee.toml README.md docs/**/*.md` | `lychee.md` | un enlace devuelve error |
| Benchmark | Tiempo de operaciones representativas | pytest-benchmark + `scripts/comparar_benchmark.py` | `pytest benchmarks --benchmark-only` | `benchmark.json`, `benchmark_comparacion.md` | regresión normalizada > 50 % o speedup < 3x |
| Profiling de CPU | Funciones que más tiempo consumen | cProfile + pyinstrument | `scripts/perfilar_cpu.py`; `pyinstrument -r html` | `perfil_cpu.txt`, `.json`, `.prof`, `pyinstrument.html` | no se puede generar (informativo) |
| Consumo de memoria | Pico de memoria de escenarios clave | tracemalloc (`scripts/medir_memoria.py`) | `python scripts/medir_memoria.py` | `memoria.md`, `memoria.json` | un pico supera su límite |

Además, fuera de `ci.py`: **CodeQL** (`.github/workflows/codeql.yml`, análisis semántico en
cada PR y semanal) y **Dependabot** (`.github/dependabot.yml`, PRs semanales).

## Por qué varias herramientas por control

No todas cumplen la misma función:

- **Ruff** es muy rápido y cubre estilo y bugs comunes; **pylint** agrega chequeos de diseño
  más profundos; **mypy** verifica contratos de tipos que ninguno de los dos ve.
- **Bandit** busca patrones inseguros en el código propio; **pip-audit** compara dependencias
  contra bases de vulnerabilidades conocidas; **gitleaks** busca secretos; **CodeQL** sigue el
  flujo de datos entre funciones (por ejemplo, de un parámetro HTTP a `open()`).
- **Radon/Xenon** miden la complejidad ciclomática; **Lizard** suma el tamaño y la cantidad de
  parámetros.

## Criterios distintos según el control

Las pruebas, el análisis estático y la seguridad son **deterministas**: el mismo código da el
mismo resultado, así que el umbral es estricto (cero errores). Los benchmarks y la memoria
dependen del entorno, así que usan:

- **Repetición**: pytest-benchmark corre varias rondas y se usa la **mediana**; la memoria toma
  el **máximo** de 3 repeticiones.
- **Normalización**: cada tiempo se divide por un benchmark de calibración medido en la misma
  corrida, para independizarse del hardware del runner.
- **Comparación con una línea base** versionada (`benchmarks/linea_base.json`,
  `benchmarks/limites_memoria.json`).
- **Tolerancia** explícita: 50 % en tiempo y 30 % de margen en memoria.

## Cómo ejecutar los controles en local

```bash
python -m venv .venv
.venv\Scripts\activate             # Windows  (Linux/macOS: source .venv/bin/activate)
python -m pip install -r requirements-dev.txt

python ci.py                       # todos los controles, en el mismo orden que el CI
python ci.py estatico seguridad    # solo algunas etapas
python ci.py --listar              # ver el comando exacto de cada control
python ci.py --estricto            # como el CI: falla si falta gitleaks, lychee o npx
```

Salida esperada al final:

```text
| Etapa | Control | Resultado | Tiempo |
|---|---|---|---:|
| estatico | ruff | ✅ OK | 0.1 s |
| estatico | mypy | ✅ OK | 0.7 s |
...
**Resultado final: APROBADO ✅**
```

Cada control también se puede correr suelto, sin `ci.py`:

```bash
python -m ruff check .
python -m mypy
python -m pytest --cov --cov-fail-under=90
python -m bandit -c pyproject.toml -r recommender api.py --severity-level high
python -m pip_audit -r requirements-dev.txt --no-deps --disable-pip
python -m mkdocs build --strict
python -m pytest benchmarks --benchmark-only --benchmark-json=reportes/benchmark.json
python scripts/comparar_benchmark.py
python scripts/medir_memoria.py
```

!!! note "Diferencias posibles entre local y CI"
    - Sin `gitleaks`, `lychee` o `npx` instalados, esos controles salen como **OMITIDO** en local
      (en el CI nunca, porque corre con `--estricto`).
    - Los tiempos absolutos de los benchmarks varían entre máquinas; el criterio usa valores
      normalizados justamente por eso.
    - Los límites de memoria se calibraron con Python 3.13; otra versión de Python puede
      asignar distinto.
