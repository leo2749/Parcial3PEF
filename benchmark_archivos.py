"""
Benchmark de escritura y lectura de archivos grandes de historial.

Compara: ingenuo vs. batching + buffer vs. procesamiento en paralelo.
Mide tiempo (``time.perf_counter``) y, por separado, el pico de memoria
(``tracemalloc``) de las lecturas.

Ejecutar:  python benchmark_archivos.py [cantidad_de_eventos]
"""
import os
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable, Iterator

from recommender.archivos import (
    Evento,
    escribir_historial,
    escribir_historial_ingenuo,
    leer_historial_ingenuo,
    leer_historial_por_lotes,
    procesar_archivo_paralelo,
    procesar_archivo_por_lotes,
)
from recommender.data_gen import generar_eventos

N_EVENTOS_DEFECTO = 2_000_000
N_USUARIOS = 50_000
N_ITEMS = 5_000


def medir(funcion: Callable[[], object]) -> tuple[object, float]:
    """Ejecuta ``funcion`` y devuelve ``(resultado, segundos)``."""
    inicio = time.perf_counter()
    resultado = funcion()
    return resultado, time.perf_counter() - inicio


def pico_memoria(funcion: Callable[[], object]) -> float:
    """Pico de memoria (MiB) de ``funcion`` en este proceso, con tracemalloc.

    Se corre aparte de :func:`medir` porque tracemalloc agrega mucho
    overhead y distorsionaría los tiempos.
    """
    tracemalloc.start()
    funcion()
    pico = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return pico / 2**20


def medir_estrategias(ruta: str, ruta_ingenua: str, n_eventos: int) -> dict[str, float]:
    """Corre todas las estrategias y devuelve sus tiempos y picos de memoria."""
    def eventos() -> Iterator[Evento]:
        return generar_eventos(n_eventos, N_USUARIOS, N_ITEMS)

    res = {}
    _, res["t_esc_ing"] = medir(lambda: escribir_historial_ingenuo(ruta_ingenua, eventos()))
    _, res["t_esc_lot"] = medir(lambda: escribir_historial(ruta, eventos()))
    ingenuo, res["t_lec_ing"] = medir(lambda: leer_historial_ingenuo(ruta))
    por_lotes, res["t_lec_lot"] = medir(lambda: procesar_archivo_por_lotes(ruta))
    paralelo, res["t_lec_par"] = medir(lambda: procesar_archivo_paralelo(ruta))
    res["iguales"] = ingenuo == por_lotes == paralelo
    del ingenuo, por_lotes, paralelo  # liberar antes de medir memoria

    res["m_lec_ing"] = pico_memoria(lambda: leer_historial_ingenuo(ruta))
    res["m_lec_lot"] = pico_memoria(lambda: procesar_archivo_por_lotes(ruta))
    res["m_lotes"] = pico_memoria(lambda: sum(len(lote) for lote in leer_historial_por_lotes(ruta)))
    return res


def imprimir_resultados(res: dict[str, float]) -> None:
    """Imprime la tabla comparativa y los speedups."""
    print(f"Mismos perfiles en las 3 lecturas: {res['iguales']}\n")
    print(f"{'Estrategia':52s} {'Tiempo (s)':>10s} {'Pico mem (MiB)':>15s}")
    filas = [
        ("Escritura ingenua (línea a línea, flush)", res["t_esc_ing"], None),
        ("Escritura por lotes + buffer 1 MiB", res["t_esc_lot"], None),
        ("Lectura ingenua (readlines, todo a memoria)", res["t_lec_ing"], res["m_lec_ing"]),
        ("Lectura por lotes (generador, streaming)", res["t_lec_lot"], res["m_lec_lot"]),
        (f"Lectura en paralelo ({os.cpu_count()} procesos)", res["t_lec_par"], None),
        ("Solo recorrer los lotes (sin armar perfiles)", None, res["m_lotes"]),
    ]
    for nombre, segundos, pico in filas:
        tiempo = f"{segundos:10.3f}" if segundos is not None else f"{'-':>10s}"
        memoria = f"{pico:15.1f}" if pico is not None else f"{'-':>15s}"
        print(f"{nombre:52s} {tiempo} {memoria}")
    print(f"\nSpeedup escritura por lotes vs. ingenua: {res['t_esc_ing'] / res['t_esc_lot']:.1f}x")
    print(f"Speedup lectura en paralelo vs. por lotes: {res['t_lec_lot'] / res['t_lec_par']:.1f}x")


def main() -> None:
    """Genera los archivos en una carpeta temporal, mide e imprime."""
    n_eventos = int(sys.argv[1]) if len(sys.argv) > 1 else N_EVENTOS_DEFECTO
    print(f"Eventos: {n_eventos:,} · usuarios: {N_USUARIOS:,} · ítems: {N_ITEMS:,} · "
          f"núcleos: {os.cpu_count()}\n")
    with tempfile.TemporaryDirectory(prefix="historial_") as carpeta:
        ruta = os.path.join(carpeta, "lotes.csv")
        resultados = medir_estrategias(ruta, os.path.join(carpeta, "ingenuo.csv"), n_eventos)
        print(f"Tamaño del archivo: {os.path.getsize(ruta) / 2**20:.1f} MiB")
    imprimir_resultados(resultados)


if __name__ == "__main__":
    main()
