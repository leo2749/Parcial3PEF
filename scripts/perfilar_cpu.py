"""
Profiling de CPU para el CI: cProfile (determinístico) sobre la carga de
``perfilar.py`` y un resumen legible con las funciones más costosas.

Genera en ``reportes/``:
    * ``perfil_cpu.prof``  -> abrir con ``snakeviz reportes/perfil_cpu.prof``
    * ``perfil_cpu.txt``   -> top de funciones por tiempo acumulado y propio
    * ``perfil_cpu.json``  -> las mismas filas en formato de máquina

El profiling es **informativo**: el control falla solo si la carga no se
puede ejecutar. La herramienta de muestreo (pyinstrument) se corre aparte,
ver ``ci.py``.

Uso:  python scripts/perfilar_cpu.py
"""
import cProfile
import io
import json
import pstats
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import perfilar  # noqa: E402  # pylint: disable=wrong-import-position

TOP = 15


def main() -> int:
    """Perfila ``perfilar.main`` y escribe los reportes."""
    destino = RAIZ / "reportes"
    destino.mkdir(exist_ok=True)
    perfilador = cProfile.Profile()
    perfilador.runcall(perfilar.main)
    perfilador.dump_stats(destino / "perfil_cpu.prof")

    texto = io.StringIO()
    estadisticas = pstats.Stats(perfilador, stream=texto)
    estadisticas.sort_stats("cumulative").print_stats(TOP)
    estadisticas.sort_stats("tottime").print_stats(TOP)
    (destino / "perfil_cpu.txt").write_text(texto.getvalue(), encoding="utf-8")

    filas = []
    # `stats` existe en tiempo de ejecución pero no está en los stubs de typeshed.
    crudas = estadisticas.stats  # type: ignore[attr-defined]
    for (archivo, linea, funcion), datos in crudas.items():
        llamadas, _, propio, acumulado, _ = datos
        filas.append({"funcion": f"{Path(archivo).name}:{linea}({funcion})",
                      "llamadas": llamadas, "tiempo_propio_s": round(propio, 4),
                      "tiempo_acumulado_s": round(acumulado, 4)})
    filas.sort(key=lambda fila: fila["tiempo_propio_s"], reverse=True)
    (destino / "perfil_cpu.json").write_text(json.dumps(filas[:TOP], indent=2),
                                             encoding="utf-8")
    print(f"Top {TOP} por tiempo propio:")
    for fila in filas[:TOP]:
        print(f"  {fila['tiempo_propio_s']:8.3f} s  {fila['llamadas']:>9}  {fila['funcion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
