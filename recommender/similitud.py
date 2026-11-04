"""
Funciones de puntuación compartidas por todas las implementaciones.

Antes del refactor, ``naive.py`` y ``optimizado.py`` tenían cada uno su
propio bucle de "sumar la similitud de cada vecino a los ítems que el
usuario no tiene" y su propio criterio de orden. Al centralizarlo acá:

* se elimina código duplicado (una sola fuente de verdad),
* ambas versiones desempatan igual, así que dan **exactamente** el mismo
  resultado y se puede verificar con tests (``tests/test_recomendadores.py``).
"""
import heapq
from collections.abc import Iterable

Perfiles = dict[int, set[int]]


def puntaje_similitud(items_a: set[int], items_b: set[int]) -> float:
    """Calcula la similitud de Jaccard entre dos conjuntos de ítems.

    ``Jaccard = |A ∩ B| / |A ∪ B|``, un valor entre 0 (nada en común) y 1
    (idénticos).

    Args:
        items_a: Ítems que le gustan al primer usuario.
        items_b: Ítems que le gustan al segundo usuario.

    Returns:
        La similitud en el rango ``[0.0, 1.0]``. Si alguno de los conjuntos
        está vacío devuelve ``0.0``.

    Example:
        >>> puntaje_similitud({1, 2, 3}, {2, 3, 4})
        0.5
    """
    if not items_a or not items_b:
        return 0.0
    interseccion = len(items_a & items_b)
    if interseccion == 0:
        return 0.0
    # |A ∪ B| = |A| + |B| - |A ∩ B|: evita construir el set unión.
    return interseccion / (len(items_a) + len(items_b) - interseccion)


def clave_vecino(similitud: float, usuario_id: int) -> tuple[float, int]:
    """Clave de orden de vecinos: mayor similitud primero, menor id si empatan.

    Args:
        similitud: Similitud del vecino con el usuario objetivo.
        usuario_id: Id del vecino.

    Returns:
        Una tupla que, ordenada de forma **descendente**, respeta ese criterio.
    """
    return similitud, -usuario_id


def top_items(vecinos: Iterable[tuple[int, float]], objetivo: set[int],
              perfiles: Perfiles, top_n: int) -> list[int]:
    """Acumula la similitud de los vecinos por ítem y devuelve los Top N.

    Args:
        vecinos: Pares ``(vecino_id, similitud)`` ya ordenados del más al
            menos parecido. Los de similitud ``<= 0`` se ignoran.
        objetivo: Ítems que el usuario ya tiene (no se le recomiendan).
        perfiles: Diccionario ``{usuario_id: set(items)}``.
        top_n: Cantidad máxima de ítems a devolver.

    Returns:
        Ids de ítems ordenados por puntaje descendente (desempate: menor id).
        Usa ``heapq.nlargest``: O(i log n) en vez de ordenar todo, O(i log i).
    """
    puntajes: dict[int, float] = {}
    for vecino_id, similitud in vecinos:
        if similitud <= 0:
            continue
        for item in perfiles[vecino_id]:
            if item not in objetivo:
                puntajes[item] = puntajes.get(item, 0.0) + similitud
    mejores = heapq.nlargest(top_n, puntajes.items(),
                             key=lambda par: (par[1], -par[0]))
    return [item for item, _ in mejores]
