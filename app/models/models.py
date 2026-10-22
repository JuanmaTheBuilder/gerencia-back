from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UnidadMedida(Base):
    __tablename__ = "unidades_medida"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    abreviatura = Column(String(20), nullable=False, unique=True)

    insumos = relationship("Insumo", back_populates="unidad_medida")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    contacto = Column(String(200))
    telefono = Column(String(50))
    email = Column(String(100))
    direccion = Column(Text)

    insumos = relationship("Insumo", back_populates="proveedor")
    compras = relationship("Compra", back_populates="proveedor")


class Insumo(Base):
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=False)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    precio_compra = Column(Numeric(12, 2), nullable=False, default=0)
    stock_actual = Column(Numeric(12, 4), nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)

    unidad_medida = relationship("UnidadMedida", back_populates="insumos")
    proveedor = relationship("Proveedor", back_populates="insumos")
    recetas_insumos = relationship("RecetaInsumo", back_populates="insumo")
    compras_detalle = relationship("CompraDetalle", back_populates="insumo")
    lotes_insumos = relationship("LoteInsumo", back_populates="insumo")
    historial_precios = relationship("HistorialPrecioInsumo", back_populates="insumo")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)

    productos_recetas = relationship("ProductoReceta", back_populates="producto")
    lotes_productos = relationship("LoteProducto", back_populates="producto")
    costos_historicos = relationship("CostoHistorico", back_populates="producto")
    precios_venta = relationship("PrecioVenta", back_populates="producto")


class Receta(Base):
    __tablename__ = "recetas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False, default="1.0")
    activa = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, nullable=False, server_default=func.now())

    productos_recetas = relationship("ProductoReceta", back_populates="receta")
    recetas_insumos = relationship("RecetaInsumo", back_populates="receta")
    lotes_productos = relationship("LoteProducto", back_populates="receta")
    precios_venta = relationship("PrecioVenta", back_populates="receta")


class ProductoReceta(Base):
    __tablename__ = "productos_recetas"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    receta_id = Column(Integer, ForeignKey("recetas.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("producto_id", "receta_id", name="uix_producto_receta"),)

    producto = relationship("Producto", back_populates="productos_recetas")
    receta = relationship("Receta", back_populates="productos_recetas")


class RecetaInsumo(Base):
    __tablename__ = "recetas_insumos"

    id = Column(Integer, primary_key=True, index=True)
    receta_id = Column(Integer, ForeignKey("recetas.id", ondelete="CASCADE"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id", ondelete="CASCADE"), nullable=False)
    cantidad = Column(Numeric(12, 4), nullable=False)

    __table_args__ = (UniqueConstraint("receta_id", "insumo_id", name="uix_receta_insumo"),)

    receta = relationship("Receta", back_populates="recetas_insumos")
    insumo = relationship("Insumo", back_populates="recetas_insumos")


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    total = Column(Numeric(12, 2), nullable=False, default=0)

    proveedor = relationship("Proveedor", back_populates="compras")
    detalles = relationship("CompraDetalle", back_populates="compra")


class CompraDetalle(Base):
    __tablename__ = "compras_detalle"

    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Numeric(12, 4), nullable=False)
    precio_unitario = Column(Numeric(12, 4), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)

    compra = relationship("Compra", back_populates="detalles")
    insumo = relationship("Insumo", back_populates="compras_detalle")


class LoteProduccion(Base):
    __tablename__ = "lotes_produccion"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    estado = Column(String(50), nullable=False, default="ABIERTO")
    costo_real_total = Column(Numeric(12, 2), nullable=False, default=0)

    lotes_productos = relationship("LoteProducto", back_populates="lote")
    lotes_insumos = relationship("LoteInsumo", back_populates="lote")
    gastos_lotes = relationship("GastoLote", back_populates="lote")
    costos_historicos = relationship("CostoHistorico", back_populates="lote")


class LoteProducto(Base):
    __tablename__ = "lotes_productos"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes_produccion.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    receta_id = Column(Integer, ForeignKey("recetas.id"))
    cantidad = Column(Numeric(12, 4), nullable=False)

    lote = relationship("LoteProduccion", back_populates="lotes_productos")
    producto = relationship("Producto", back_populates="lotes_productos")
    receta = relationship("Receta", back_populates="lotes_productos")


class LoteInsumo(Base):
    __tablename__ = "lotes_insumos"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes_produccion.id", ondelete="CASCADE"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Numeric(12, 4), nullable=False)

    lote = relationship("LoteProduccion", back_populates="lotes_insumos")
    insumo = relationship("Insumo", back_populates="lotes_insumos")


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(100), nullable=False)
    descripcion = Column(Text)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(DateTime, nullable=False, server_default=func.now())

    gastos_lotes = relationship("GastoLote", back_populates="gasto")


class GastoLote(Base):
    __tablename__ = "gastos_lotes"

    id = Column(Integer, primary_key=True, index=True)
    gasto_id = Column(Integer, ForeignKey("gastos.id", ondelete="CASCADE"), nullable=False)
    lote_id = Column(Integer, ForeignKey("lotes_produccion.id", ondelete="CASCADE"), nullable=False)
    monto_asignado = Column(Numeric(12, 2), nullable=False)

    gasto = relationship("Gasto", back_populates="gastos_lotes")
    lote = relationship("LoteProduccion", back_populates="gastos_lotes")


class CostoHistorico(Base):
    __tablename__ = "costos_historicos"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes_produccion.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    cantidad_fabricada = Column(Numeric(12, 4), nullable=False)
    costo_total = Column(Numeric(12, 2), nullable=False)
    costo_unitario = Column(Numeric(12, 4), nullable=False)

    lote = relationship("LoteProduccion", back_populates="costos_historicos")
    producto = relationship("Producto", back_populates="costos_historicos")


class HistorialPrecioInsumo(Base):
    __tablename__ = "historial_precios_insumos"

    id = Column(Integer, primary_key=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id", ondelete="CASCADE"), nullable=False)
    precio = Column(Numeric(12, 4), nullable=False)
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="SET NULL"))

    insumo = relationship("Insumo", back_populates="historial_precios")
    compra = relationship("Compra")


class Recurso(Base):
    __tablename__ = "recursos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)
    periodicidad = Column(String(50), nullable=False, default="MENSUAL")
    es_fijo = Column(Boolean, nullable=False, default=True)
    monto = Column(Numeric(12, 2), nullable=False, default=0)
    descripcion = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)


