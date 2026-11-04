"""
Lectura y escritura de historiales de interacción en archivos grandes.

Formato: CSV de dos columnas ``usuario_id,item_id`` (una interacción por
línea, con encabezado opcional). Se ofrecen tres estrategias para comparar
en ``benchmark_archivos.py``:

* **Ingenua**: escribir línea por línea con flush inmediato y leer todo el
  archivo a memoria con ``readlines()``.
* **Batching + buffer**: escribir con ``writelines`` en lotes de N líneas
  sobre un buffer de E/S grande, y leer en *streaming* con un generador que
  entrega lotes, con memoria constante sin importar el tamaño del archivo.
* **Procesamiento en paralelo**: dividir el archivo en rangos de bytes,
  procesar cada rango en un proceso distinto (``multiprocessing.Pool``) y
  combinar los resultados parciales.
"""
import itertools
import multiprocessing as mp
import os
from collections.abc import Iterable, Iterator

from .similitud import Perfiles

Evento = tuple[int, int]

ENCABEZADO = "usuario_id,item_id\n"
TAM_LOTE_DEFECTO = 50_000
TAM_BUFFER_DEFECTO = 1 << 20  # 1 MiB


def _parsear_linea(linea: str | bytes) -> Evento | None:
    """Convierte ``"3,14"`` (str o bytes) en ``(3, 14)``.

    Returns:
        La tupla, o ``None`` si la línea es el encabezado, está vacía o es
        inválida (se descarta en lugar de abortar todo el procesamiento).
    """
    # Un split por tipo (mypy no admite mezclar str y bytes en una sola llamada).
    partes = linea.split(b",") if isinstance(linea, bytes) else linea.split(",")
    try:
        usuario, item = partes
        return int(usuario), int(item)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Escritura
# --------------------------------------------------------------------------
def escribir_historial_ingenuo(ruta: str, eventos: Iterable[Evento]) -> None:
    """Escribe un evento por vez con buffer de línea (flush en cada ``\\n``).

    Es la versión "línea base": cada línea termina en una llamada al sistema.

    Args:
        ruta: Archivo de destino (se sobrescribe).
        eventos: Pares ``(usuario_id, item_id)``.
    """
    with open(ruta, "w", encoding="utf-8", newline="", buffering=1) as archivo:
        archivo.write(ENCABEZADO)
        for usuario_id, item_id in eventos:
            archivo.write(f"{usuario_id},{item_id}\n")


def escribir_historial(ruta: str, eventos: Iterable[Evento],
                       tam_lote: int = TAM_LOTE_DEFECTO,
                       tam_buffer: int = TAM_BUFFER_DEFECTO) -> int:
    """Escribe eventos en lotes con un buffer de E/S grande.

    Acumula ``tam_lote`` líneas en una lista y las vuelca con un solo
    ``writelines``; el buffer evita una llamada al sistema por línea. Acepta
    cualquier iterable (incluso un generador infinito cortado), así que la
    memoria usada es O(tam_lote) y no O(cantidad de eventos).

    Args:
        ruta: Archivo de destino (se sobrescribe).
        eventos: Pares ``(usuario_id, item_id)``.
        tam_lote: Líneas por lote.
        tam_buffer: Tamaño del buffer de E/S en bytes.

    Returns:
        Cantidad de eventos escritos.
    """
    total = 0
    lote: list[str] = []
    with open(ruta, "w", encoding="utf-8", newline="", buffering=tam_buffer) as archivo:
        archivo.write(ENCABEZADO)
        for usuario_id, item_id in eventos:
            lote.append(f"{usuario_id},{item_id}\n")
            if len(lote) >= tam_lote:
                archivo.writelines(lote)
                total += len(lote)
                lote.clear()
        archivo.writelines(lote)
        total += len(lote)
    return total


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------
def leer_historial_ingenuo(ruta: str) -> Perfiles:
    """Carga el archivo entero a memoria con ``readlines()`` y lo procesa.

    Args:
        ruta: Archivo CSV de historial.

    Returns:
        Diccionario ``{usuario_id: set(items)}``.
    """
    with open(ruta, encoding="utf-8") as archivo:
        lineas = archivo.readlines()
    perfiles: Perfiles = {}
    for linea in lineas:
        evento = _parsear_linea(linea)
        if evento is not None:
            perfiles.setdefault(evento[0], set()).add(evento[1])
    return perfiles


