"""
Cálculo de recomendaciones en batch: secuencial vs. concurrente.

La versión concurrente usa ``multiprocessing.Pool`` con un inicializador
que construye **un** recomendador por proceso (el índice se arma una vez
por worker, no una vez por tarea).
"""
import multiprocessing as mp

from .optimizado import RecomendadorOptimizado
from .similitud import Perfiles

Recomendaciones = dict[int, list[int]]

# Estado propio de cada proceso worker (no es una constante).
_recomendador_worker: RecomendadorOptimizado | None = None  # pylint: disable=invalid-name


def _inicializar_worker(usuarios: Perfiles) -> None:
    # Estado por proceso: es la forma estándar de pasar datos a un Pool sin re-enviarlos.
    global _recomendador_worker  # pylint: disable=global-statement  # noqa: PLW0603
    _recomendador_worker = RecomendadorOptimizado(usuarios)


def _tarea(args: tuple[int, int, int]) -> tuple[int, list[int]]:
    usuario_id, top_n, k_vecinos = args
    if _recomendador_worker is None:  # pragma: no cover - solo si se usa sin el Pool
        raise RuntimeError("El worker no fue inicializado con _inicializar_worker")
    return usuario_id, _recomendador_worker.recomendar(usuario_id, top_n, k_vecinos)


def recomendar_batch_concurrente(usuarios: Perfiles, ids_a_procesar: list[int],
                                 top_n: int = 10, k_vecinos: int = 20,
                                 n_workers: int = 4) -> Recomendaciones:
    """Calcula recomendaciones para muchos usuarios repartidas en procesos.

    Args:
        usuarios: Perfiles ``{usuario_id: set(items)}``.
        ids_a_procesar: Usuarios para los que se pide recomendación.
        top_n: Ítems por usuario.
        k_vecinos: Vecinos considerados.
        n_workers: Cantidad de procesos.

    Returns:
        ``{usuario_id: recomendaciones}``.
    """
    tareas = [(uid, top_n, k_vecinos) for uid in ids_a_procesar]
    chunksize = max(1, len(tareas) // (n_workers * 4))
    with mp.Pool(processes=n_workers, initializer=_inicializar_worker,
                 initargs=(usuarios,)) as pool:
        return dict(pool.map(_tarea, tareas, chunksize=chunksize))


def recomendar_batch_secuencial(recomendador: RecomendadorOptimizado, ids_a_procesar: list[int],
                                top_n: int = 10, k_vecinos: int = 20) -> Recomendaciones:
    """Versión secuencial de :func:`recomendar_batch_concurrente`, para comparar.

    Args:
        recomendador: Motor ya construido.
        ids_a_procesar: Usuarios para los que se pide recomendación.
        top_n: Ítems por usuario.
        k_vecinos: Vecinos considerados.

    Returns:
        ``{usuario_id: recomendaciones}``.
    """
    return {uid: recomendador.recomendar(uid, top_n, k_vecinos) for uid in ids_a_procesar}
