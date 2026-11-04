"""
Benchmarks de operaciones representativas (pytest-benchmark).

Se ejecutan aparte de los tests funcionales:

    python -m pytest benchmarks --benchmark-only --benchmark-json=reportes/benchmark.json
    python scripts/comparar_benchmark.py

``test_calibracion`` mide una carga fija de Python puro. El comparador divide
cada tiempo por el de la calibración, así el resultado depende poco de la
velocidad de la máquina y se puede comparar contra la línea base guardada en
``benchmarks/linea_base.json`` aunque el CI corra en otro hardware.
"""
import pytest

from recommender.archivos import escribir_historial, procesar_archivo_por_lotes
from recommender.data_gen import generar_dataset, generar_eventos
from recommender.historial import procesar_historial
from recommender.naive import RecomendadorNaive
from recommender.optimizado import RecomendadorOptimizado
from recommender.similitud import Perfiles, puntaje_similitud

N_USUARIOS = 10_000
N_ITEMS = 5_000
ITEMS_POR_USUARIO = 15
N_CONSULTAS = 20
N_EVENTOS = 100_000


@pytest.fixture(scope="module")
def usuarios() -> Perfiles:
    """Dataset sintético reproducible (semilla fija)."""
    return generar_dataset(N_USUARIOS, N_ITEMS, ITEMS_POR_USUARIO, seed=42)


@pytest.fixture(scope="module")
def eventos() -> list[tuple[int, int]]:
    """Historial sintético en memoria."""
    return list(generar_eventos(N_EVENTOS, N_USUARIOS, N_ITEMS, seed=42))


@pytest.fixture(scope="module")
def archivo_historial(tmp_path_factory: pytest.TempPathFactory,
                      eventos: list[tuple[int, int]]) -> str:
    """CSV de historial escrito una vez para los benchmarks de lectura."""
    ruta = tmp_path_factory.mktemp("bench") / "historial.csv"
    escribir_historial(str(ruta), eventos)
    return str(ruta)


def _carga_calibracion() -> int:
    total = 0
    for i in range(200_000):
        total += (i * i) % 7
    return total


def test_calibracion(benchmark) -> None:
    """Carga fija de referencia para normalizar el resto de las mediciones."""
    assert benchmark(_carga_calibracion) > 0


def test_recomendar_baseline(benchmark, usuarios: Perfiles) -> None:
    motor = RecomendadorNaive(usuarios)
    resultado = benchmark(lambda: [motor.recomendar(uid) for uid in range(N_CONSULTAS)])
    assert len(resultado) == N_CONSULTAS


def test_construir_indice_invertido(benchmark, usuarios: Perfiles) -> None:
    motor = benchmark(RecomendadorOptimizado, usuarios)
    assert len(motor.usuarios) == N_USUARIOS


def test_recomendar_optimizado_sin_cache(benchmark, usuarios: Perfiles) -> None:
    """Mismas consultas que el baseline, con un motor nuevo por ronda (caché vacío).

    La construcción del índice va en ``setup``, que pytest-benchmark no
    cronometra; su costo se mide en ``test_construir_indice_invertido``.
    """
    def preparar() -> tuple[tuple[RecomendadorOptimizado], dict[str, object]]:
        return (RecomendadorOptimizado(usuarios),), {}

    def consultar(motor: RecomendadorOptimizado) -> list[list[int]]:
        return [motor.recomendar(uid) for uid in range(N_CONSULTAS)]

    resultado = benchmark.pedantic(consultar, setup=preparar, rounds=15)
    naive = RecomendadorNaive(usuarios)
    assert resultado == [naive.recomendar(uid) for uid in range(N_CONSULTAS)]


def test_recomendar_optimizado_con_cache(benchmark, usuarios: Perfiles) -> None:
    """Consultas repetidas: se resuelven desde el caché (50 pasadas por ronda)."""
    motor = RecomendadorOptimizado(usuarios)
    esperados = [motor.recomendar(uid) for uid in range(N_CONSULTAS)]

    def consultar() -> list[list[int]]:
        for _ in range(49):
            for uid in range(N_CONSULTAS):
                motor.recomendar(uid)
        return [motor.recomendar(uid) for uid in range(N_CONSULTAS)]

    assert benchmark(consultar) == esperados


def test_puntaje_similitud(benchmark, usuarios: Perfiles) -> None:
    pares = [(usuarios[i], usuarios[i + 1]) for i in range(2_000)]
    resultado = benchmark(lambda: [puntaje_similitud(a, b) for a, b in pares])
    assert all(0.0 <= valor <= 1.0 for valor in resultado)


def test_procesar_historial_en_memoria(benchmark, eventos: list[tuple[int, int]]) -> None:
    perfiles = benchmark(procesar_historial, eventos)
    assert len(perfiles) <= N_USUARIOS


def test_leer_archivo_por_lotes(benchmark, archivo_historial: str) -> None:
    perfiles = benchmark(procesar_archivo_por_lotes, archivo_historial)
    assert len(perfiles) <= N_USUARIOS
