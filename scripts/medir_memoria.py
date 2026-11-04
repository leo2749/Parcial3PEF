"""
Mide el pico de memoria de operaciones representativas con ``tracemalloc``
y lo compara contra los límites de ``benchmarks/limites_memoria.json``.

tracemalloc cuenta las asignaciones que hace Python, no la memoria del
proceso (RSS): por eso es reproducible entre máquinas con la misma versión de
Python y sirve como control del CI. Cada medición se repite y se toma la
**máxima**, para no aprobar por azar.

Uso:
    python scripts/medir_memoria.py               # medir y controlar
    python scripts/medir_memoria.py --actualizar  # regrabar límites (medido x margen)

Sale con código 1 si algún pico supera su límite.
"""
import argparse
import gc
import json
import sys
import tempfile
import tracemalloc
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# pylint: disable=wrong-import-position
from recommender.archivos import (  # noqa: E402
    escribir_historial,
    leer_historial_por_lotes,
    procesar_archivo_por_lotes,
)
from recommender.data_gen import generar_dataset, generar_eventos  # noqa: E402
from recommender.optimizado import RecomendadorOptimizado  # noqa: E402

REPETICIONES = 3
MARGEN_LIMITE = 1.30  # el límite se fija 30 % por encima de lo medido
N_USUARIOS, N_ITEMS, ITEMS_POR_USUARIO = 15_000, 3_000, 15
N_EVENTOS = 300_000
TAM_LOTE = 50_000


def pico_mib(funcion: Callable[[], object]) -> float:
    """Pico de memoria (MiB) asignada por Python durante ``funcion``."""
    gc.collect()
    tracemalloc.start()
    try:
        funcion()
        return tracemalloc.get_traced_memory()[1] / 2**20
    finally:
        tracemalloc.stop()


def recorrer_lotes(ruta: str) -> int:
    """Solo recorre el archivo en streaming (memoria acotada por el lote)."""
    return sum(len(lote) for lote in leer_historial_por_lotes(ruta, TAM_LOTE))


def medir_todo(carpeta: Path) -> dict[str, float]:
    """Corre cada escenario ``REPETICIONES`` veces y devuelve el pico máximo."""
    usuarios = generar_dataset(N_USUARIOS, N_ITEMS, ITEMS_POR_USUARIO)
    ruta = str(carpeta / "historial.csv")
    escribir_historial(ruta, generar_eventos(N_EVENTOS, 50_000, 5_000))

    def recomendar_100() -> object:
        motor = RecomendadorOptimizado(usuarios)
        return [motor.recomendar(uid) for uid in range(100)]

    escenarios: dict[str, Callable[[], object]] = {
        "construir_indice_invertido": lambda: RecomendadorOptimizado(usuarios),
        "recomendar_100_consultas_con_cache": recomendar_100,
        "leer_archivo_streaming_lotes": lambda: recorrer_lotes(ruta),
        "procesar_archivo_por_lotes": lambda: procesar_archivo_por_lotes(ruta, TAM_LOTE),
    }
    return {nombre: max(pico_mib(funcion) for _ in range(REPETICIONES))
            for nombre, funcion in escenarios.items()}


def main() -> int:
    """Punto de entrada; devuelve el código de salida."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limites", type=Path,
                        default=RAIZ / "benchmarks" / "limites_memoria.json")
    parser.add_argument("--reporte", type=Path, default=RAIZ / "reportes" / "memoria")
    parser.add_argument("--actualizar", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="memoria_") as carpeta:
        picos = medir_todo(Path(carpeta))

    if args.actualizar:
        limites = {nombre: round(valor * MARGEN_LIMITE, 1) for nombre, valor in picos.items()}
        args.limites.write_text(json.dumps(
            {"descripcion": f"Pico de tracemalloc en MiB. Límite = medido x {MARGEN_LIMITE}. "
                            "Regenerar con: python scripts/medir_memoria.py --actualizar",
             "limites_mib": limites}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Límites actualizados en {args.limites}: {limites}")
        return 0

    limites = json.loads(args.limites.read_text(encoding="utf-8"))["limites_mib"]
    filas = [{"escenario": nombre, "pico_mib": round(pico, 2), "limite_mib": limites[nombre],
              "estado": "OK" if pico <= limites[nombre] else "EXCEDIDO"}
             for nombre, pico in picos.items()]
    lineas = ["# Consumo de memoria (tracemalloc, pico de " f"{REPETICIONES} repeticiones)", "",
              "| Escenario | Pico (MiB) | Límite (MiB) | Estado |", "|---|---:|---:|---|"]
    lineas += [f"| {f['escenario']} | {f['pico_mib']:.2f} | {f['limite_mib']:.1f} | "
               f"{f['estado']} |" for f in filas]
    args.reporte.parent.mkdir(parents=True, exist_ok=True)
    args.reporte.with_suffix(".md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    args.reporte.with_suffix(".json").write_text(json.dumps(filas, indent=2), encoding="utf-8")
    print("\n".join(lineas))

    excedidos = [f["escenario"] for f in filas if f["estado"] == "EXCEDIDO"]
    if excedidos:
        print(f"\nRECHAZADO: límite de memoria superado en {excedidos}", file=sys.stderr)
        return 1
    print("\nAPROBADO: todos los picos dentro del límite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
