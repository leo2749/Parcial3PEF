"""
Corre todas las herramientas de análisis de calidad y guarda los reportes.

Herramientas:
    * pylint  -> errores, malas prácticas, nombres, docstrings (puntaje /10)
    * flake8  -> cumplimiento de PEP 8
    * radon   -> complejidad ciclomática (cc) e índice de mantenibilidad (mi)
    * pytest-cov -> cobertura de tests (también en XML para SonarQube)

Los archivos ``coverage.xml`` y ``pylint_sonar.txt`` los importa SonarQube
(ver ``sonar-project.properties``).

Ejecutar desde la raíz del proyecto:  python calidad/analizar.py
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "calidad"
CODIGO = ["recommender", "api.py", "cli.py", "demo.py", "benchmark.py", "benchmark_archivos.py"]
# En los tests, el nombre de la función ya documenta qué se prueba y
# pytest inyecta fixtures con el mismo nombre que la función que las define.
PYLINT_TESTS = ["--disable=missing-function-docstring,redefined-outer-name,protected-access"]

COMANDOS = {
    "pylint.txt": ["-m", "pylint", *CODIGO],
    "pylint_sonar.txt": ["-m", "pylint", "--output-format=parseable", *CODIGO],
    "pylint_tests.txt": ["-m", "pylint", "tests", *PYLINT_TESTS],
    "flake8.txt": ["-m", "flake8", "."],
    "radon_cc.txt": ["-m", "radon", "cc", "-s", "-a", *CODIGO],
    "radon_mi.txt": ["-m", "radon", "mi", "-s", *CODIGO],
    "cobertura.txt": ["-m", "pytest", "--cov", "--cov-report=term-missing",
                      "--cov-report=xml:calidad/coverage.xml"],
}


def main() -> None:
    """Ejecuta cada herramienta, guarda su salida y muestra un resumen."""
    for archivo, argumentos in COMANDOS.items():
        # Argumentos fijos definidos en este archivo, sin entrada externa.
        proceso = subprocess.run([sys.executable, *argumentos],  # noqa: S603  # nosec B603
                                 cwd=RAIZ, capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", check=False)
        salida = proceso.stdout + proceso.stderr
        (SALIDA / archivo).write_text(salida, encoding="utf-8")
        lineas = [linea for linea in salida.splitlines() if linea.strip()]
        ultima = lineas[-1] if lineas else "(sin salida)"
        print(f"{archivo:18s} -> {ultima.strip()}")
    corregir_coverage_para_sonar(SALIDA / "coverage.xml")


def corregir_coverage_para_sonar(ruta: Path) -> None:
    """Reemplaza la carpeta raíz vacía (``<source></source>``) por ``.``.

    Con ``relative_files`` coverage escribe la raíz como una ruta vacía, y
    SonarQube no encuentra los archivos que están ahí (``api.py``).
    """
    if ruta.exists():
        contenido = ruta.read_text(encoding="utf-8")
        ruta.write_text(contenido.replace("<source></source>", "<source>.</source>"),
                        encoding="utf-8")


if __name__ == "__main__":
    main()
