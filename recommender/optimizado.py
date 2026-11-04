"""
Implementación OPTIMIZADA del motor de recomendaciones.

Mejoras respecto al baseline (``recommender/naive.py``):

1. **Estructura de datos - diccionario invertido** (HashMap ítem -> set de
   usuarios): en vez de recorrer a todos los usuarios, se obtienen
   directamente los "candidatos" (usuarios que comparten al menos un ítem
   con el objetivo).

2. **Algoritmo - Top-K con heap** (``heapq.nlargest``): O(c log k) en lugar
   de ordenar toda la lista, O(c log c).

3. **Memoización** de la similitud entre pares de usuarios. Cada entrada
   guarda la *versión* del perfil de ambos usuarios con la que se calculó;
   si alguno cambió, la entrada se descarta y se recalcula.

4. **Caching con invalidación** de las recomendaciones finales. Cada
   entrada guarda la *versión global* del recomendador: cualquier cambio de
   preferencias (de este usuario **o de un vecino**) la deja obsoleta. La
   clave incluye ``top_n`` y ``k_vecinos``.

Corrección respecto al primer parcial: antes la memoización de similitud
nunca se invalidaba y el caché de recomendaciones solo miraba la versión
del propio usuario, por lo que si cambiaba un vecino se devolvían
resultados viejos; además la clave era solo el usuario, así que pedir el
Top 1 después del Top 5 devolvía los 5 ítems cacheados. Está cubierto por
``tests/test_recomendadores.py``.

Complejidad por consulta, con m = ítems del usuario, c = candidatos (c <= n):
    candidatos O(m) · similitudes O(c · m) · top-k O(c log k) · top-n O(i log n).
"""
import heapq

from .similitud import Perfiles, clave_vecino, puntaje_similitud, top_items


class RecomendadorOptimizado:
    """Recomendador con índice invertido, heap, memoización y caché.

    Args:
        usuarios: Diccionario ``{usuario_id: set(items)}``. Se usa (y se
            modifica) directamente, sin copiarlo.
    """

    def __init__(self, usuarios: Perfiles):
        self.usuarios = usuarios
        self.version: dict[int, int] = dict.fromkeys(usuarios, 0)
        self._version_global = 0

        self.item_a_usuarios: dict[int, set[int]] = {}
        for uid, items in usuarios.items():
            for item in items:
                self.item_a_usuarios.setdefault(item, set()).add(uid)

        # (uid_menor, uid_mayor) -> (versión_menor, versión_mayor, similitud)
        self._cache_similitud: dict[tuple[int, int], tuple[int, int, float]] = {}
        # (uid, top_n, k_vecinos) -> (versión_global, recomendaciones)
        self._cache_recs: dict[tuple[int, int, int], tuple[int, list[int]]] = {}

    def actualizar_usuario(self, usuario_id: int, nuevos_items: set[int]) -> None:
        """Registra un usuario o reemplaza sus preferencias.

        Mantiene el diccionario invertido actualizado de forma incremental
        (solo toca los ítems que cambiaron) e invalida los cachés subiendo
        las versiones, sin necesidad de recorrerlos.

        Args:
            usuario_id: Usuario a registrar o actualizar.
            nuevos_items: Conjunto completo de ítems que le gustan.
        """
        viejos = self.usuarios.get(usuario_id, set())
        for item in viejos - nuevos_items:
            self.item_a_usuarios[item].discard(usuario_id)
        for item in nuevos_items - viejos:
            self.item_a_usuarios.setdefault(item, set()).add(usuario_id)
        self.usuarios[usuario_id] = nuevos_items
        self.version[usuario_id] = self.version.get(usuario_id, 0) + 1
        self._version_global += 1

    def similitud(self, a_id: int, b_id: int) -> float:
        """Similitud de Jaccard entre dos usuarios registrados, memoizada.

        Args:
            a_id: Id del primer usuario.
            b_id: Id del segundo usuario.

        Returns:
            La similitud en ``[0.0, 1.0]``.
        """
        menor, mayor = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
        version_menor, version_mayor = self.version[menor], self.version[mayor]
        entrada = self._cache_similitud.get((menor, mayor))
        if entrada is not None and entrada[0] == version_menor and entrada[1] == version_mayor:
            return entrada[2]
        valor = puntaje_similitud(self.usuarios[menor], self.usuarios[mayor])
        self._cache_similitud[(menor, mayor)] = (version_menor, version_mayor, valor)
        return valor

    def _candidatos(self, usuario_id: int) -> set[int]:
        """Usuarios que comparten al menos un ítem con ``usuario_id``."""
        indice = self.item_a_usuarios
        candidatos = set().union(*(indice.get(item, ()) for item in self.usuarios[usuario_id]))
        candidatos.discard(usuario_id)
        return candidatos

    def recomendar(self, usuario_id: int, top_n: int = 10, k_vecinos: int = 20) -> list[int]:
        """Devuelve los ``top_n`` ítems recomendados para ``usuario_id``.

        Da el mismo resultado que :meth:`RecomendadorNaive.recomendar`.

        Args:
            usuario_id: Usuario al que se le recomienda.
            top_n: Cantidad de ítems a devolver.
            k_vecinos: Cantidad de usuarios similares que se consideran.

        Returns:
            Lista de ids de ítems, del más al menos recomendado.

        Raises:
            KeyError: Si el usuario no está registrado.
        """
        clave = (usuario_id, top_n, k_vecinos)
        entrada = self._cache_recs.get(clave)
        if entrada is not None and entrada[0] == self._version_global:
            return list(entrada[1])

        pares = [(otro_id, self.similitud(usuario_id, otro_id))
                 for otro_id in self._candidatos(usuario_id)]
        vecinos = heapq.nlargest(k_vecinos, pares, key=lambda par: clave_vecino(par[1], par[0]))
        resultado = top_items(vecinos, self.usuarios[usuario_id], self.usuarios, top_n)

        self._cache_recs[clave] = (self._version_global, resultado)
        return list(resultado)
