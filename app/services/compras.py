from typing import List
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas


def crear_compra(db: Session, compra_in: schemas.CompraCreate) -> models.Compra:
    """Crea una compra con sus detalles y registra el historial de precios de cada insumo."""
    compra = models.Compra(
        proveedor_id=compra_in.proveedor_id,
        fecha=compra_in.fecha,
    )
    db.add(compra)
    db.flush()  # Obtener el id de la compra sin commit

    for detalle in compra_in.detalles:
        db.add(models.CompraDetalle(
            compra_id=compra.id,
            insumo_id=detalle.insumo_id,
            cantidad=detalle.cantidad,
            precio_unitario=detalle.precio_unitario,
        ))
        # Registrar precio en historial
        db.add(models.HistorialPrecioInsumo(
            insumo_id=detalle.insumo_id,
            precio=detalle.precio_unitario,
            compra_id=compra.id,
        ))

    db.commit()
    db.refresh(compra)
    return compra
