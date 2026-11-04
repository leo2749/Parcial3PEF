# 9. Mantenimiento

## Cómo contribuir

1. Crear una rama desde `main`: `git switch -c feature/descripcion-corta`.
2. Hacer el cambio **con sus pruebas** (y su benchmark, si afecta rendimiento).
3. Correr los controles en local: `python ci.py` (o al menos `python ci.py estatico pruebas`).
4. Si el cambio afecta comportamiento, API, decisiones de diseño o resultados, **actualizar la
   documentación en `docs/` en el mismo PR**.
5. Abrir un pull request hacia `main`. El CI corre solo; el merge queda bloqueado hasta que el
   job **7 · Resultado final** esté en verde y otro integrante apruebe la revisión.

### Convenciones

- PEP 8 con líneas de hasta 100 caracteres (Ruff y pylint lo verifican).
- Type hints en todas las firmas (mypy en modo estricto).
- Docstrings estilo Google (`Args`, `Returns`, `Raises`, `Example`): alimentan la
  [referencia del código](referencia.md).
- Mensajes de commit en imperativo y en español: "Agregar caché de similitud".

### Configuración del repositorio en GitHub (una vez)

| Dónde | Qué |
|---|---|
| Settings → Branches → *Branch protection rule* para `main` | Requerir PR, 1 aprobación y el status check **"7 · Resultado final"**; bloquear *force push* |
| Settings → Pages | Source: **GitHub Actions** (publica esta documentación) |
| Settings → Code security | Activar Dependabot alerts y security updates; CodeQL (si el repo es público) |
| Settings → Collaborators | Agregar a los integrantes con rol *Write*; el docente con *Read* |

## Ejecutar los controles

```bash
python ci.py                 # todo (igual que el CI)
python ci.py estatico        # Ruff, mypy, pylint, Radon/Xenon, Lizard
python ci.py seguridad       # Bandit, gitleaks
python ci.py pruebas         # pytest + cobertura
python ci.py dependencias    # pip check, pip-audit
python ci.py docs            # MkDocs, markdownlint, lychee
python ci.py rendimiento     # benchmark, profiling, memoria
python ci.py --estricto      # además falla si falta gitleaks, lychee o npx
```

Los reportes quedan en `reportes/` y el resumen en `reportes/resumen.md`.

## Resolver fallos del pipeline

Primero abrir el job en rojo en la pestaña *Actions*: el resumen muestra qué control falló.
Los reportes completos están en *Artifacts* (`reportes-<etapa>`). Después reproducir en local
con `python ci.py <etapa>`.

| Job / control | Causa típica | Solución |
|---|---|---|
| 2 · Preparación: `requirements*.txt desactualizados` | Se editó `requirements/*.in` sin regenerar | `python ci.py lock` y commitear los `.txt` |
| 2 · Preparación: `pip check` | Conflicto de versiones | Ajustar rangos en `requirements/*.in` y `python ci.py lock` |
| `ruff` | Error de estilo o bug potencial | `python -m ruff check . --fix` resuelve la mayoría |
| `mypy` | Tipos inconsistentes o firma sin anotar | Anotar o corregir; no usar `# type: ignore` sin código de error |
| `pylint` | Puntaje < 9,5 | Ver `reportes/pylint.txt` |
| `xenon` / `lizard` | Función con complejidad > B (CC > 10), > 50 NLOC o > 6 parámetros | Extraer funciones auxiliares |
| `bandit` | Patrón inseguro de severidad alta | Corregir; si es falso positivo, ver [excepciones](seguridad.md#falsos-positivos-y-excepciones) |
| `gitleaks` | Secreto en algún commit | **Rotar el secreto** primero; después limpiar el historial (`git filter-repo`) |
| `pytest` | Prueba fallida o cobertura < 90 % | `python -m pytest -x -v`; agregar pruebas para el código nuevo |
| `pip-audit` | Vulnerabilidad nueva en una dependencia | Subir la versión en `requirements/*.in` y `python ci.py lock`; o aceptar el PR de Dependabot |
| `mkdocs` (`--strict`) | Enlace roto entre páginas o página fuera del `nav` | Ver el *warning* en `reportes/mkdocs.txt` |
| `markdownlint` | Estilo de Markdown | `npx markdownlint-cli2@0.23.3 --fix` |
| `lychee` | Enlace externo caído | Corregirlo o, si es temporal, excluirlo en `lychee.toml` |
| `benchmark-regresion` | Regresión > 50 % o speedup < 3x | Ver `reportes/benchmark_comparacion.md` y el perfil `reportes/perfil_cpu.txt`; si es ruido, re-ejecutar el job |
| `memoria` | Pico por encima del límite | Ver `reportes/memoria.md`; revisar estructuras que crecen |

### Actualizar líneas base

Cuando un cambio **intencional** modifica el rendimiento o la memoria (por ejemplo, una
optimización), regenerar las líneas base y explicarlo en el PR:

```bash
python -m pytest benchmarks --benchmark-only --benchmark-json=reportes/benchmark.json
python scripts/comparar_benchmark.py --actualizar
python scripts/medir_memoria.py --actualizar
```

!!! tip "Línea base desde el CI"
    Para que la línea base refleje el hardware del CI, descargar el artefacto
    `reportes-rendimiento` de una corrida en `main` y ejecutar
    `python scripts/comparar_benchmark.py --resultado <ruta>/benchmark.json --actualizar`.

## Actualizar dependencias

```bash
# 1. Editar el rango en requirements/base.in o requirements/dev.in
# 2. Regenerar los lock files (usa uv, ya incluido en requirements-dev.txt)
python ci.py lock
# 3. Instalar y verificar
python -m pip install -r requirements-dev.txt
python ci.py dependencias pruebas
```

Dependabot abre PRs semanales; se integran cuando el CI pasa.
