from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("/", response_model=List[schemas.Producto])
def listar_productos(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    activo: bool = None,
):
    query = db.query(models.Producto)
    if activo is not None:
        query = query.filter(models.Producto.activo == activo)
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Producto, status_code=status.HTTP_201_CREATED)
def crear_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db)):
    db_producto = models.Producto(**producto.model_dump())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


@router.get("/{producto_id}", response_model=schemas.Producto)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.patch("/{producto_id}", response_model=schemas.Producto)
def actualizar_producto(
    producto_id: int,
    producto_in: schemas.ProductoUpdate,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in producto_in.model_dump(exclude_unset=True).items():
        setattr(producto, key, value)
    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(producto)
    db.commit()
    return None


@router.get("/{producto_id}/recetas", response_model=List[schemas.Receta])
def recetas_de_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    relaciones = (
        db.query(models.ProductoReceta)
        .filter(models.ProductoReceta.producto_id == producto_id)
        .all()
    )
    recetas = [r.receta for r in relaciones]
    return recetas
