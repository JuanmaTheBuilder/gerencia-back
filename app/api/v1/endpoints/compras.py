from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.compras import crear_compra

router = APIRouter(prefix="/compras", tags=["compras"])


@router.get("/", response_model=List[schemas.Compra])
def listar_compras(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(models.Compra).order_by(models.Compra.fecha.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Compra, status_code=status.HTTP_201_CREATED)
def registrar_compra(compra: schemas.CompraCreate, db: Session = Depends(get_db)):
    if not compra.detalles:
        raise HTTPException(status_code=400, detail="La compra debe tener al menos un detalle")
    return crear_compra(db, compra)


@router.get("/{compra_id}", response_model=schemas.Compra)
def obtener_compra(compra_id: int, db: Session = Depends(get_db)):
    compra = db.query(models.Compra).filter(models.Compra.id == compra_id).first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return compra


@router.delete("/{compra_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_compra(compra_id: int, db: Session = Depends(get_db)):
    compra = db.query(models.Compra).filter(models.Compra.id == compra_id).first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    db.delete(compra)
    db.commit()
    return None
