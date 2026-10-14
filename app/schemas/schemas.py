from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# Unidades de medida
# =====================================================

class UnidadMedidaBase(BaseSchema):
    nombre: str = Field(..., max_length=100)
    abreviatura: str = Field(..., max_length=20)


class UnidadMedidaCreate(UnidadMedidaBase):
    pass


class UnidadMedidaUpdate(BaseSchema):
    nombre: Optional[str] = Field(None, max_length=100)
    abreviatura: Optional[str] = Field(None, max_length=20)


class UnidadMedida(UnidadMedidaBase):
    id: int


# =====================================================
# Proveedores
# =====================================================

class ProveedorBase(BaseSchema):
    nombre: str = Field(..., max_length=200)
    contacto: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    direccion: Optional[str] = None


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(BaseSchema):
    nombre: Optional[str] = Field(None, max_length=200)
    contacto: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    direccion: Optional[str] = None


class Proveedor(ProveedorBase):
    id: int


# =====================================================
# Historial de precios de insumos
# =====================================================

class HistorialPrecioInsumoBase(BaseSchema):
    precio: Decimal = Field(..., ge=0, decimal_places=4)
    fecha: Optional[datetime] = None
    compra_id: Optional[int] = None


class HistorialPrecioInsumoCreate(HistorialPrecioInsumoBase):
    insumo_id: int


class HistorialPrecioInsumo(HistorialPrecioInsumoBase):
    id: int
    insumo_id: int


# =====================================================
# Insumos
# =====================================================

class InsumoBase(BaseSchema):
    nombre: str = Field(..., max_length=200)
    unidad_medida_id: int
    proveedor_id: Optional[int] = None
    precio_compra: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    stock_actual: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    activo: bool = True


class InsumoCreate(InsumoBase):
    pass


class InsumoUpdate(BaseSchema):
    nombre: Optional[str] = Field(None, max_length=200)
    unidad_medida_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    precio_compra: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    stock_actual: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    activo: Optional[bool] = None


class Insumo(InsumoBase):
    id: int
    unidad_medida: Optional[UnidadMedida] = None
    proveedor: Optional[Proveedor] = None


class InsumoDetail(Insumo):
    historial_precios: List[HistorialPrecioInsumo] = []


# =====================================================
# Productos
# =====================================================

class ProductoBase(BaseSchema):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    activo: bool = True


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseSchema):
    nombre: Optional[str] = Field(None, max_length=200)
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


class Producto(ProductoBase):
    id: int


# =====================================================
# Recetas
# =====================================================

class RecetaInsumoBase(BaseSchema):
    insumo_id: int
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)


class RecetaInsumoCreate(RecetaInsumoBase):
    pass


class RecetaInsumoUpdate(BaseSchema):
    cantidad: Optional[Decimal] = Field(None, gt=0, decimal_places=4)


class RecetaInsumo(RecetaInsumoBase):
    id: int
    receta_id: int
    insumo: Optional[Insumo] = None


class RecetaBase(BaseSchema):
    nombre: str = Field(..., max_length=200)
    version: str = Field(default="1.0", max_length=50)
    activa: bool = True


class RecetaCreate(RecetaBase):
    insumos: List[RecetaInsumoCreate] = []


class RecetaUpdate(BaseSchema):
    nombre: Optional[str] = Field(None, max_length=200)
    version: Optional[str] = Field(None, max_length=50)
    activa: Optional[bool] = None


class Receta(RecetaBase):
    id: int
    fecha_creacion: datetime


class RecetaDetail(Receta):
    recetas_insumos: List[RecetaInsumo] = []
    productos_recetas: List[Producto] = []


# =====================================================
# Productos - Recetas
# =====================================================

class ProductoRecetaCreate(BaseSchema):
    producto_id: int
    receta_id: int


class ProductoReceta(ProductoRecetaCreate):
    id: int


# =====================================================
# Compras
# =====================================================

class CompraDetalleBase(BaseSchema):
    insumo_id: int
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    precio_unitario: Decimal = Field(..., ge=0, decimal_places=4)


