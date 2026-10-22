from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.punto_equilibrio import calcular_y_guardar_punto_equilibrio

router = APIRouter(prefix="/punto-equilibrio", tags=["punto-equilibrio"])


@router.post("/calcular", response_model=schemas.PuntoEquilibrioResponse, status_code=status.HTTP_201_CREATED)
def calcular_punto_equilibrio(
    data: schemas.PuntoEquilibrioInput,
    db: Session = Depends(get_db),
):
    try:
        return calcular_y_guardar_punto_equilibrio(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.PuntoEquilibrioResponse])
def listar_puntos_equilibrio(db: Session = Depends(get_db)):
    return (
        db.query(models.PuntoEquilibrio)
        .order_by(models.PuntoEquilibrio.fecha_calculo.desc())
        .all()
    )


@router.get("/{punto_id}", response_model=schemas.PuntoEquilibrioResponse)
def obtener_punto_equilibrio(punto_id: int, db: Session = Depends(get_db)):
    punto = db.query(models.PuntoEquilibrio).filter(models.PuntoEquilibrio.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de equilibrio no encontrado")
    return punto
