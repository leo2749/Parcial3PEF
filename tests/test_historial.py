"""Tests del registro de usuarios y del procesamiento de historiales."""
import pytest

from recommender.archivos import escribir_historial
from recommender.historial import (
    cargar_usuarios_desde_archivo,
    cargar_usuarios_desde_historial,
    procesar_historial,
    registrar_usuario,
)
from recommender.optimizado import RecomendadorOptimizado


def test_procesar_historial_agrupa_y_elimina_repetidos():
    assert procesar_historial([(1, 10), (1, 11), (2, 10), (1, 10)]) == {1: {10, 11}, 2: {10}}


def test_registrar_usuario_reemplaza_preferencias():
    motor = RecomendadorOptimizado({})
    registrar_usuario(motor, 1, {1, 2})
    registrar_usuario(motor, 1, {3})
    assert motor.usuarios[1] == {3}


def test_registrar_usuario_copia_el_set():
    motor = RecomendadorOptimizado({})
    items = {1, 2}
    registrar_usuario(motor, 1, items)
    items.add(3)
    assert motor.usuarios[1] == {1, 2}


def test_historial_es_acumulativo():
    motor = RecomendadorOptimizado({})
    registrar_usuario(motor, 1, {10})
    cargar_usuarios_desde_historial(motor, [(1, 11), (2, 12)])
    assert motor.usuarios == {1: {10, 11}, 2: {12}}


@pytest.mark.parametrize("paralelo", [False, True])
def test_cargar_desde_archivo(tmp_path, paralelo):
    ruta = tmp_path / "historial.csv"
    escribir_historial(str(ruta), [(1, 10), (2, 20), (1, 11)])
    motor = RecomendadorOptimizado({1: {5}})
    assert cargar_usuarios_desde_archivo(motor, str(ruta), paralelo=paralelo) == 2
    assert motor.usuarios == {1: {5, 10, 11}, 2: {20}}
