from fastapi import APIRouter
from app.api.v1.endpoints import (
    unidades_medida,
    proveedores,
    insumos,
    productos,
    recetas,
    compras,
    lotes,
    gastos,
    reportes,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(unidades_medida.router)
api_router.include_router(proveedores.router)
api_router.include_router(insumos.router)
api_router.include_router(productos.router)
api_router.include_router(recetas.router)
api_router.include_router(compras.router)
api_router.include_router(lotes.router)
api_router.include_router(gastos.router)
api_router.include_router(reportes.router)
