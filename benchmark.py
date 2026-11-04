"""
Benchmark + perfilado: baseline vs optimizado vs caching vs concurrencia.

Además de imprimir los resultados, guarda los perfiles de cProfile en
``perfiles/*.prof`` para abrirlos con SnakeViz::

    python benchmark.py
    snakeviz perfiles/baseline.prof
"""
import cProfile
import io
import os
import pstats
import time
from collections.abc import Callable
from typing import Any

from recommender.concurrente import recomendar_batch_concurrente, recomendar_batch_secuencial
from recommender.data_gen import generar_dataset
from recommender.naive import RecomendadorNaive
from recommender.optimizado import RecomendadorOptimizado

Recomendador = RecomendadorNaive | RecomendadorOptimizado

N_USUARIOS = 15_000
N_ITEMS = 3_000
ITEMS_POR_USUARIO = 15
N_CONSULTAS = 80
N_BATCH = 300
TOP_N = 10
K_VECINOS = 20
CARPETA_PERFILES = "perfiles"


def medir(funcion: Callable[..., object], *args: Any, **kwargs: Any) -> tuple[object, float]:
    """Ejecuta ``funcion`` y devuelve ``(resultado, segundos)``."""
    inicio = time.perf_counter()
    resultado = funcion(*args, **kwargs)
    return resultado, time.perf_counter() - inicio


def consultar(recomendador: Recomendador, ids: list[int]) -> list[list[int]]:
    """Pide recomendaciones para cada id (la carga de trabajo medida)."""
    return [recomendador.recomendar(uid, TOP_N, K_VECINOS) for uid in ids]


def perfilar(nombre: str, funcion: Callable[[], object], lineas: int = 6) -> None:
    """Perfila ``funcion`` con cProfile, imprime el top y guarda ``<nombre>.prof``."""
    perfilador = cProfile.Profile()
    perfilador.runcall(funcion)
    os.makedirs(CARPETA_PERFILES, exist_ok=True)
    perfilador.dump_stats(os.path.join(CARPETA_PERFILES, f"{nombre}.prof"))

    salida = io.StringIO()
    pstats.Stats(perfilador, stream=salida).sort_stats("cumulative").print_stats(lineas)
    print(f"--- Perfilado (cProfile) de {nombre.upper()}: top funciones por tiempo acumulado ---")
    print(salida.getvalue())


def main() -> None:
    """Corre todas las mediciones e imprime la tabla comparativa."""
    print(f"Dataset: {N_USUARIOS} usuarios, {N_ITEMS} items, "
          f"~{ITEMS_POR_USUARIO} items/usuario\n")
    usuarios = generar_dataset(N_USUARIOS, N_ITEMS, ITEMS_POR_USUARIO)
    ids_consulta = list(range(N_CONSULTAS))
    tabla: list[tuple[str, float]] = []

    naive = RecomendadorNaive(usuarios)
    recs_naive, t_naive = medir(consultar, naive, ids_consulta)
    tabla.append(("Implementación inicial (baseline)", t_naive))
    print(f"[Baseline]              {N_CONSULTAS} consultas -> {t_naive:.4f} s "
          f"({t_naive / N_CONSULTAS * 1000:.2f} ms/consulta)")

    opt = RecomendadorOptimizado(usuarios)
    recs_opt, t_opt = medir(consultar, opt, ids_consulta)
    tabla.append(("Estructura + algoritmo optimizado (1ra pasada, sin cache aún)", t_opt))
    print(f"[Optimizado 1ra pasada] {N_CONSULTAS} consultas -> {t_opt:.4f} s "
          f"({t_opt / N_CONSULTAS * 1000:.2f} ms/consulta)  "
          f"-> speedup vs baseline: {t_naive / t_opt:.1f}x")
    print(f"[Verificación]          resultados idénticos al baseline: {recs_naive == recs_opt}")

    _, t_cache = medir(consultar, opt, ids_consulta)
    tabla.append(("Con caching (2da consulta, mismos usuarios)", t_cache))
    print(f"[Con caching]           {N_CONSULTAS} consultas -> {t_cache:.4f} s "
          f"({t_cache / N_CONSULTAS * 1000:.2f} ms/consulta)  "
          f"-> speedup vs 1ra pasada: {t_opt / max(t_cache, 1e-9):.1f}x")

    opt.actualizar_usuario(0, usuarios[0] | {N_ITEMS + 1})
    _, t_invalidado = medir(opt.recomendar, 0, TOP_N, K_VECINOS)
    print(f"\n[Invalidación] Tras actualizar al usuario 0 se recalcula en "
          f"{t_invalidado * 1000:.2f} ms (no se devuelve la versión cacheada).")

    ids_batch = list(range(N_BATCH))
    _, t_seq = medir(recomendar_batch_secuencial, RecomendadorOptimizado(usuarios),
                     ids_batch, TOP_N, K_VECINOS)
    tabla.append((f"Batch secuencial ({N_BATCH} usuarios)", t_seq))
    print(f"\n[Batch secuencial]     {N_BATCH} usuarios -> {t_seq:.4f} s")

    n_workers = min(4, os.cpu_count() or 1)
    _, t_conc = medir(recomendar_batch_concurrente, usuarios, ids_batch,
                      TOP_N, K_VECINOS, n_workers)
    tabla.append((f"Batch concurrente, {n_workers} procesos ({N_BATCH} usuarios)", t_conc))
    print(f"[Batch concurrente]    {N_BATCH} usuarios, {n_workers} procesos -> {t_conc:.4f} s "
          f"-> speedup: {t_seq / t_conc:.1f}x  ({os.cpu_count()} núcleos lógicos)\n")

    perfilar("baseline", lambda: consultar(naive, ids_consulta))
    perfilar("optimizado", lambda: consultar(RecomendadorOptimizado(usuarios), ids_consulta))

    print("=== Tabla comparativa (tiempos totales) ===")
    for nombre, segundos in tabla:
        print(f"{nombre:60s} {segundos * 1000:10.2f} ms")


if __name__ == "__main__":
    main()
