from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


@router.get("/", response_model=List[schemas.Proveedor])
def listar_proveedores(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(models.Proveedor).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Proveedor, status_code=status.HTTP_201_CREATED)
def crear_proveedor(proveedor: schemas.ProveedorCreate, db: Session = Depends(get_db)):
    db_proveedor = models.Proveedor(**proveedor.model_dump())
    db.add(db_proveedor)
    db.commit()
    db.refresh(db_proveedor)
    return db_proveedor


@router.get("/{proveedor_id}", response_model=schemas.Proveedor)
def obtener_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.patch("/{proveedor_id}", response_model=schemas.Proveedor)
def actualizar_proveedor(
    proveedor_id: int,
    proveedor_in: schemas.ProveedorUpdate,
    db: Session = Depends(get_db),
):
    proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for key, value in proveedor_in.model_dump(exclude_unset=True).items():
        setattr(proveedor, key, value)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    db.delete(proveedor)
    db.commit()
    return None
