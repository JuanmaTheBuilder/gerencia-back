from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/recursos", tags=["recursos"])


@router.get("/", response_model=List[schemas.Recurso])
def listar_recursos(db: Session = Depends(get_db)):
    return db.query(models.Recurso).order_by(models.Recurso.tipo, models.Recurso.nombre).all()


@router.post("/", response_model=schemas.Recurso, status_code=status.HTTP_201_CREATED)
def crear_recurso(recurso: schemas.RecursoCreate, db: Session = Depends(get_db)):
    db_recurso = models.Recurso(**recurso.model_dump())
    db.add(db_recurso)
    db.commit()
    db.refresh(db_recurso)
    return db_recurso


@router.get("/{recurso_id}", response_model=schemas.Recurso)
def obtener_recurso(recurso_id: int, db: Session = Depends(get_db)):
    recurso = db.query(models.Recurso).filter(models.Recurso.id == recurso_id).first()
    if not recurso:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return recurso


@router.patch("/{recurso_id}", response_model=schemas.Recurso)
def actualizar_recurso(
    recurso_id: int,
    recurso_in: schemas.RecursoUpdate,
    db: Session = Depends(get_db),
):
    recurso = db.query(models.Recurso).filter(models.Recurso.id == recurso_id).first()
    if not recurso:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    for key, value in recurso_in.model_dump(exclude_unset=True).items():
        setattr(recurso, key, value)
    db.commit()
    db.refresh(recurso)
    return recurso


@router.delete("/{recurso_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_recurso(recurso_id: int, db: Session = Depends(get_db)):
    recurso = db.query(models.Recurso).filter(models.Recurso.id == recurso_id).first()
    if not recurso:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    db.delete(recurso)
    db.commit()
    return None
