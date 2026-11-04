# 8. Seguridad

## Controles

| Requisito | Herramienta | Qué analiza | Reportes |
|---|---|---|---|
| Analizar el código fuente | **Bandit** | Patrones inseguros en Python (subprocess, random, eval, asserts…) | `bandit.txt`, `bandit.json`, `bandit.sarif` |
| | **Ruff** (reglas `S`) | Las mismas reglas de Bandit, en el editor y en cada commit | `ruff.txt` |
| | **CodeQL** (`security-extended`) | Análisis semántico de flujo de datos (inyecciones, *path traversal*) | pestaña *Security* de GitHub |
| Analizar las dependencias | **pip-audit** | Todas las versiones fijadas contra la base de PyPI/OSV | `pip-audit.txt`, `pip-audit.json` |
| | **Dependabot** | Alertas y PRs de actualización semanales | PRs y pestaña *Security* |
| Detectar secretos | **gitleaks** | Tokens, claves y contraseñas en **todo el historial** de git | `gitleaks.txt`, `gitleaks.sarif` |

Los reportes `.txt` son legibles; los `.json` y `.sarif` son para máquinas. Los SARIF se suben a
la pestaña *Security → Code scanning* de GitHub cuando el repositorio lo permite (público o con
GitHub Advanced Security). Todos quedan en los artefactos del CI.

## Política de bloqueo por severidad

| Fuente | Bloquea el merge | Se revisa antes de integrar | Informativo |
|---|---|---|---|
| Bandit | Severidad **alta** con confianza **media o alta** | Severidad media | Severidad baja |
| CodeQL | — (el job no es requerido) | Alertas *high* y *critical* | *medium* y menores |
| pip-audit | **Cualquier** vulnerabilidad conocida no exceptuada | — | — |
| Dependabot | — | Alertas *high* y *critical*: actualizar en ≤ 7 días | resto |
| gitleaks | **Cualquier** hallazgo | — | — |

Justificación:

- **pip-audit bloquea todo** porque las dependencias están fijadas y casi siempre existe una
  versión corregida; actualizar es barato. Si no hay corrección, se documenta una excepción.
- **Bandit bloquea solo lo alto**: sus reglas de severidad baja tienen muchos falsos positivos
  (por ejemplo, `random` en datos sintéticos).
- **Un secreto filtrado siempre es crítico**: aunque se borre, sigue en el historial de git.
  Hay que rotarlo, no solo eliminarlo.

## Riesgos identificados

### R1. Lectura de archivos arbitrarios desde la API

| | |
|---|---|
| Tipo | CWE-22 · *Path traversal* |
| Severidad | **Alta** |
| Detectado por | Revisión manual de la API (Bandit no lo detecta; es el tipo de flujo que analiza CodeQL) |
| Estado | **Corregido** |

`POST /historial/archivo` recibía una ruta y la abría directamente: cualquier cliente podía leer
(o intentar parsear) cualquier archivo del servidor, por ejemplo `../../etc/passwd`, y
confirmar si existía por la diferencia entre 404 y 200.

**Medida correctiva**: `api.resolver_ruta_segura()` resuelve la ruta (incluidos `..` y enlaces
simbólicos) y exige que quede dentro de `MOTOR_DIR_DATOS` (por defecto `./datos`). Si no, la API
responde **403**. Cubierto por `test_cargar_archivo_rechaza_path_traversal` y
`test_cargar_archivo_rechaza_ruta_absoluta_externa`.

### R2. API sin autenticación

| | |
|---|---|
| Severidad | Media |
| Estado | **Aceptado** (fuera de alcance) |

Cualquiera que llegue al puerto puede modificar perfiles. Mitigación: Uvicorn escucha en
`127.0.0.1` por defecto; no exponer la API sin un gateway con autenticación.

### R3. Denegación de servicio por cargas grandes

| | |
|---|---|
| Severidad | Media |
| Estado | **Mitigado parcialmente** |

`top_n` (≤ 100) y `k_vecinos` (≤ 500) están acotados por validación. `POST /historial` no
limita la cantidad de eventos: debe limitarse el tamaño del cuerpo en el proxy inverso.

### R4. Dependencias vulnerables

| | |
|---|---|
| Estado | **Controlado**: 0 vulnerabilidades conocidas a la fecha (pip-audit) |

Versiones fijadas + `pip-audit` en cada push + Dependabot semanal.

## Falsos positivos y excepciones

| Id | Herramienta / regla | Ubicación | Decisión | Justificación |
|---|---|---|---|---|
| FP-01 | Bandit B311 / Ruff S311 (`random` no criptográfico) | `recommender/data_gen.py` | `# nosec B311` + `# noqa: S311` | Genera datos sintéticos reproducibles para tests y benchmarks; necesita semilla fija, que es justamente lo que un generador criptográfico no permite |
| FP-02 | Bandit B603 / Ruff S603 (`subprocess` sin shell) | `ci.py`, `calidad/analizar.py` | `# nosec B603` + `# noqa: S603` | Los argumentos son listas fijas definidas en el propio archivo; no hay entrada externa ni `shell=True` |
| EX-01 | gitleaks (rutas) | `.venv/`, `site/`, `reportes/`, `perfiles/`, `docs/_build/` | Excluidas en `.gitleaks.toml` | Son archivos generados o de terceros, no versionados (salvo `perfiles/`, que solo tiene salidas de profilers) |

Reglas para agregar una excepción:

1. Confirmar que es un falso positivo (o un riesgo aceptado) y explicarlo en el PR.
2. Suprimir **la línea concreta** con el código de regla (`# nosec BXXX`, `# noqa: SXXX`), nunca
   un archivo o una regla completa.
3. Para pip-audit, agregar el ID en `seguridad/pip-audit-ignore.txt` con justificación y fecha.
4. Registrar la excepción en esta tabla. Se revisan en cada actualización de dependencias.

## Medidas correctivas aplicadas en este trabajo

| Hallazgo | Medida |
|---|---|
| R1 *path traversal* | Directorio de datos permitido + 403 + tests |
| mypy: `_tarea` usaba un global que podía ser `None` | Verificación explícita con error claro (`concurrente.py`) |
| mypy: `split` mezclaba `str` y `bytes` | Separación por tipo en `_parsear_linea` |
| Dependencias con rangos (`>=`) | Lock files con versiones exactas, auditados en cada push |