def leer_historial_por_lotes(ruta: str, tam_lote: int = TAM_LOTE_DEFECTO,
                             tam_buffer: int = TAM_BUFFER_DEFECTO) -> Iterator[list[Evento]]:
    """Generador que lee el archivo en *streaming* y entrega lotes de eventos.

    Nunca tiene más de ``tam_lote`` eventos en memoria, así que sirve para
    archivos más grandes que la RAM disponible.

    Args:
        ruta: Archivo CSV de historial.
        tam_lote: Eventos por lote.
        tam_buffer: Tamaño del buffer de lectura en bytes.

    Yields:
        Listas de hasta ``tam_lote`` tuplas ``(usuario_id, item_id)``.
    """
    lote: list[Evento] = []
    with open(ruta, encoding="utf-8", buffering=tam_buffer) as archivo:
        for linea in archivo:
            evento = _parsear_linea(linea)
            if evento is None:
                continue
            lote.append(evento)
            if len(lote) >= tam_lote:
                yield lote
                lote = []
    if lote:
        yield lote


def procesar_archivo_por_lotes(ruta: str, tam_lote: int = TAM_LOTE_DEFECTO) -> Perfiles:
    """Construye los perfiles consumiendo :func:`leer_historial_por_lotes`.

    Args:
        ruta: Archivo CSV de historial.
        tam_lote: Eventos por lote.

    Returns:
        Diccionario ``{usuario_id: set(items)}``.
    """
    perfiles: Perfiles = {}
    for lote in leer_historial_por_lotes(ruta, tam_lote):
        for usuario_id, item_id in lote:
            perfiles.setdefault(usuario_id, set()).add(item_id)
    return perfiles


# --------------------------------------------------------------------------
# Procesamiento en paralelo
# --------------------------------------------------------------------------
def dividir_en_rangos(ruta: str, n_partes: int) -> list[tuple[int, int]]:
    """Divide el archivo en ``n_partes`` rangos de bytes ``[inicio, fin)``.

    Los cortes pueden caer en medio de una línea; :func:`_procesar_rango`
    se encarga de que cada línea la procese exactamente un rango (el que
    contiene su primer byte).

    Args:
        ruta: Archivo a dividir.
        n_partes: Cantidad de rangos deseada (al menos 1).

    Returns:
        Lista de tuplas ``(inicio, fin)`` que cubren todo el archivo.
    """
    tamanio = os.path.getsize(ruta)
    n_partes = max(1, min(n_partes, tamanio or 1))
    paso = tamanio // n_partes
    cortes = [i * paso for i in range(n_partes)] + [tamanio]
    return list(itertools.pairwise(cortes))


def _procesar_rango(args: tuple[str, int, int]) -> Perfiles:
    """Tarea de un worker: procesa las líneas que *empiezan* en ``[inicio, fin)``."""
    ruta, inicio, fin = args
    perfiles: Perfiles = {}
    with open(ruta, "rb", buffering=TAM_BUFFER_DEFECTO) as archivo:
        posicion = inicio
        if inicio > 0:
            # Retroceder un byte y descartar hasta el fin de esa línea: si
            # el byte anterior era "\n", la línea de `inicio` es nuestra.
            archivo.seek(inicio - 1)
            posicion = inicio - 1 + len(archivo.readline())
        while posicion < fin:
            linea = archivo.readline()
            if not linea:
                break
            posicion += len(linea)
            evento = _parsear_linea(linea)
            if evento is not None:
                perfiles.setdefault(evento[0], set()).add(evento[1])
    return perfiles


def combinar_perfiles(parciales: Iterable[Perfiles]) -> Perfiles:
    """Une varios diccionarios de perfiles (unión de sets por usuario).

    Args:
        parciales: Resultados parciales de cada worker.

    Returns:
        Un único diccionario ``{usuario_id: set(items)}``.
    """
    total: Perfiles = {}
    for parcial in parciales:
        for usuario_id, items in parcial.items():
            if usuario_id in total:
                total[usuario_id] |= items
            else:
                total[usuario_id] = items
    return total


def procesar_archivo_paralelo(ruta: str, n_procesos: int | None = None) -> Perfiles:
    """Procesa el archivo dividiéndolo en rangos que se leen en paralelo.

    Args:
        ruta: Archivo CSV de historial.
        n_procesos: Cantidad de procesos (por defecto, ``os.cpu_count()``).

    Returns:
        Diccionario ``{usuario_id: set(items)}``, igual al de
        :func:`procesar_archivo_por_lotes`.
    """
    n_procesos = n_procesos or os.cpu_count() or 1
    tareas = [(ruta, inicio, fin) for inicio, fin in dividir_en_rangos(ruta, n_procesos)]
    with mp.Pool(processes=len(tareas)) as pool:
        return combinar_perfiles(pool.imap_unordered(_procesar_rango, tareas))
