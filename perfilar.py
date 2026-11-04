"""
Carga de trabajo para perfilar con herramientas externas.

Corre el baseline y la versión optimizada sobre el mismo dataset, sin
multiprocessing, para que el perfil quede limpio. Uso::

    py-spy record -o perfiles/py_spy.svg -- python perfilar.py
    pyinstrument -r html -o perfiles/pyinstrument.html perfilar.py
    python -m cProfile -o perfiles/perfilar.prof perfilar.py && snakeviz perfiles/perfilar.prof
"""
from recommender.data_gen import generar_dataset
from recommender.naive import RecomendadorNaive
from recommender.optimizado import RecomendadorOptimizado
from recommender.similitud import Perfiles

N_CONSULTAS = 80


def correr_baseline(usuarios: Perfiles) -> None:
    """Consultas con el recomendador baseline."""
    naive = RecomendadorNaive(usuarios)
    for uid in range(N_CONSULTAS):
        naive.recomendar(uid)


def correr_optimizado(usuarios: Perfiles) -> None:
    """Las mismas consultas con el recomendador optimizado (sin caché previo)."""
    optimizado = RecomendadorOptimizado(usuarios)
    for uid in range(N_CONSULTAS):
        optimizado.recomendar(uid)


def main() -> None:
    """Genera el dataset y corre ambas versiones."""
    usuarios = generar_dataset(15_000, 3_000, 15)
    correr_baseline(usuarios)
    correr_optimizado(usuarios)


if __name__ == "__main__":
    main()
