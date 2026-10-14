from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import models


REDONDEO = Decimal("0.0001")
REDONDEO_DINERO = Decimal("0.01")


def calcular_costo_receta(db: Session, receta_id: int) -> Dict:
    """Calcula el costo estimado de una receta segun los precios actuales de los insumos."""
    receta = db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    if not receta:
        raise ValueError(f"Receta con id {receta_id} no encontrada")

    producto_receta = (
        db.query(models.ProductoReceta)
        .filter(models.ProductoReceta.receta_id == receta_id)
        .first()
    )
    producto_nombre = "Sin producto asociado"
    producto_id = None
    if producto_receta and producto_receta.producto:
        producto_nombre = producto_receta.producto.nombre
        producto_id = producto_receta.producto.id

    insumos = (
        db.query(models.RecetaInsumo, models.Insumo)
        .join(models.Insumo, models.RecetaInsumo.insumo_id == models.Insumo.id)
        .filter(models.RecetaInsumo.receta_id == receta_id)
        .all()
    )

    costo_total = Decimal("0")
    detalle_insumos = []

    for ri, insumo in insumos:
        costo_insumo = (ri.cantidad * insumo.precio_compra).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)
        costo_total += costo_insumo
        detalle_insumos.append({
            "insumo_id": insumo.id,
            "insumo_nombre": insumo.nombre,
            "cantidad": ri.cantidad,
            "unidad": insumo.unidad_medida.abreviatura if insumo.unidad_medida else None,
            "precio_unitario": insumo.precio_compra,
            "costo_insumo": costo_insumo,
        })

    return {
        "receta_id": receta.id,
        "receta_nombre": receta.nombre,
        "producto_id": producto_id,
        "producto_nombre": producto_nombre,
        "costo_total_estimado": costo_total.quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP),
        "insumos": detalle_insumos,
    }


def calcular_costos_por_producto(db: Session) -> List[Dict]:
    """Resumen de costos historicos por producto."""
    resultados = (
        db.query(
            models.CostoHistorico.producto_id,
            models.Producto.nombre,
            func.sum(models.CostoHistorico.cantidad_fabricada).label("cantidad_total"),
            func.sum(models.CostoHistorico.costo_total).label("costo_total"),
        )
        .join(models.Producto, models.CostoHistorico.producto_id == models.Producto.id)
        .group_by(models.CostoHistorico.producto_id, models.Producto.nombre)
        .all()
    )

    reporte = []
    for row in resultados:
        cantidad = Decimal(row.cantidad_total or 0)
        costo = Decimal(row.costo_total or 0)
        unitario = (costo / cantidad).quantize(REDONDEO, rounding=ROUND_HALF_UP) if cantidad > 0 else Decimal("0")
        reporte.append({
            "producto_id": row.producto_id,
            "producto_nombre": row.nombre,
            "cantidad_total_fabricada": cantidad,
            "costo_total_acumulado": costo.quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP),
            "costo_unitario_promedio": unitario,
        })
    return reporte


def comparar_estimado_vs_real(db: Session) -> List[Dict]:
    """Compara el costo estimado de cada receta con el costo real promedio historico."""
    recetas = db.query(models.Receta).all()
    resultado = []

    for receta in recetas:
        costo_estimado_dict = calcular_costo_receta(db, receta.id)
        producto_id = costo_estimado_dict["producto_id"]

        if not producto_id:
            continue

        historico = (
            db.query(func.avg(models.CostoHistorico.costo_unitario).label("promedio_real"))
            .filter(models.CostoHistorico.producto_id == producto_id)
            .first()
        )

        costo_real = Decimal(historico.promedio_real or 0)
        costo_estimado = costo_estimado_dict["costo_total_estimado"]
        diferencia = costo_real - costo_estimado

        resultado.append({
            "receta_id": receta.id,
            "receta_nombre": receta.nombre,
            "producto_id": producto_id,
            "producto_nombre": costo_estimado_dict["producto_nombre"],
            "costo_estimado": costo_estimado,
            "costo_real_promedio": costo_real.quantize(REDONDEO, rounding=ROUND_HALF_UP),
            "diferencia": diferencia.quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP),
        })

    return resultado
