Uso
===

Interfaces
----------

* ``python cli.py``: menú interactivo por consola.
* ``uvicorn api:app --reload``: API REST (FastAPI). La documentación
  interactiva queda en http://127.0.0.1:8000/docs.
* ``python demo.py``: recorrido guionado de las funcionalidades.

Ejemplo desde código
--------------------

.. code-block:: python

   from recommender.optimizado import RecomendadorOptimizado
   from recommender.historial import registrar_usuario, cargar_usuarios_desde_archivo

   motor = RecomendadorOptimizado(usuarios={})
   registrar_usuario(motor, 1, {10, 11, 12})
   registrar_usuario(motor, 2, {11, 12, 13})
   cargar_usuarios_desde_archivo(motor, "historial.csv", paralelo=True)
   motor.recomendar(1, top_n=5)

Formato de los archivos de historial
------------------------------------

CSV con encabezado ``usuario_id,item_id`` y una interacción por línea. Las
líneas inválidas se descartan. Ver :mod:`recommender.archivos`.
