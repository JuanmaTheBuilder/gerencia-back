import os

# Forzar uso de la base de datos de pruebas antes de importar la app
os.environ["DATABASE_URL"] = "postgresql://postgres:Balto2018@localhost:5432/gerencia_costos_test"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.db.session import get_db
from app.core.config import settings
from app.models import models

engine_test = create_engine(settings.DATABASE_URL)
SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = SessionLocalTest()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def limpiar_datos_prueba():
    """Limpia registros de prueba despues de cada test para no contaminar la BD."""
    yield
    db = SessionLocalTest()
    try:
        db.query(models.CostoHistorico).delete()
        db.query(models.GastoLote).delete()
        db.query(models.Gasto).delete()
        db.query(models.LoteInsumo).delete()
        db.query(models.LoteProducto).delete()
        db.query(models.LoteProduccion).delete()
        db.query(models.CompraDetalle).delete()
        db.query(models.HistorialPrecioInsumo).delete()
        db.query(models.Compra).delete()
        # Eliminar insumos de prueba (id > 5 son los de ejemplo)
        db.query(models.Insumo).filter(models.Insumo.id > 5).delete()
        # Restaurar precios y stock de los insumos de ejemplo
        db.query(models.Insumo).update({
            models.Insumo.precio_compra: 0,
            models.Insumo.stock_actual: 0,
        })
        db.commit()
    finally:
        db.close()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_listar_insumos():
    response = client.get("/api/v1/insumos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    nombres = [i["nombre"] for i in data]
    assert "Madera pino" in nombres


def test_crear_insumo():
    response = client.post("/api/v1/insumos/", json={
        "nombre": "Insumo de prueba",
        "unidad_medida_id": 3,
        "precio_compra": "10.00",
        "stock_actual": "0",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Insumo de prueba"
    assert data["activo"] is True


def test_crear_compra_y_historial_precios():
    response = client.post("/api/v1/compras/", json={
        "proveedor_id": 1,
        "detalles": [
            {"insumo_id": 1, "cantidad": "100", "precio_unitario": "3.00"},
            {"insumo_id": 2, "cantidad": "500", "precio_unitario": "0.15"},
        ]
    })
    assert response.status_code == 201
    compra = response.json()
    assert float(compra["total"]) == 375.0

    # Verificar que se registro el historial de precios
    response = client.get("/api/v1/insumos/1/precios")
    assert response.status_code == 200
    precios = response.json()
    assert len(precios) == 1
    assert float(precios[0]["precio"]) == 3.00

    # Verificar stock actualizado
    response = client.get("/api/v1/insumos/1")
    assert response.status_code == 200
    insumo = response.json()
    assert float(insumo["stock_actual"]) == 100.0
    assert float(insumo["precio_compra"]) == 3.00


def test_costo_estimado_receta():
    # Comprar insumos para establecer precios
    client.post("/api/v1/compras/", json={
        "proveedor_id": 1,
        "detalles": [
            {"insumo_id": 1, "cantidad": "100", "precio_unitario": "2.00"},
            {"insumo_id": 2, "cantidad": "500", "precio_unitario": "0.10"},
            {"insumo_id": 3, "cantidad": "20", "precio_unitario": "5.00"},
        ]
    })

    response = client.get("/api/v1/recetas/1/costo-estimado")
    assert response.status_code == 200
    data = response.json()
    # Receta silla: 2.5 madera * 2.00 + 8 tornillos * 0.10 + 0.2 pegamento * 5.00 = 5.00 + 0.80 + 1.00 = 6.80
    assert float(data["costo_total_estimado"]) == 6.80


def test_crear_y_cerrar_lote():
    # Comprar insumos
    client.post("/api/v1/compras/", json={
        "proveedor_id": 1,
        "detalles": [
            {"insumo_id": 1, "cantidad": "100", "precio_unitario": "2.00"},
            {"insumo_id": 2, "cantidad": "500", "precio_unitario": "0.10"},
            {"insumo_id": 3, "cantidad": "20", "precio_unitario": "5.00"},
        ]
    })

    # Crear gasto y asignarlo al lote
    response = client.post("/api/v1/gastos/", json={
        "categoria": "Mano de obra",
        "descripcion": "Operarios",
        "monto": "30.00",
    })
    assert response.status_code == 201
    gasto_id = response.json()["id"]

    # Crear lote
    response = client.post("/api/v1/lotes-produccion/", json={
        "productos": [{"producto_id": 1, "receta_id": 1, "cantidad": "10"}],
        "insumos": [
            {"insumo_id": 1, "cantidad": "25"},
            {"insumo_id": 2, "cantidad": "80"},
            {"insumo_id": 3, "cantidad": "2"},
        ]
    })
    assert response.status_code == 201
    lote = response.json()
    lote_id = lote["id"]

    # Asignar gasto al lote
    response = client.post(f"/api/v1/lotes-produccion/{lote_id}/gastos", json={
        "gasto_id": gasto_id,
        "lote_id": lote_id,
        "monto_asignado": "30.00",
    })
    assert response.status_code == 201

    # Cerrar lote
    response = client.patch(f"/api/v1/lotes-produccion/{lote_id}/cerrar")
    assert response.status_code == 200
    lote_cerrado = response.json()
    assert lote_cerrado["estado"] == "CERRADO"
    # Costo insumos: 25*2 + 80*0.1 + 2*5 = 50 + 8 + 10 = 68; + gasto 30 = 98
    assert float(lote_cerrado["costo_real_total"]) == 98.0

    # Verificar costos historicos
    response = client.get("/api/v1/reportes/evolucion-costos?producto_id=1")
    assert response.status_code == 200
    historicos = response.json()
    assert len(historicos) == 1
    assert float(historicos[0]["costo_total"]) == 98.0
    assert float(historicos[0]["costo_unitario"]) == 9.8


def test_desactivar_producto():
    response = client.patch("/api/v1/productos/1", json={"activo": False})
    assert response.status_code == 200
    data = response.json()
    assert data["activo"] is False

    response = client.get("/api/v1/productos/?activo=true")
    assert response.status_code == 200
    data = response.json()
    assert all(p["activo"] for p in data)
    assert len(data) == 2


def test_reporte_costos_por_producto():
    # Comprar y producir
    client.post("/api/v1/compras/", json={
        "proveedor_id": 1,
        "detalles": [
            {"insumo_id": 1, "cantidad": "100", "precio_unitario": "2.00"},
            {"insumo_id": 2, "cantidad": "500", "precio_unitario": "0.10"},
            {"insumo_id": 3, "cantidad": "20", "precio_unitario": "5.00"},
        ]
    })
    response = client.post("/api/v1/lotes-produccion/", json={
        "productos": [{"producto_id": 1, "receta_id": 1, "cantidad": "10"}],
        "insumos": [
            {"insumo_id": 1, "cantidad": "25"},
            {"insumo_id": 2, "cantidad": "80"},
            {"insumo_id": 3, "cantidad": "2"},
        ]
    })
    lote_id = response.json()["id"]
    client.patch(f"/api/v1/lotes-produccion/{lote_id}/cerrar")

    response = client.get("/api/v1/reportes/costos-por-producto")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["producto_id"] == 1
    assert float(data[0]["cantidad_total_fabricada"]) == 10.0
