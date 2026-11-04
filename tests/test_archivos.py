"""Tests de lectura/escritura de archivos grandes (lotes, buffer, paralelo)."""
# pylint: disable=protected-access
import itertools

import pytest

from recommender import archivos
from recommender.data_gen import generar_eventos
from recommender.historial import procesar_historial


@pytest.fixture
def archivo_historial(tmp_path):
    """Archivo con 5000 eventos y los perfiles que deberían salir de él."""
    eventos = list(generar_eventos(5000, n_usuarios=300, n_items=100, seed=3))
    ruta = str(tmp_path / "historial.csv")
    archivos.escribir_historial(ruta, eventos, tam_lote=777)
    return ruta, procesar_historial(eventos)


def test_escritura_por_lotes_e_ingenua_generan_el_mismo_archivo(tmp_path):
    eventos = list(generar_eventos(1234, 50, 50))
    por_lotes, ingenuo = tmp_path / "a.csv", tmp_path / "b.csv"
    assert archivos.escribir_historial(str(por_lotes), eventos, tam_lote=100) == 1234
    archivos.escribir_historial_ingenuo(str(ingenuo), eventos)
    assert por_lotes.read_bytes() == ingenuo.read_bytes()
    assert por_lotes.read_text(encoding="utf-8").splitlines()[0] == archivos.ENCABEZADO.strip()


def test_lectores_dan_el_mismo_resultado(archivo_historial):
    ruta, esperado = archivo_historial
    assert archivos.leer_historial_ingenuo(ruta) == esperado
    assert archivos.procesar_archivo_por_lotes(ruta, tam_lote=100) == esperado
    assert archivos.procesar_archivo_paralelo(ruta, n_procesos=3) == esperado


def test_lotes_respetan_el_tamanio(archivo_historial):
    ruta, _ = archivo_historial
    tamanios = [len(lote) for lote in archivos.leer_historial_por_lotes(ruta, tam_lote=1000)]
    assert tamanios == [1000] * 5


@pytest.mark.parametrize("n_partes", [1, 2, 7, 64, 1000])
def test_rangos_procesan_cada_linea_una_sola_vez(archivo_historial, n_partes):
    """Los cortes caen en medio de las líneas: ninguna se pierde ni se duplica."""
    ruta, esperado = archivo_historial
    rangos = archivos.dividir_en_rangos(ruta, n_partes)
    assert rangos[0][0] == 0
    assert all(fin == siguiente for (_, fin), (siguiente, _) in itertools.pairwise(rangos))

    lineas_procesadas = 0
    parciales = []
    for inicio, fin in rangos:
        parcial = archivos._procesar_rango((ruta, inicio, fin))
        parciales.append(parcial)
        lineas_procesadas += sum(len(items) for items in parcial.values())
    assert archivos.combinar_perfiles(parciales) == esperado
    # Un mismo (usuario, ítem) podría estar en dos rangos, pero nunca falta ninguno.
    assert lineas_procesadas >= sum(len(items) for items in esperado.values())


def test_lineas_invalidas_se_ignoran(tmp_path):
    ruta = tmp_path / "sucio.csv"
    ruta.write_text("usuario_id,item_id\n1,2\n\nbasura\n3,x\n4,5\n", encoding="utf-8")
    assert archivos.procesar_archivo_por_lotes(str(ruta)) == {1: {2}, 4: {5}}
    assert archivos._procesar_rango((str(ruta), 0, ruta.stat().st_size)) == {1: {2}, 4: {5}}


def test_archivo_vacio(tmp_path):
    ruta = tmp_path / "vacio.csv"
    ruta.write_text("", encoding="utf-8")
    assert not archivos.procesar_archivo_por_lotes(str(ruta))
    assert not archivos.procesar_archivo_paralelo(str(ruta), n_procesos=2)


def test_parsear_linea_acepta_str_y_bytes():
    assert archivos._parsear_linea("3,14\n") == (3, 14)
    assert archivos._parsear_linea(b"3,14\r\n") == (3, 14)
    assert archivos._parsear_linea("usuario_id,item_id") is None
