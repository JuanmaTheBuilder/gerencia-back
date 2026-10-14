from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.lotes import crear_lote, cerrar_lote

router = APIRouter(prefix="/lotes-produccion", tags=["lotes-produccion"])


@router.get("/", response_model=List[schemas.LoteProduccion])
def listar_lotes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    estado: str = None,
):
    query = db.query(models.LoteProduccion)
    if estado:
        query = query.filter(models.LoteProduccion.estado == estado.upper())
    return query.order_by(models.LoteProduccion.fecha.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.LoteProduccionDetail, status_code=status.HTTP_201_CREATED)
def registrar_lote(lote: schemas.LoteProduccionCreate, db: Session = Depends(get_db)):
    if not lote.productos:
        raise HTTPException(status_code=400, detail="El lote debe tener al menos un producto fabricado")
    return crear_lote(db, lote)


@router.get("/{lote_id}", response_model=schemas.LoteProduccionDetail)
def obtener_lote(lote_id: int, db: Session = Depends(get_db)):
    lote = db.query(models.LoteProduccion).filter(models.LoteProduccion.id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


@router.patch("/{lote_id}/cerrar", response_model=schemas.LoteProduccionDetail)
def cerrar_lote_endpoint(lote_id: int, db: Session = Depends(get_db)):
    try:
        return cerrar_lote(db, lote_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lote_id}/gastos", response_model=schemas.GastoLote, status_code=status.HTTP_201_CREATED)
def asignar_gasto_a_lote(
    lote_id: int,
    gasto_lote_in: schemas.GastoLoteCreate,
    db: Session = Depends(get_db),
):
    lote = db.query(models.LoteProduccion).filter(models.LoteProduccion.id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    if lote.estado == "CERRADO":
        raise HTTPException(status_code=400, detail="No se pueden asignar gastos a un lote cerrado")

    gasto = db.query(models.Gasto).filter(models.Gasto.id == gasto_lote_in.gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    db_gasto_lote = models.GastoLote(
        lote_id=lote_id,
        gasto_id=gasto_lote_in.gasto_id,
        monto_asignado=gasto_lote_in.monto_asignado,
    )
    db.add(db_gasto_lote)
    db.commit()
    db.refresh(db_gasto_lote)
    return db_gasto_lote
