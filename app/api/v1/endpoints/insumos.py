from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/insumos", tags=["insumos"])


@router.get("/", response_model=List[schemas.Insumo])
def listar_insumos(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    activo: bool = None,
):
    query = db.query(models.Insumo).order_by(models.Insumo.id)
    if activo is not None:
        query = query.filter(models.Insumo.activo == activo)
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Insumo, status_code=status.HTTP_201_CREATED)
def crear_insumo(insumo: schemas.InsumoCreate, db: Session = Depends(get_db)):
    db_insumo = models.Insumo(**insumo.model_dump())
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo


@router.get("/{insumo_id}", response_model=schemas.InsumoDetail)
def obtener_insumo(insumo_id: int, db: Session = Depends(get_db)):
    insumo = db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    return insumo


@router.patch("/{insumo_id}", response_model=schemas.Insumo)
def actualizar_insumo(
    insumo_id: int,
    insumo_in: schemas.InsumoUpdate,
    db: Session = Depends(get_db),
):
    insumo = db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    for key, value in insumo_in.model_dump(exclude_unset=True).items():
        setattr(insumo, key, value)
    db.commit()
    db.refresh(insumo)
    return insumo


@router.delete("/{insumo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_insumo(insumo_id: int, db: Session = Depends(get_db)):
    insumo = db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    db.delete(insumo)
    db.commit()
    return None


@router.get("/{insumo_id}/precios", response_model=List[schemas.HistorialPrecioInsumo])
def historial_precios(insumo_id: int, db: Session = Depends(get_db)):
    insumo = db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    return (
        db.query(models.HistorialPrecioInsumo)
        .filter(models.HistorialPrecioInsumo.insumo_id == insumo_id)
        .order_by(models.HistorialPrecioInsumo.fecha.desc())
        .all()
    )


@router.post("/{insumo_id}/precios", response_model=schemas.HistorialPrecioInsumo, status_code=status.HTTP_201_CREATED)
def registrar_precio(
    insumo_id: int,
    precio_in: schemas.HistorialPrecioInsumoCreate,
    db: Session = Depends(get_db),
):
    insumo = db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    db_precio = models.HistorialPrecioInsumo(
        insumo_id=insumo_id,
        precio=precio_in.precio,
        compra_id=precio_in.compra_id,
    )
    db.add(db_precio)
    db.commit()
    db.refresh(db_precio)
    return db_precio
