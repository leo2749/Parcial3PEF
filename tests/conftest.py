"""Fixtures compartidas por los tests."""
import pytest

from recommender.data_gen import generar_dataset


@pytest.fixture
def perfiles_chicos():
    """Dataset chico y legible, el mismo estado al que llega ``demo.py``."""
    return {
        1: {10, 11, 12, 14},
        2: {11, 12, 13},
        3: {10, 12, 14},
        4: {11, 12, 13, 15},
    }


@pytest.fixture
def perfiles_grandes():
    """Dataset sintético con suficientes empates como para probar el desempate."""
    return generar_dataset(n_usuarios=800, n_items=200, items_por_usuario=8, seed=7)
