from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/gastos", tags=["gastos"])


@router.get("/", response_model=List[schemas.Gasto])
def listar_gastos(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(models.Gasto).order_by(models.Gasto.fecha.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Gasto, status_code=status.HTTP_201_CREATED)
def crear_gasto(gasto: schemas.GastoCreate, db: Session = Depends(get_db)):
    db_gasto = models.Gasto(**gasto.model_dump())
    db.add(db_gasto)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto


@router.get("/{gasto_id}", response_model=schemas.Gasto)
def obtener_gasto(gasto_id: int, db: Session = Depends(get_db)):
    gasto = db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


@router.patch("/{gasto_id}", response_model=schemas.Gasto)
def actualizar_gasto(
    gasto_id: int,
    gasto_in: schemas.GastoUpdate,
    db: Session = Depends(get_db),
):
    gasto = db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    for key, value in gasto_in.model_dump(exclude_unset=True).items():
        setattr(gasto, key, value)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_gasto(gasto_id: int, db: Session = Depends(get_db)):
    gasto = db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(gasto)
    db.commit()
    return None
