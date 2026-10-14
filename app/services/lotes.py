from typing import List
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas


def crear_lote(db: Session, lote_in: schemas.LoteProduccionCreate) -> models.LoteProduccion:
    """Crea un lote de produccion con sus productos e insumos."""
    lote = models.LoteProduccion(
        fecha=lote_in.fecha,
    )
    db.add(lote)
    db.flush()

    for producto in lote_in.productos:
        db.add(models.LoteProducto(
            lote_id=lote.id,
            producto_id=producto.producto_id,
            receta_id=producto.receta_id,
            cantidad=producto.cantidad,
        ))

    for insumo in lote_in.insumos:
        db.add(models.LoteInsumo(
            lote_id=lote.id,
            insumo_id=insumo.insumo_id,
            cantidad=insumo.cantidad,
        ))

    db.commit()
    db.refresh(lote)
    return lote


def cerrar_lote(db: Session, lote_id: int) -> models.LoteProduccion:
    """Cierra un lote de produccion, disparando el calculo automatico de costos."""
    lote = db.query(models.LoteProduccion).filter(models.LoteProduccion.id == lote_id).first()
    if not lote:
        raise ValueError(f"Lote con id {lote_id} no encontrado")
    if lote.estado == "CERRADO":
        raise ValueError("El lote ya esta cerrado")

    lote.estado = "CERRADO"
    db.commit()
    db.refresh(lote)
    return lote
