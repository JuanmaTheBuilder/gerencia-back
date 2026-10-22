from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas
from app.services.costos import calcular_costo_receta


REDONDEO = Decimal("0.0001")
REDONDEO_DINERO = Decimal("0.01")


IVA_POR_DEFECTO = Decimal("19.00")


def _precio_sin_iva(precio_con_iva: Decimal, tasa_iva: Decimal) -> Decimal:
    if tasa_iva <= 0:
        return precio_con_iva
    factor = Decimal("1") + (tasa_iva / Decimal("100"))
    return (precio_con_iva / factor).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)


def _obtener_precio_activo(db: Session, producto_id: int, receta_id: int = None) -> models.PrecioVenta:
    query = db.query(models.PrecioVenta).filter(
        models.PrecioVenta.producto_id == producto_id,
        models.PrecioVenta.activo == True
    )
    if receta_id:
        query = query.filter(models.PrecioVenta.receta_id == receta_id)
    return query.order_by(models.PrecioVenta.fecha_inicio.desc()).first()


def _obtener_receta_para_producto(db: Session, producto_id: int, receta_id: int = None) -> models.Receta:
    if receta_id:
        return db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    producto_receta = (
        db.query(models.ProductoReceta)
        .filter(models.ProductoReceta.producto_id == producto_id)
        .first()
    )
    if producto_receta:
        return producto_receta.receta
    return None


def _calcular_costos_fijos_mensuales(db: Session) -> Decimal:
    total = db.query(models.Recurso).filter(
        models.Recurso.periodicidad == "MENSUAL",
        models.Recurso.es_fijo == True,
        models.Recurso.activo == True
    ).all()
    return sum((r.monto for r in total), Decimal("0")).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)


def _calcular_inversion_inicial(db: Session) -> Decimal:
    total = db.query(models.Recurso).filter(
        models.Recurso.periodicidad == "UNICO",
        models.Recurso.activo == True
    ).all()
    return sum((r.monto for r in total), Decimal("0")).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)


def _generar_diagnostico(
    estado: str,
    costos_fijos: Decimal,
    inversion_inicial: Decimal,
    meta_unidades: Decimal,
    unidades_equilibrio: Decimal,
    utilidad: Decimal,
    detalles: List[Dict],
    recursos: List[models.Recurso]
) -> str:
    lineas = []

    if estado == "BIEN":
        lineas.append(
            f"Con tu meta de {meta_unidades} unidades mensuales estás por encima del punto de equilibrio "
            f"({unidades_equilibrio} unidades). Estimarías una utilidad de ${utilidad}."
        )
    else:
        faltante = unidades_equilibrio - meta_unidades
        lineas.append(
            f"Tu meta de {meta_unidades} unidades no alcanza. Necesitás vender {unidades_equilibrio} unidades "
            f"(te faltan {faltante}). Estimarías una pérdida de ${abs(utilidad)}."
        )

    # Recurso fijo más alto
    recursos_fijos = [r for r in recursos if r.periodicidad == "MENSUAL" and r.es_fijo and r.activo]
    if recursos_fijos:
        mayor = max(recursos_fijos, key=lambda r: r.monto)
        lineas.append(f"Tu costo fijo mensual más alto es {mayor.nombre} (${mayor.monto}).")

    # Producto con menor margen
    if detalles:
        menor_margen = min(detalles, key=lambda d: d["margen_contribucion_unitario"])
        lineas.append(
            f"El producto con menor margen de contribución es {menor_margen['producto_nombre']} "
            f"(${menor_margen['margen_contribucion_unitario']} por unidad)."
        )

    if inversion_inicial > 0:
        lineas.append(f"Tu inversión inicial estimada es de ${inversion_inicial}.")

    if estado == "MAL":
        lineas.append(
            "Sugerencias: revisá el precio de venta, buscá reducir el costo de los insumos principales, "
            "o ajustá la mezcla de productos para vender más del producto más rentable."
        )

    return " ".join(lineas)


