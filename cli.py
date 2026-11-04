"""
Interfaz de consola: acá es donde el "usuario del programa" (quien lo
corre, no un usuario sintético del dataset) realmente registra usuarios,
carga historiales de interacción y pide recomendaciones, en vez de que
todo esté hardcodeado en un script.

Ejecutar:  python3 cli.py
"""
import os
from collections.abc import Callable

from recommender.historial import (
    cargar_usuarios_desde_archivo,
    cargar_usuarios_desde_historial,
    registrar_usuario,
)
from recommender.optimizado import RecomendadorOptimizado

recomendador = RecomendadorOptimizado(usuarios={})
MIN_USUARIOS_SIMILITUD = 2


def pedir_entero(mensaje: str) -> int:
    """Pide por teclado un entero, repitiendo hasta que sea válido."""
    while True:
        valor = input(mensaje).strip()
        try:
            return int(valor)
        except ValueError:
            print("  Ingresá un número entero válido.")


def opcion_registrar_usuario() -> None:
    """Opción 1: alta o reemplazo de las preferencias de un usuario."""
    uid = pedir_entero("ID del usuario: ")
    crudo = input("Ítems que le gustan, separados por coma (ej: 10,11,12): ")
    try:
        items = {int(x.strip()) for x in crudo.split(",") if x.strip() != ""}
    except ValueError:
        print("  Los ítems deben ser números enteros separados por coma.")
        return
    if not items:
        print("  Tenés que indicar al menos un ítem.")
        return
    ya_existia = uid in recomendador.usuarios
    registrar_usuario(recomendador, uid, items)
    accion = "actualizado" if ya_existia else "registrado"
    print(f"  Usuario {uid} {accion}. Preferencias actuales: {recomendador.usuarios[uid]}")


def opcion_cargar_historial() -> None:
    """Opción 2: carga eventos ``usuario,item`` tipeados uno por línea."""
    print("  Ingresá eventos como 'usuario,item' (uno por línea). Línea vacía para terminar.")
    eventos = []
    while True:
        linea = input("  evento> ").strip()
        if linea == "":
            break
        try:
            uid_str, item_str = linea.split(",")
            eventos.append((int(uid_str.strip()), int(item_str.strip())))
        except ValueError:
            print("    Formato inválido, usá 'usuario,item' (ej: 3,14). Se ignora esta línea.")
    if not eventos:
        print("  No se cargó ningún evento.")
        return
    cargar_usuarios_desde_historial(recomendador, eventos)
    afectados = sorted({uid for uid, _ in eventos})
    print(f"  Historial procesado. Usuarios actualizados: {afectados}")
    for uid in afectados:
        print(f"    Usuario {uid} -> {recomendador.usuarios[uid]}")


def opcion_similitud() -> None:
    """Opción 3: similitud de Jaccard entre dos usuarios registrados."""
    if len(recomendador.usuarios) < MIN_USUARIOS_SIMILITUD:
        print("  Necesitás al menos 2 usuarios registrados.")
        return
    a = pedir_entero("ID del primer usuario: ")
    b = pedir_entero("ID del segundo usuario: ")
    if a not in recomendador.usuarios or b not in recomendador.usuarios:
        print("  Alguno de los dos usuarios no está registrado.")
        return
    sim = recomendador.similitud(a, b)
    print(f"  Similitud entre {a} y {b}: {sim:.2f}")


def opcion_recomendar() -> None:
    """Opción 4: Top N recomendaciones para un usuario."""
    if not recomendador.usuarios:
        print("  No hay usuarios registrados todavía.")
        return
    uid = pedir_entero("ID del usuario a recomendar: ")
    if uid not in recomendador.usuarios:
        print("  Ese usuario no está registrado.")
        return
    n = pedir_entero("¿Top cuántos resultados querés? (ej: 5): ")
    recs = recomendador.recomendar(uid, top_n=n, k_vecinos=20)
    if recs:
        print(f"  Top {n} recomendaciones para el usuario {uid}: {recs}")
    else:
        print("  Todavía no hay suficientes datos de otros usuarios para recomendar algo.")


def opcion_listar_usuarios() -> None:
    """Opción 5: lista los usuarios y sus preferencias."""
    if not recomendador.usuarios:
        print("  No hay usuarios registrados todavía.")
        return
    for uid, items in sorted(recomendador.usuarios.items()):
        print(f"  Usuario {uid}: {items}")


def opcion_cargar_archivo() -> None:
    """Opción 6: carga un historial grande desde un CSV ``usuario_id,item_id``."""
    ruta = input("Ruta del archivo CSV: ").strip().strip('"')
    if not os.path.isfile(ruta):
        print("  No existe ese archivo.")
        return
    paralelo = input("¿Procesar en paralelo? (s/N): ").strip().lower() == "s"
    afectados = cargar_usuarios_desde_archivo(recomendador, ruta, paralelo=paralelo)
    print(f"  Archivo procesado. Usuarios afectados: {afectados}. "
          f"Total registrados: {len(recomendador.usuarios)}")


MENU = """
=== Motor de recomendaciones — menú ===
1) Registrar usuario y sus preferencias
2) Cargar historial de interacciones (varios eventos)
3) Calcular similitud entre dos usuarios
4) Generar recomendaciones (Top N) para un usuario
5) Listar usuarios registrados
6) Cargar historial desde archivo CSV
0) Salir
"""


OPCIONES: dict[str, Callable[[], None]] = {
    "1": opcion_registrar_usuario,
    "2": opcion_cargar_historial,
    "3": opcion_similitud,
    "4": opcion_recomendar,
    "5": opcion_listar_usuarios,
    "6": opcion_cargar_archivo,
}


def main() -> None:
    """Bucle principal del menú."""
    while True:
        print(MENU)
        opcion = input("Elegí una opción: ").strip()
        if opcion == "0":
            print("Chau.")
            break
        accion = OPCIONES.get(opcion)
        if accion is None:
            print("  Opción inválida.")
        else:
            accion()


if __name__ == "__main__":
    main()
