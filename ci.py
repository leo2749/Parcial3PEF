"""
Orquestador de los controles de calidad y eficiencia.

Es la **única fuente de verdad** de los comandos: GitHub Actions
(``.github/workflows/ci.yml``) llama a este mismo script, así que correrlo en
local reproduce exactamente lo que hace el CI.

Uso:
    python ci.py                      # todas las etapas
    python ci.py estatico pruebas     # solo algunas etapas
    python ci.py --listar             # ver etapas y controles
    python ci.py --estricto           # falla si falta una herramienta externa
    python ci.py lock                 # regenerar requirements*.txt (requiere uv)

Cada control guarda su salida en ``reportes/<control>.txt`` (además de los
reportes JSON/SARIF/XML propios de cada herramienta). Al final se escribe
``reportes/resumen.md`` y, dentro de GitHub Actions, el resumen del job.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REPORTES = RAIZ / "reportes"
PY = sys.executable

CODIGO = ["recommender", "api.py", "cli.py", "demo.py", "benchmark.py",
          "benchmark_archivos.py", "perfilar.py"]
HERRAMIENTAS = ["ci.py", "scripts"]

# Versiones fijas de las herramientas que no son paquetes de Python.
MARKDOWNLINT = "markdownlint-cli2@0.23.3"


@dataclass
class Control:
    """Un comando del pipeline.

    Attributes:
        nombre: Identificador corto; también nombra el reporte ``.txt``.
        comando: Argumentos del proceso (sin shell).
        externo: Ejecutable que no se instala con pip; si falta se omite
            (o falla, con ``--estricto``).
        bloqueante: Si es ``False`` el fallo se informa pero no rechaza.
    """

    nombre: str
    comando: list[str]
    externo: str | None = None
    bloqueante: bool = True


def _ignorados_pip_audit() -> list[str]:
    """Lee las excepciones documentadas de ``seguridad/pip-audit-ignore.txt``."""
    ruta = RAIZ / "seguridad" / "pip-audit-ignore.txt"
    argumentos: list[str] = []
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            identificador = linea.split("#", 1)[0].strip()
            if identificador:
                argumentos += ["--ignore-vuln", identificador]
    return argumentos


def _gitleaks() -> list[str]:
    """Con historial git se escanean todos los commits; si no, los archivos."""
    modo = ["git", "."] if (RAIZ / ".git").exists() else ["dir", "."]
    return ["gitleaks", *modo, "--config", ".gitleaks.toml", "--redact", "--no-banner",
            "--report-format", "sarif", "--report-path", "reportes/gitleaks.sarif"]


def _npx() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def definir_etapas() -> dict[str, list[Control]]:
    """Etapas en el orden del pipeline: primero lo rápido, al final lo costoso."""
    ignorados = _ignorados_pip_audit()
    pip_audit = [PY, "-m", "pip_audit", "-r", "requirements-dev.txt", "--no-deps",
                 "--disable-pip", "--progress-spinner", "off", *ignorados]
    return {
        "estatico": [
            Control("ruff", [PY, "-m", "ruff", "check", ".", "--output-format", "concise"]),
            Control("mypy", [PY, "-m", "mypy", "--junit-xml", "reportes/mypy.xml"]),
            Control("pylint", [PY, "-m", "pylint", *CODIGO, *HERRAMIENTAS,
                               "--fail-under=9.5"]),
            Control("radon", [PY, "-m", "radon", "cc", "-s", "-a", *CODIGO],
                    bloqueante=False),
            Control("xenon", [PY, "-m", "xenon", "--max-absolute", "B", "--max-modules", "A",
                              "--max-average", "A", *CODIGO]),
            # CCN <= 10, <= 50 líneas de código (NLOC), <= 100 líneas totales, <= 6 parámetros.
            Control("lizard", [PY, "-m", "lizard", *CODIGO, "-C", "10", "-L", "100",
                               "-T", "nloc=50", "-a", "6", "-w"]),
        ],
        "seguridad": [
            Control("bandit-reporte", [PY, "-m", "bandit", "-c", "pyproject.toml", "-r",
                                       *CODIGO, "-f", "json", "-o", "reportes/bandit.json",
                                       "--exit-zero", "-q"]),
            Control("bandit-sarif", [PY, "-m", "bandit", "-c", "pyproject.toml", "-r", *CODIGO,
                                     "-f", "sarif", "-o", "reportes/bandit.sarif",
                                     "--exit-zero", "-q"]),
            Control("bandit", [PY, "-m", "bandit", "-c", "pyproject.toml", "-r", *CODIGO,
                               "--severity-level", "high", "--confidence-level", "medium"]),
            Control("gitleaks", _gitleaks(), externo="gitleaks"),
        ],
        "pruebas": [
            Control("pytest", [PY, "-m", "pytest", "-p", "no:cacheprovider", "--cov",
                               "--cov-report=term-missing",
                               "--cov-report=xml:reportes/coverage.xml",
                               "--cov-report=html:reportes/cobertura_html",
                               "--cov-fail-under=90", "--junitxml=reportes/pytest.xml"]),
        ],
        "dependencias": [
            Control("pip-check", [PY, "-m", "pip", "check"]),
            Control("pip-audit-reporte", [*pip_audit, "-f", "json", "-o",
                                          "reportes/pip-audit.json"], bloqueante=False),
            Control("pip-audit", [*pip_audit, "--desc", "on"]),
        ],
        "docs": [
            Control("mkdocs", [PY, "-m", "mkdocs", "build", "--strict", "-d", "site"]),
            Control("markdownlint", [_npx(), "--yes", MARKDOWNLINT], externo=_npx()),
            Control("lychee", ["lychee", "--config", "lychee.toml", "--format", "markdown",
                               "--output", "reportes/lychee.md", "README.md", "docs/**/*.md"],
                    externo="lychee"),
        ],
        "rendimiento": [
            Control("benchmark", [PY, "-m", "pytest", "benchmarks", "-p", "no:cacheprovider",
                                  "--benchmark-only", "--benchmark-columns",
                                  "min,median,max,stddev,rounds",
                                  "--benchmark-json=reportes/benchmark.json"]),
            Control("benchmark-regresion", [PY, "scripts/comparar_benchmark.py"]),
            Control("profiling-cprofile", [PY, "scripts/perfilar_cpu.py"]),
            Control("profiling-pyinstrument", [PY, "-m", "pyinstrument", "-r", "html", "-o",
                                               "reportes/pyinstrument.html", "perfilar.py"]),
            Control("memoria", [PY, "scripts/medir_memoria.py"]),
        ],
    }


def ejecutar(control: Control, estricto: bool) -> tuple[str, float]:
    """Corre un control mostrando su salida y guardándola en ``reportes/``.

    Returns:
        ``(estado, segundos)`` con estado ``OK``, ``FALLA``, ``AVISO`` u ``OMITIDO``.
    """
    print(f"\n{'=' * 78}\n▶ {control.nombre}: {' '.join(control.comando)}\n{'=' * 78}",
          flush=True)
    if control.externo and shutil.which(control.externo) is None:
        print(f"  '{control.externo}' no está instalado (ver docs/mantenimiento.md).")
        return ("FALLA" if estricto else "OMITIDO"), 0.0

    entorno = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    inicio = time.perf_counter()
    with (REPORTES / f"{control.nombre}.txt").open("w", encoding="utf-8") as reporte, \
            subprocess.Popen(control.comando, cwd=RAIZ, env=entorno, text=True,  # noqa: S603
                             encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT) as proceso:  # nosec B603
        for linea in proceso.stdout or ():
            print(linea, end="")
            reporte.write(linea)
    segundos = time.perf_counter() - inicio
    if proceso.returncode == 0:
        return "OK", segundos
    return ("FALLA" if control.bloqueante else "AVISO"), segundos


def escribir_resumen(resultados: list[tuple[str, str, str, float]]) -> str:
    """Arma la tabla Markdown de resultados y la guarda en ``reportes/resumen.md``."""
    iconos = {"OK": "✅", "FALLA": "❌", "AVISO": "⚠️", "OMITIDO": "⏭️"}
    lineas = ["| Etapa | Control | Resultado | Tiempo |", "|---|---|---|---:|"]
    lineas += [f"| {etapa} | {nombre} | {iconos[estado]} {estado} | {segundos:.1f} s |"
               for etapa, nombre, estado, segundos in resultados]
    rechazado = any(estado == "FALLA" for *_, estado, _ in resultados)
    lineas += ["", f"**Resultado final: {'RECHAZADO ❌' if rechazado else 'APROBADO ✅'}**", ""]
    texto = "\n".join(lineas)
    (REPORTES / "resumen.md").write_text(texto, encoding="utf-8")
    resumen_github = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen_github:
        with open(resumen_github, "a", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
    return texto


def regenerar_lock() -> int:
    """Recompila ``requirements.txt`` y ``requirements-dev.txt`` con versiones exactas."""
    base = [PY, "-m", "uv", "pip", "compile", "--universal", "--python-version", "3.11", "-q"]
    for entrada, salida in (("requirements/base.in", "requirements.txt"),
                            ("requirements/dev.in", "requirements-dev.txt")):
        codigo = subprocess.call([*base, entrada, "-o", salida], cwd=RAIZ)  # noqa: S603  # nosec
        if codigo != 0:
            print("Falló uv. ¿Está instalado? -> python -m pip install uv")
            return codigo
    return 0


def main() -> int:
    """Punto de entrada; devuelve el código de salida del pipeline."""
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    etapas = definir_etapas()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("etapas", nargs="*", metavar="ETAPA",
                        help=f"etapas a correr (por defecto, todas): {', '.join(etapas)} o lock")
    parser.add_argument("--estricto", action="store_true",
                        help="falla si falta una herramienta externa (gitleaks, lychee, npx)")
    parser.add_argument("--listar", action="store_true", help="muestra los controles y sale")
    args = parser.parse_args()

    desconocidas = set(args.etapas) - {*etapas, "lock"}
    if desconocidas:
        parser.error(f"etapas desconocidas: {sorted(desconocidas)}")
    if "lock" in args.etapas:
        return regenerar_lock()
    if args.listar:
        for etapa, controles in etapas.items():
            print(etapa)
            for control in controles:
                print(f"  - {control.nombre}: {' '.join(control.comando)}")
        return 0

    REPORTES.mkdir(exist_ok=True)
    resultados = [(etapa, control.nombre, *ejecutar(control, args.estricto))
                  for etapa in (args.etapas or list(etapas))
                  for control in etapas[etapa]]
    print(f"\n{'=' * 78}\n{escribir_resumen(resultados)}")
    return 1 if any(estado == "FALLA" for *_, estado, _ in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
