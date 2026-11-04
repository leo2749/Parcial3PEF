"""
Demostración de las 5 "funcionalidades posibles" que pide la consigna
de la Opción 2, en orden, con datos chicos y legibles (para mostrar en
la presentación oral, no para medir rendimiento — eso lo hace benchmark.py
con un dataset grande).

Ejecutar:  python3 demo.py
"""
from recommender.historial import (
    cargar_usuarios_desde_historial,
    procesar_historial,
    registrar_usuario,
)
from recommender.optimizado import RecomendadorOptimizado


def main() -> None:
    """Ejecuta el recorrido completo, imprimiendo cada paso."""
    print("=== 1) Registrar usuarios y preferencias ===")
    # Alta manual de un par de usuarios con sus preferencias iniciales.
    recomendador = RecomendadorOptimizado(usuarios={})
    registrar_usuario(recomendador, usuario_id=1, items={10, 11, 12})
    registrar_usuario(recomendador, usuario_id=2, items={11, 12, 13})
    print("Usuario 1:", recomendador.usuarios[1])
    print("Usuario 2:", recomendador.usuarios[2])

    print("\n=== 2) Procesar historial de interacción ===")
    # Un historial "crudo": cada tupla es (usuario_id, item_id), como si
    # viniera de un log de clics/compras.
    historial_crudo = [
        (3, 10), (3, 12), (3, 14),
        (4, 11), (4, 12), (4, 13), (4, 15),
        (1, 14),   # el usuario 1 interactúa con un ítem nuevo
    ]
    nuevas_preferencias = procesar_historial(historial_crudo)
    print("Preferencias derivadas del historial:", nuevas_preferencias)

    # Registrar/actualizar a todos los usuarios que aparecen en el historial.
    cargar_usuarios_desde_historial(recomendador, historial_crudo)
    print("Usuario 1 actualizado con el nuevo ítem:", recomendador.usuarios[1])
    print("Usuario 3 (nuevo, viene del historial):", recomendador.usuarios[3])

    print("\n=== 3) Calcular similitudes ===")
    sim_1_2 = recomendador.similitud(1, 2)
    sim_1_4 = recomendador.similitud(1, 4)
    print(f"Similitud usuario 1 vs usuario 2: {sim_1_2:.2f}")
    print(f"Similitud usuario 1 vs usuario 4: {sim_1_4:.2f}")

    print("\n=== 4) Generar recomendaciones ===")
    recs_usuario_1 = recomendador.recomendar(usuario_id=1, top_n=5, k_vecinos=3)
    print("Recomendaciones para el usuario 1:", recs_usuario_1)

    print("\n=== 5) Obtener los Top N resultados ===")
    for n in (1, 3, 5):
        print(f"Top {n} para el usuario 1:", recomendador.recomendar(1, top_n=n, k_vecinos=3))


if __name__ == "__main__":
    main()
