"""Tests del baseline y de la versión optimizada (equivalencia y cachés)."""
import pytest

from recommender.naive import RecomendadorNaive
from recommender.optimizado import RecomendadorOptimizado


def test_recomendacion_esperada(perfiles_chicos):
    assert RecomendadorOptimizado(perfiles_chicos).recomendar(1, top_n=5, k_vecinos=3) == [13, 15]


@pytest.mark.parametrize("top_n, k_vecinos", [(1, 1), (5, 3), (10, 20), (50, 100)])
def test_optimizado_equivale_al_baseline(perfiles_grandes, top_n, k_vecinos):
    naive = RecomendadorNaive(perfiles_grandes)
    optimizado = RecomendadorOptimizado(perfiles_grandes)
    for uid in range(0, 800, 37):
        esperado = naive.recomendar(uid, top_n, k_vecinos)
        assert optimizado.recomendar(uid, top_n, k_vecinos) == esperado


def test_usuario_inexistente_lanza_key_error(perfiles_chicos):
    with pytest.raises(KeyError):
        RecomendadorOptimizado(perfiles_chicos).recomendar(999)


def test_caching_devuelve_lo_mismo_sin_recalcular(perfiles_chicos, monkeypatch):
    motor = RecomendadorOptimizado(perfiles_chicos)
    primera = motor.recomendar(1, 5, 3)
    monkeypatch.setattr(motor, "_candidatos", lambda _: pytest.fail("no debía recalcular"))
    assert motor.recomendar(1, 5, 3) == primera


def test_resultado_cacheado_no_se_puede_corromper_desde_afuera(perfiles_chicos):
    motor = RecomendadorOptimizado(perfiles_chicos)
    motor.recomendar(1, 5, 3).append(12345)
    assert 12345 not in motor.recomendar(1, 5, 3)


def test_cache_distingue_top_n(perfiles_chicos):
    """Regresión: antes, pedir el Top 1 después del Top 5 devolvía 2 ítems."""
    motor = RecomendadorOptimizado(perfiles_chicos)
    assert motor.recomendar(1, top_n=5, k_vecinos=3) == [13, 15]
    assert motor.recomendar(1, top_n=1, k_vecinos=3) == [13]


def test_cache_se_invalida_si_cambia_un_vecino(perfiles_chicos):
    """Regresión: antes solo se miraba la versión del propio usuario."""
    motor = RecomendadorOptimizado(perfiles_chicos)
    motor.recomendar(1, 5, 3)
    motor.actualizar_usuario(2, {11, 12, 13, 77})
    assert 77 in motor.recomendar(1, 5, 3)
    assert motor.recomendar(1, 5, 3) == RecomendadorNaive(motor.usuarios).recomendar(1, 5, 3)


def test_memo_de_similitud_se_invalida(perfiles_chicos):
    motor = RecomendadorOptimizado(perfiles_chicos)
    assert motor.similitud(1, 2) == pytest.approx(2 / 5)
    motor.actualizar_usuario(2, {10, 11, 12, 14})
    assert motor.similitud(2, 1) == pytest.approx(1.0)


def test_actualizar_usuario_mantiene_indice_invertido(perfiles_chicos):
    motor = RecomendadorOptimizado(perfiles_chicos)
    motor.actualizar_usuario(1, {10, 99})
    assert 1 not in motor.item_a_usuarios[11]
    assert 1 in motor.item_a_usuarios[99]
    assert motor.version[1] == 1


def test_sin_vecinos_devuelve_lista_vacia():
    assert not RecomendadorOptimizado({1: {1}, 2: {2}}).recomendar(1)
