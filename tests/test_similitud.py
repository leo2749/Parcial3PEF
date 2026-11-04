"""Tests de las funciones de puntuación compartidas."""
import pytest

from recommender.similitud import clave_vecino, puntaje_similitud, top_items


@pytest.mark.parametrize("items_a, items_b, esperado", [
    ({1, 2, 3}, {2, 3, 4}, 0.5),
    ({1, 2}, {1, 2}, 1.0),
    ({1, 2}, {3, 4}, 0.0),
    (set(), {1}, 0.0),
    (set(), set(), 0.0),
    ({1}, {1, 2, 3, 4}, 0.25),
])
def test_puntaje_similitud(items_a, items_b, esperado):
    assert puntaje_similitud(items_a, items_b) == pytest.approx(esperado)


def test_puntaje_similitud_es_simetrico():
    a, b = {1, 2, 5}, {2, 5, 9, 10}
    assert puntaje_similitud(a, b) == puntaje_similitud(b, a)


def test_clave_vecino_desempata_por_menor_id():
    ordenados = sorted([(3, 0.5), (1, 0.5), (2, 0.9)],
                       key=lambda par: clave_vecino(par[1], par[0]), reverse=True)
    assert [uid for uid, _ in ordenados] == [2, 1, 3]


def test_top_items_acumula_y_excluye_los_que_ya_tiene():
    perfiles = {1: {10, 20}, 2: {20, 30}}
    resultado = top_items([(1, 0.5), (2, 0.4)], objetivo={10}, perfiles=perfiles, top_n=5)
    # 20 -> 0.9, 30 -> 0.4 ; el 10 ya lo tiene el usuario
    assert resultado == [20, 30]


def test_top_items_ignora_vecinos_sin_similitud_y_respeta_top_n():
    perfiles = {1: {1, 2, 3}, 2: {99}}
    assert top_items([(1, 0.3), (2, 0.0)], set(), perfiles, top_n=2) == [1, 2]
