from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/unidades-medida", tags=["unidades-medida"])


@router.get("/", response_model=List[schemas.UnidadMedida])
def listar_unidades_medida(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(models.UnidadMedida).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.UnidadMedida, status_code=status.HTTP_201_CREATED)
def crear_unidad_medida(unidad: schemas.UnidadMedidaCreate, db: Session = Depends(get_db)):
    db_unidad = models.UnidadMedida(**unidad.model_dump())
    db.add(db_unidad)
    db.commit()
    db.refresh(db_unidad)
    return db_unidad


@router.get("/{unidad_id}", response_model=schemas.UnidadMedida)
def obtener_unidad_medida(unidad_id: int, db: Session = Depends(get_db)):
    unidad = db.query(models.UnidadMedida).filter(models.UnidadMedida.id == unidad_id).first()
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    return unidad


@router.patch("/{unidad_id}", response_model=schemas.UnidadMedida)
def actualizar_unidad_medida(
    unidad_id: int,
    unidad_in: schemas.UnidadMedidaUpdate,
    db: Session = Depends(get_db),
):
    unidad = db.query(models.UnidadMedida).filter(models.UnidadMedida.id == unidad_id).first()
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    for key, value in unidad_in.model_dump(exclude_unset=True).items():
        setattr(unidad, key, value)
    db.commit()
    db.refresh(unidad)
    return unidad


@router.delete("/{unidad_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_unidad_medida(unidad_id: int, db: Session = Depends(get_db)):
    unidad = db.query(models.UnidadMedida).filter(models.UnidadMedida.id == unidad_id).first()
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    db.delete(unidad)
    db.commit()
    return None
