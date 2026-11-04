"""
Registro de usuarios y procesamiento de historiales de interacción.

Convierte datos "crudos" (eventos individuales, uno por cada clic, compra
o reproducción) en la estructura que usa el resto del motor:
``{usuario_id: set(items)}``. Se hace con un único recorrido de los eventos
y un diccionario de sets, evitando buscar linealmente en una lista si el
usuario ya existe.
"""
from collections.abc import Iterable

from .archivos import Evento, procesar_archivo_paralelo, procesar_archivo_por_lotes
from .optimizado import RecomendadorOptimizado
from .similitud import Perfiles


def registrar_usuario(recomendador: RecomendadorOptimizado, usuario_id: int,
                      items: set[int]) -> None:
    """Da de alta un usuario o reemplaza sus preferencias si ya existía.

    Es un alias semántico de :meth:`RecomendadorOptimizado.actualizar_usuario`
    (misma lógica de índice e invalidación; cambia el motivo: alta vs.
    cambio de gustos).

    Args:
        recomendador: Motor donde se registra el usuario.
        usuario_id: Id del usuario.
        items: Ítems que le gustan. Se copian.
    """
    recomendador.actualizar_usuario(usuario_id, set(items))


def procesar_historial(eventos: Iterable[Evento]) -> Perfiles:
    """Agrupa un historial de interacciones por usuario.

    Complejidad O(E), con E = cantidad de eventos: un único recorrido con
    inserciones O(1) promedio en sets.

    Args:
        eventos: Tuplas ``(usuario_id, item_id)``; puede haber repetidos.

    Returns:
        Diccionario ``{usuario_id: set(items)}``.

    Example:
        >>> procesar_historial([(1, 10), (1, 11), (2, 10), (1, 10)])
        {1: {10, 11}, 2: {10}}
    """
    preferencias: Perfiles = {}
    for usuario_id, item_id in eventos:
        preferencias.setdefault(usuario_id, set()).add(item_id)
    return preferencias


def aplicar_preferencias(recomendador: RecomendadorOptimizado, preferencias: Perfiles) -> None:
    """Suma preferencias nuevas a las que cada usuario ya tenía.

    Un historial es acumulativo: los ítems se **unen** a los previos, no
    los reemplazan.

    Args:
        recomendador: Motor a actualizar.
        preferencias: ``{usuario_id: set(items)}`` a incorporar.
    """
    for usuario_id, items_nuevos in preferencias.items():
        items_previos = recomendador.usuarios.get(usuario_id, set())
        registrar_usuario(recomendador, usuario_id, items_previos | items_nuevos)


def cargar_usuarios_desde_historial(recomendador: RecomendadorOptimizado,
                                    eventos: Iterable[Evento]) -> None:
    """Procesa un historial en memoria y registra o actualiza a sus usuarios.

    Args:
        recomendador: Motor a actualizar.
        eventos: Tuplas ``(usuario_id, item_id)``.
    """
    aplicar_preferencias(recomendador, procesar_historial(eventos))


def cargar_usuarios_desde_archivo(recomendador: RecomendadorOptimizado, ruta: str,
                                  paralelo: bool = False) -> int:
    """Lee un historial CSV (ver :mod:`recommender.archivos`) y lo incorpora.

    Args:
        recomendador: Motor a actualizar.
        ruta: Archivo ``usuario_id,item_id``.
        paralelo: Si es ``True`` usa varios procesos; si no, streaming por lotes.

    Returns:
        Cantidad de usuarios afectados.
    """
    procesar = procesar_archivo_paralelo if paralelo else procesar_archivo_por_lotes
    preferencias = procesar(ruta)
    aplicar_preferencias(recomendador, preferencias)
    return len(preferencias)
