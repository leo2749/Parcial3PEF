"""Tests del cálculo de recomendaciones en batch."""
from recommender.concurrente import recomendar_batch_concurrente, recomendar_batch_secuencial
from recommender.optimizado import RecomendadorOptimizado


def test_concurrente_equivale_a_secuencial(perfiles_grandes):
    ids = list(range(60))
    secuencial = recomendar_batch_secuencial(RecomendadorOptimizado(perfiles_grandes), ids, 5, 10)
    concurrente = recomendar_batch_concurrente(perfiles_grandes, ids, 5, 10, n_workers=2)
    assert concurrente == secuencial