class PrecioVenta(Base):
    __tablename__ = "precios_venta"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    receta_id = Column(Integer, ForeignKey("recetas.id", ondelete="CASCADE"), nullable=True)
    precio_con_iva = Column(Numeric(12, 2), nullable=False, default=0)
    iva_porcentaje = Column(Numeric(5, 2), nullable=False, default=19.00)
    fecha_inicio = Column(DateTime, nullable=False, server_default=func.now())
    activo = Column(Boolean, nullable=False, default=True)

    producto = relationship("Producto", back_populates="precios_venta")
    receta = relationship("Receta", back_populates="precios_venta")


class PuntoEquilibrio(Base):
    __tablename__ = "puntos_equilibrio"

    id = Column(Integer, primary_key=True, index=True)
    periodo_mes = Column(Integer, nullable=False)
    periodo_anio = Column(Integer, nullable=False)
    fecha_calculo = Column(DateTime, nullable=False, server_default=func.now())
    tasa_iva = Column(Numeric(5, 2), nullable=False, default=19.00)

    costos_fijos_mensuales = Column(Numeric(14, 2), nullable=False, default=0)
    inversion_inicial_total = Column(Numeric(14, 2), nullable=False, default=0)
    meta_unidades = Column(Numeric(12, 4), nullable=False, default=0)
    unidades_equilibrio = Column(Numeric(12, 4), nullable=False, default=0)
    ventas_equilibrio_pesos = Column(Numeric(14, 2), nullable=False, default=0)
    utilidad_estimada = Column(Numeric(14, 2), nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="MAL")
    diagnostico = Column(Text)

    detalles = relationship("PuntoEquilibrioDetalle", back_populates="punto_equilibrio", cascade="all, delete-orphan")


class PuntoEquilibrioDetalle(Base):
    __tablename__ = "puntos_equilibrio_detalle"

    id = Column(Integer, primary_key=True, index=True)
    punto_equilibrio_id = Column(Integer, ForeignKey("puntos_equilibrio.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    receta_id = Column(Integer, ForeignKey("recetas.id"), nullable=True)
    peso_venta = Column(Numeric(5, 4), nullable=False, default=0)
    precio_con_iva = Column(Numeric(12, 2), nullable=False, default=0)
    precio_sin_iva = Column(Numeric(12, 2), nullable=False, default=0)
    costo_variable_unitario = Column(Numeric(12, 4), nullable=False, default=0)
    margen_contribucion_unitario = Column(Numeric(12, 4), nullable=False, default=0)
    unidades_equilibrio = Column(Numeric(12, 4), nullable=False, default=0)

    punto_equilibrio = relationship("PuntoEquilibrio", back_populates="detalles")
    producto = relationship("Producto")
    receta = relationship("Receta")
