"""
Implementación BASELINE (línea base) del motor de recomendaciones.

Compara al usuario objetivo contra **todos** los usuarios del sistema y
ordena la lista completa: O(n · m + n log n) por consulta. Se mantiene
deliberadamente simple para medir contra ella las optimizaciones de
``optimizado.py``.
"""

from .similitud import Perfiles, puntaje_similitud, top_items


class RecomendadorNaive:
    """Recomendador por filtrado colaborativo usuario-usuario, sin índices.

    Args:
        usuarios: Diccionario ``{usuario_id: set(items)}``.
    """

    def __init__(self, usuarios: Perfiles):
        self.usuarios = usuarios

    def recomendar(self, usuario_id: int, top_n: int = 10, k_vecinos: int = 20) -> list[int]:
        """Devuelve los ``top_n`` ítems recomendados para ``usuario_id``.

        Args:
            usuario_id: Usuario al que se le recomienda.
            top_n: Cantidad de ítems a devolver.
            k_vecinos: Cantidad de usuarios similares que se consideran.

        Returns:
            Lista de ids de ítems, del más al menos recomendado.

        Raises:
            KeyError: Si el usuario no está registrado.
        """
        objetivo = self.usuarios[usuario_id]

        # Tuplas (similitud, -id): ordenadas de mayor a menor siguen el mismo
        # criterio que similitud.clave_vecino (empate -> menor id primero).
        similitudes: list[tuple[float, int]] = [
            (puntaje_similitud(objetivo, otro_items), -otro_id)
            for otro_id, otro_items in self.usuarios.items()
            if otro_id != usuario_id
        ]
        similitudes.sort(reverse=True)

        vecinos = [(-menos_id, sim) for sim, menos_id in similitudes[:k_vecinos]]
        return top_items(vecinos, objetivo, self.usuarios, top_n)
