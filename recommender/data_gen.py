"""
Generación de datos sintéticos para el motor de recomendaciones.
"""
import random
from collections.abc import Iterator

from .archivos import Evento
from .similitud import Perfiles


def generar_dataset(n_usuarios: int, n_items: int, items_por_usuario: int,
                    seed: int = 42) -> Perfiles:
    """Genera perfiles aleatorios reproducibles.

    Args:
        n_usuarios: Cantidad de usuarios (ids ``0 .. n_usuarios - 1``).
        n_items: Cantidad de ítems distintos (ids ``0 .. n_items - 1``).
        items_por_usuario: Ítems por usuario (se recorta a ``n_items``).
        seed: Semilla, para que los benchmarks sean comparables.

    Returns:
        Diccionario ``{usuario_id: set(items)}``.
    """
    # Datos sintéticos, no criptográficos: falso positivo documentado (FP-01).
    rnd = random.Random(seed)  # noqa: S311  # nosec B311
    cantidad = min(items_por_usuario, n_items)
    return {uid: set(rnd.sample(range(n_items), cantidad)) for uid in range(n_usuarios)}


def generar_eventos(n_eventos: int, n_usuarios: int, n_items: int,
                    seed: int = 42) -> Iterator[Evento]:
    """Generador perezoso de eventos ``(usuario_id, item_id)`` aleatorios.

    Al ser un generador no ocupa memoria proporcional a ``n_eventos``, lo
    que permite crear archivos de historial de cualquier tamaño.

    Args:
        n_eventos: Cantidad de eventos a producir.
        n_usuarios: Rango de ids de usuario.
        n_items: Rango de ids de ítem.
        seed: Semilla del generador aleatorio.

    Yields:
        Tuplas ``(usuario_id, item_id)``.
    """
    rnd = random.Random(seed)  # noqa: S311  # nosec B311 - ver FP-01
    for _ in range(n_eventos):
        yield rnd.randrange(n_usuarios), rnd.randrange(n_items)