class CompraDetalleCreate(CompraDetalleBase):
    pass


class CompraDetalle(CompraDetalleBase):
    id: int
    compra_id: int
    subtotal: Decimal
    insumo: Optional[Insumo] = None


class CompraBase(BaseSchema):
    proveedor_id: Optional[int] = None
    fecha: Optional[datetime] = None


class CompraCreate(CompraBase):
    detalles: List[CompraDetalleCreate] = []


class CompraUpdate(BaseSchema):
    proveedor_id: Optional[int] = None
    fecha: Optional[datetime] = None


class Compra(CompraBase):
    id: int
    total: Decimal
    detalles: List[CompraDetalle] = []
    proveedor: Optional[Proveedor] = None


# =====================================================
# Lotes de produccion
# =====================================================

class LoteProductoBase(BaseSchema):
    producto_id: int
    receta_id: Optional[int] = None
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)


class LoteProductoCreate(LoteProductoBase):
    pass


class LoteProducto(LoteProductoBase):
    id: int
    lote_id: int
    producto: Optional[Producto] = None
    receta: Optional[Receta] = None


class LoteInsumoBase(BaseSchema):
    insumo_id: int
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)


class LoteInsumoCreate(LoteInsumoBase):
    pass


class LoteInsumo(LoteInsumoBase):
    id: int
    lote_id: int
    insumo: Optional[Insumo] = None


class LoteProduccionBase(BaseSchema):
    fecha: Optional[datetime] = None


class LoteProduccionCreate(LoteProduccionBase):
    productos: List[LoteProductoCreate] = []
    insumos: List[LoteInsumoCreate] = []


class LoteProduccionUpdate(BaseSchema):
    estado: Optional[str] = Field(None, pattern="^(ABIERTO|CERRADO)$")


class LoteProduccion(LoteProduccionBase):
    id: int
    estado: str
    costo_real_total: Decimal


class LoteProduccionDetail(LoteProduccion):
    productos: List[LoteProducto] = []
    insumos: List[LoteInsumo] = []


# =====================================================
# Gastos
# =====================================================

class GastoBase(BaseSchema):
    categoria: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    monto: Decimal = Field(..., ge=0, decimal_places=2)
    fecha: Optional[datetime] = None


class GastoCreate(GastoBase):
    pass


class GastoUpdate(BaseSchema):
    categoria: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    monto: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    fecha: Optional[datetime] = None


class Gasto(GastoBase):
    id: int


class GastoLoteBase(BaseSchema):
    gasto_id: int
    lote_id: int
    monto_asignado: Decimal = Field(..., ge=0, decimal_places=2)


class GastoLoteCreate(GastoLoteBase):
    pass


class GastoLote(GastoLoteBase):
    id: int
    gasto: Optional[Gasto] = None


# =====================================================
# Costos historicos
# =====================================================

class CostoHistoricoBase(BaseSchema):
    lote_id: int
    producto_id: int
    cantidad_fabricada: Decimal
    costo_total: Decimal
    costo_unitario: Decimal


class CostoHistorico(CostoHistoricoBase):
    id: int
    fecha: datetime
    producto: Optional[Producto] = None
    lote: Optional[LoteProduccion] = None


# =====================================================
# Reportes y calculos
# =====================================================

class CostoEstimadoReceta(BaseSchema):
    receta_id: int
    receta_nombre: str
    producto_id: int
    producto_nombre: str
    costo_total_estimado: Decimal
    insumos: List[dict] = []


class CostoPorProducto(BaseSchema):
    producto_id: int
    producto_nombre: str
    cantidad_total_fabricada: Decimal
    costo_total_acumulado: Decimal
    costo_unitario_promedio: Decimal


class ComparacionEstimadoReal(BaseSchema):
    receta_id: int
    receta_nombre: str
    producto_id: int
    producto_nombre: str
    costo_estimado: Decimal
    costo_real_promedio: Decimal
    diferencia: Decimal


# =====================================================
# Respuestas genericas
# =====================================================

class MessageResponse(BaseSchema):
    message: str


class ErrorResponse(BaseSchema):
    detail: str
