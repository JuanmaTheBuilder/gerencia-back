from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/precios-venta", tags=["precios-venta"])


@router.get("/", response_model=List[schemas.PrecioVenta])
def listar_precios_venta(db: Session = Depends(get_db)):
    return db.query(models.PrecioVenta).order_by(models.PrecioVenta.fecha_inicio.desc()).all()


@router.get("/producto/{producto_id}", response_model=schemas.PrecioVenta)
def obtener_precio_activo(producto_id: int, db: Session = Depends(get_db)):
    precio = (
        db.query(models.PrecioVenta)
        .filter(
            models.PrecioVenta.producto_id == producto_id,
            models.PrecioVenta.activo == True,
        )
        .order_by(models.PrecioVenta.fecha_inicio.desc())
        .first()
    )
    if not precio:
        raise HTTPException(status_code=404, detail="No hay precio de venta activo para este producto")
    return precio


@router.post("/", response_model=schemas.PrecioVenta, status_code=status.HTTP_201_CREATED)
def crear_precio_venta(precio: schemas.PrecioVentaCreate, db: Session = Depends(get_db)):
    # Desactivar precios anteriores para el mismo producto/receta
    db.query(models.PrecioVenta).filter(
        models.PrecioVenta.producto_id == precio.producto_id,
        models.PrecioVenta.receta_id == precio.receta_id,
        models.PrecioVenta.activo == True,
    ).update({"activo": False})

    db_precio = models.PrecioVenta(**precio.model_dump())
    db.add(db_precio)
    db.commit()
    db.refresh(db_precio)
    return db_precio


@router.patch("/{precio_id}/desactivar", response_model=schemas.PrecioVenta)
def desactivar_precio_venta(precio_id: int, db: Session = Depends(get_db)):
    precio = db.query(models.PrecioVenta).filter(models.PrecioVenta.id == precio_id).first()
    if not precio:
        raise HTTPException(status_code=404, detail="Precio de venta no encontrado")
    precio.activo = False
    db.commit()
    db.refresh(precio)
    return precio
