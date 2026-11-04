"""
API REST del motor de recomendaciones, hecha con el framework FastAPI.

Expone por HTTP las mismas funcionalidades que ``cli.py``. FastAPI valida
los datos de entrada con modelos Pydantic y genera documentación
interactiva automática (OpenAPI) en ``/docs``.

Ejecutar:  uvicorn api:app --reload      ->  http://127.0.0.1:8000/docs

Seguridad: ``POST /historial/archivo`` solo lee archivos que estén dentro del
directorio de datos (variable de entorno ``MOTOR_DIR_DATOS``, por defecto
``./datos``). Antes aceptaba cualquier ruta del servidor (CWE-22, *path
traversal*); ver ``docs/seguridad.md``.
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from recommender.historial import (
    cargar_usuarios_desde_archivo,
    cargar_usuarios_desde_historial,
    registrar_usuario,
)
from recommender.optimizado import RecomendadorOptimizado


class Usuario(BaseModel):
    """Alta o actualización de un usuario."""
    usuario_id: int
    items: list[int] = Field(min_length=1, description="Ítems que le gustan al usuario")


class Evento(BaseModel):
    """Una interacción ``usuario -> ítem`` de un historial."""
    usuario_id: int
    item_id: int


class Archivo(BaseModel):
    """Historial CSV a cargar desde el disco del servidor."""
    ruta: str
    paralelo: bool = False


class Recomendacion(BaseModel):
    """Resultado de una consulta de recomendaciones."""
    usuario_id: int
    top_n: int
    items: list[int]


DIR_DATOS_DEFECTO = "datos"


def resolver_ruta_segura(ruta: str, directorio_datos: Path) -> Path:
    """Resuelve ``ruta`` y verifica que quede dentro de ``directorio_datos``.

    Las rutas relativas se interpretan desde ``directorio_datos``. Se
    resuelven ``..`` y enlaces simbólicos antes de comparar, así que
    ``../../etc/passwd`` o una ruta absoluta externa se rechazan.

    Args:
        ruta: Ruta recibida del cliente.
        directorio_datos: Único directorio desde el que se permite leer.

    Returns:
        La ruta absoluta y resuelta.

    Raises:
        PermissionError: Si la ruta queda fuera de ``directorio_datos``.
    """
    base = directorio_datos.resolve()
    destino = (base / ruta).resolve()
    if not destino.is_relative_to(base):
        raise PermissionError(f"Ruta fuera del directorio de datos: {ruta}")
    return destino


def crear_app(recomendador: RecomendadorOptimizado | None = None,
              directorio_datos: str | Path | None = None) -> FastAPI:
    """Construye la aplicación FastAPI.

    Recibir el recomendador por parámetro (inyección de dependencias)
    permite que cada test use una instancia limpia.

    Args:
        recomendador: Motor a exponer; si es ``None`` se crea uno vacío.
        directorio_datos: Directorio desde el que se permite cargar historiales.
            Si es ``None`` se usa ``MOTOR_DIR_DATOS`` o ``./datos``.

    Returns:
        La aplicación lista para servir con uvicorn.
    """
    motor = recomendador if recomendador is not None else RecomendadorOptimizado(usuarios={})
    dir_datos = Path(directorio_datos if directorio_datos is not None
                     else os.environ.get("MOTOR_DIR_DATOS", DIR_DATOS_DEFECTO))
    aplicacion = FastAPI(title="Motor de recomendaciones",
                         description="Filtrado colaborativo usuario-usuario (Jaccard).")

    def exigir_usuario(usuario_id: int) -> None:
        if usuario_id not in motor.usuarios:
            raise HTTPException(status_code=404, detail=f"Usuario {usuario_id} no registrado")

    @aplicacion.get("/usuarios")
    def listar_usuarios() -> dict[int, list[int]]:
        """Lista los usuarios registrados y sus ítems."""
        return {uid: sorted(items) for uid, items in sorted(motor.usuarios.items())}

    @aplicacion.put("/usuarios", status_code=201)
    def registrar(usuario: Usuario) -> dict[str, object]:
        """Registra un usuario o reemplaza sus preferencias."""
        registrar_usuario(motor, usuario.usuario_id, set(usuario.items))
        return {"usuario_id": usuario.usuario_id,
                "items": sorted(motor.usuarios[usuario.usuario_id])}

    @aplicacion.post("/historial")
    def cargar_historial(eventos: list[Evento]) -> dict[str, list[int]]:
        """Suma un historial de interacciones a las preferencias existentes."""
        cargar_usuarios_desde_historial(motor, ((e.usuario_id, e.item_id) for e in eventos))
        return {"usuarios_afectados": sorted({e.usuario_id for e in eventos})}

    @aplicacion.post("/historial/archivo")
    def cargar_archivo(archivo: Archivo) -> dict[str, int]:
        """Carga un historial CSV grande (por lotes o en paralelo).

        La ruta debe estar dentro del directorio de datos (403 si no).
        """
        try:
            ruta = resolver_ruta_segura(archivo.ruta, dir_datos)
            afectados = cargar_usuarios_desde_archivo(motor, str(ruta), archivo.paralelo)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="Ruta no permitida") from error
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="Archivo no encontrado") from error
        return {"usuarios_afectados": afectados, "total_usuarios": len(motor.usuarios)}

    @aplicacion.get("/similitud/{a_id}/{b_id}")
    def similitud(a_id: int, b_id: int) -> dict[str, float]:
        """Similitud de Jaccard entre dos usuarios."""
        exigir_usuario(a_id)
        exigir_usuario(b_id)
        return {"similitud": motor.similitud(a_id, b_id)}

    @aplicacion.get("/recomendaciones/{usuario_id}", response_model=Recomendacion)
    def recomendar(usuario_id: int,
                   top_n: int = Query(10, ge=1, le=100),
                   k_vecinos: int = Query(20, ge=1, le=500)) -> Recomendacion:
        """Top N ítems recomendados para un usuario."""
        exigir_usuario(usuario_id)
        items = motor.recomendar(usuario_id, top_n=top_n, k_vecinos=k_vecinos)
        return Recomendacion(usuario_id=usuario_id, top_n=top_n, items=items)

    return aplicacion


app = crear_app()
