"""Tests de integración de la API REST (FastAPI + TestClient)."""
import pytest
from fastapi.testclient import TestClient

from api import crear_app
from recommender.archivos import escribir_historial
from recommender.optimizado import RecomendadorOptimizado


@pytest.fixture
def cliente(perfiles_chicos):
    """Cliente HTTP contra una app con el dataset chico precargado."""
    return TestClient(crear_app(RecomendadorOptimizado(perfiles_chicos)))


def test_flujo_completo():
    cliente = TestClient(crear_app())
    assert cliente.put("/usuarios", json={"usuario_id": 1, "items": [10, 11]}).status_code == 201
    respuesta = cliente.post("/historial", json=[{"usuario_id": 2, "item_id": 10},
                                                 {"usuario_id": 2, "item_id": 12}])
    assert respuesta.json() == {"usuarios_afectados": [2]}
    assert cliente.get("/usuarios").json() == {"1": [10, 11], "2": [10, 12]}
    assert cliente.get("/similitud/1/2").json() == {"similitud": pytest.approx(1 / 3)}
    assert cliente.get("/recomendaciones/1").json()["items"] == [12]


def test_recomendaciones_top_n(cliente):
    respuesta = cliente.get("/recomendaciones/1", params={"top_n": 1, "k_vecinos": 3})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"usuario_id": 1, "top_n": 1, "items": [13]}


@pytest.mark.parametrize("url", ["/recomendaciones/999", "/similitud/1/999"])
def test_usuario_inexistente_404(cliente, url):
    assert cliente.get(url).status_code == 404


@pytest.mark.parametrize("cuerpo", [{"usuario_id": 1, "items": []},
                                    {"usuario_id": "x", "items": [1]}])
def test_validacion_de_entrada_422(cliente, cuerpo):
    assert cliente.put("/usuarios", json=cuerpo).status_code == 422


def test_top_n_fuera_de_rango_422(cliente):
    assert cliente.get("/recomendaciones/1", params={"top_n": 0}).status_code == 422


def test_cargar_archivo(perfiles_chicos, tmp_path):
    cliente = TestClient(crear_app(RecomendadorOptimizado(perfiles_chicos), tmp_path))
    escribir_historial(str(tmp_path / "h.csv"), [(9, 10), (9, 11)])
    respuesta = cliente.post("/historial/archivo", json={"ruta": "h.csv"})
    assert respuesta.json() == {"usuarios_afectados": 1, "total_usuarios": 5}
    assert cliente.post("/historial/archivo", json={"ruta": "no_existe.csv"}).status_code == 404


@pytest.mark.parametrize("ruta", ["../fuera.csv", "sub/../../fuera.csv"])
def test_cargar_archivo_rechaza_path_traversal(tmp_path, ruta):
    """Seguridad (CWE-22): no se puede leer fuera del directorio de datos."""
    datos = tmp_path / "datos"
    datos.mkdir()
    escribir_historial(str(tmp_path / "fuera.csv"), [(1, 1)])
    cliente = TestClient(crear_app(directorio_datos=datos))
    assert cliente.post("/historial/archivo", json={"ruta": ruta}).status_code == 403


def test_cargar_archivo_rechaza_ruta_absoluta_externa(tmp_path):
    datos = tmp_path / "datos"
    datos.mkdir()
    externo = tmp_path / "externo.csv"
    escribir_historial(str(externo), [(1, 1)])
    cliente = TestClient(crear_app(directorio_datos=datos))
    assert cliente.post("/historial/archivo", json={"ruta": str(externo)}).status_code == 403
    assert not cliente.get("/usuarios").json()


def test_directorio_de_datos_por_variable_de_entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("MOTOR_DIR_DATOS", str(tmp_path))
    escribir_historial(str(tmp_path / "h.csv"), [(3, 30)])
    cliente = TestClient(crear_app())
    assert cliente.post("/historial/archivo", json={"ruta": "h.csv"}).status_code == 200