def calcular_y_guardar_punto_equilibrio(
    db: Session,
    data: schemas.PuntoEquilibrioInput
) -> models.PuntoEquilibrio:
    if data.tasa_iva != IVA_POR_DEFECTO:
        raise ValueError("La tasa de IVA está fijada en 19%")
    tasa_iva = IVA_POR_DEFECTO

    costos_fijos = _calcular_costos_fijos_mensuales(db)
    inversion_inicial = _calcular_inversion_inicial(db)

    # Validar que la suma de pesos sea 1 (100%)
    peso_total = sum(p.peso_venta for p in data.productos)
    if not (Decimal("0.9999") <= peso_total <= Decimal("1.0001")):
        raise ValueError(f"La suma de los pesos de venta debe ser 1 (100%). Actual: {peso_total}")

    detalles_data = []
    precio_ponderado = Decimal("0")
    costo_variable_ponderado = Decimal("0")
    margen_ponderado = Decimal("0")

    for prod_input in data.productos:
        producto = db.query(models.Producto).filter(models.Producto.id == prod_input.producto_id).first()
        if not producto:
            raise ValueError(f"Producto con id {prod_input.producto_id} no encontrado")

        receta = _obtener_receta_para_producto(db, prod_input.producto_id, prod_input.receta_id)
        if not receta:
            raise ValueError(f"El producto {producto.nombre} no tiene una receta asociada")

        precio_venta = _obtener_precio_activo(db, prod_input.producto_id, receta.id)
        if not precio_venta:
            raise ValueError(f"El producto {producto.nombre} no tiene un precio de venta activo")

        precio_con_iva = precio_venta.precio_con_iva
        precio_sin_iva = _precio_sin_iva(precio_con_iva, tasa_iva)

        costo_receta = calcular_costo_receta(db, receta.id)
        costo_variable = costo_receta["costo_total_estimado"]
        margen = (precio_sin_iva - costo_variable).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)

        detalles_data.append({
            "producto_id": producto.id,
            "receta_id": receta.id,
            "producto_nombre": producto.nombre,
            "peso_venta": prod_input.peso_venta,
            "precio_con_iva": precio_con_iva,
            "precio_sin_iva": precio_sin_iva,
            "costo_variable_unitario": costo_variable,
            "margen_contribucion_unitario": margen,
        })

        precio_ponderado += precio_sin_iva * prod_input.peso_venta
        costo_variable_ponderado += costo_variable * prod_input.peso_venta
        margen_ponderado += margen * prod_input.peso_venta

    precio_ponderado = precio_ponderado.quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)
    costo_variable_ponderado = costo_variable_ponderado.quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)
    margen_ponderado = margen_ponderado.quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)

    if margen_ponderado <= 0:
        raise ValueError(
            "El margen de contribución ponderado es menor o igual a cero. "
            "Revisá los precios de venta o los costos de los insumos."
        )

    unidades_equilibrio = (costos_fijos / margen_ponderado).quantize(Decimal("1"), rounding=ROUND_CEILING)
    ventas_equilibrio = (unidades_equilibrio * precio_ponderado).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)
    utilidad_estimada = (data.meta_unidades * margen_ponderado - costos_fijos).quantize(REDONDEO_DINERO, rounding=ROUND_HALF_UP)
    estado = "BIEN" if utilidad_estimada >= 0 else "MAL"

    # Calcular unidades desagregadas por producto
    for det in detalles_data:
        det["unidades_equilibrio"] = (unidades_equilibrio * det["peso_venta"]).quantize(REDONDEO, rounding=ROUND_HALF_UP)

    recursos = db.query(models.Recurso).filter(models.Recurso.activo == True).all()
    diagnostico = _generar_diagnostico(
        estado, costos_fijos, inversion_inicial, data.meta_unidades,
        unidades_equilibrio, utilidad_estimada, detalles_data, recursos
    )

    # Guardar en base de datos
    punto = models.PuntoEquilibrio(
        periodo_mes=data.periodo_mes,
        periodo_anio=data.periodo_anio,
        tasa_iva=tasa_iva,
        costos_fijos_mensuales=costos_fijos,
        inversion_inicial_total=inversion_inicial,
        meta_unidades=data.meta_unidades,
        unidades_equilibrio=unidades_equilibrio,
        ventas_equilibrio_pesos=ventas_equilibrio,
        utilidad_estimada=utilidad_estimada,
        estado=estado,
        diagnostico=diagnostico,
    )
    db.add(punto)
    db.flush()

    for det in detalles_data:
        db_detalle = models.PuntoEquilibrioDetalle(
            punto_equilibrio_id=punto.id,
            producto_id=det["producto_id"],
            receta_id=det["receta_id"],
            peso_venta=det["peso_venta"],
            precio_con_iva=det["precio_con_iva"],
            precio_sin_iva=det["precio_sin_iva"],
            costo_variable_unitario=det["costo_variable_unitario"],
            margen_contribucion_unitario=det["margen_contribucion_unitario"],
            unidades_equilibrio=det["unidades_equilibrio"],
        )
        db.add(db_detalle)

    db.commit()
    db.refresh(punto)
    return punto
