from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.costos import (
    calcular_costo_receta,
    calcular_costos_por_producto,
    comparar_estimado_vs_real,
)

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/costos-por-producto")
def costos_por_producto(db: Session = Depends(get_db)):
    return calcular_costos_por_producto(db)


@router.get("/evolucion-costos")
def evolucion_costos(db: Session = Depends(get_db), producto_id: int = None):
    query = db.query(models.CostoHistorico)
    if producto_id:
        query = query.filter(models.CostoHistorico.producto_id == producto_id)
    return query.order_by(models.CostoHistorico.fecha.desc()).all()


@router.get("/comparacion-estimado-real")
def comparacion_estimado_real(db: Session = Depends(get_db)):
    return comparar_estimado_vs_real(db)


@router.get("/costo-receta/{receta_id}")
def costo_receta_reporte(receta_id: int, db: Session = Depends(get_db)):
    try:
        return calcular_costo_receta(db, receta_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
