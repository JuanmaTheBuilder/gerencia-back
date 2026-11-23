"""Plan de negocio y proyecciones. Replica las formulas de la hoja 'Proyecciones' de la plantilla.

Se conservan a proposito los comportamientos de la plantilla (ver `observaciones`).
Indice 0 = primer ano (2025 en la plantilla); el ano 0 del flujo es la inversion.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .nomina import Empleado, ParametrosNomina, liquidar_nomina, costo_empleado_minimo

N_ANIOS_DEFECTO = 6


class Inversion(BaseModel):
    categoria: str = ""
    concepto: str = ""
    valor: float = 0


class MateriaPrima(BaseModel):
    nombre: str = ""
    cantidad: float = 0        # gramos o ml por unidad (columna B)
    costo_unitario: float = 0  # costo por gramo/ml del proveedor (columna C)


class LineaAnual(BaseModel):
    """Renglon con un valor por ano (CIF, gastos de administracion y ventas)."""
    nombre: str = ""
    justificacion: str = ""
    consumo_mes: float = 0
    costo: float = 0
    consumo_anio: float = 0
    valores: list[float] = Field(default_factory=list)
    origen: Optional[str] = None  # p.ej. "nomina"


class PlanDatos(BaseModel):
    empresa: str = ""
    producto: str = ""
    anio_inicial: int = 2025
    n_anios: int = N_ANIOS_DEFECTO

    inversiones: list[Inversion] = Field(default_factory=list)
    capital_mano_obra: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    capital_gastos: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])

    crecimiento: list[float] = Field(default_factory=list)  # por ano; el primero no se usa
    ipc: list[float] = Field(default_factory=list)
    cantidad: list[float] = Field(default_factory=list)
    precio_inicial: float = 0
    pct_provision: float = 0
    pct_credito: float = 0.3
    pct_contado: float = 0.7

    materias_primas: list[MateriaPrima] = Field(default_factory=list)
    pct_pago_contado: float = 0.3
    pct_pago_credito: float = 0.7

    # None = 5 % de la materia prima, como en la plantilla
    mano_obra: Optional[list[float]] = None
    cif: list[LineaAnual] = Field(default_factory=list)
    gastos: list[LineaAnual] = Field(default_factory=list)

    pct_renta: float = 0
    pct_reserva: float = 0
    pct_dividendos: float = 0
    tasa_oportunidad: float = 0.12

    parametros_nomina: ParametrosNomina = Field(default_factory=ParametrosNomina)
    empleados: list[Empleado] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ajustar_longitudes(self):
        n = self.n_anios

        def ajustar(v: list[float]) -> list[float]:
            return (list(v) + [0.0] * n)[:n]

        self.crecimiento = ajustar(self.crecimiento)
        self.ipc = ajustar(self.ipc)
        self.cantidad = ajustar(self.cantidad)
        if self.mano_obra is not None:
            self.mano_obra = ajustar(self.mano_obra)
        for linea in [*self.cif, *self.gastos]:
            linea.valores = ajustar(linea.valores)
        self.capital_mano_obra = (list(self.capital_mano_obra) + [0.0] * 3)[:3]
        self.capital_gastos = (list(self.capital_gastos) + [0.0] * 3)[:3]
        return self


def _div(a: float, b: float) -> Optional[float]:
    return a / b if b else None


def irr(flujos: list[float], guess: float = 0.1) -> Optional[float]:
    """TIR como la funcion IRR de Excel. None si no tiene solucion."""
    if not (any(f > 0 for f in flujos) and any(f < 0 for f in flujos)):
        return None

    def f(r: float) -> float:
        return sum(c / (1 + r) ** i for i, c in enumerate(flujos))

    lo, hi = -0.999999, 1.0
    f_lo, f_hi = f(lo), f(hi)
    while f_lo * f_hi > 0 and hi < 1e6:
        hi *= 2
        f_hi = f(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def npv_excel(tasa: float, flujos: list[float]) -> float:
    """NPV de Excel: el primer valor se descuenta un periodo (igual que la plantilla)."""
    return sum(v / (1 + tasa) ** (i + 1) for i, v in enumerate(flujos))


def calcular(d: PlanDatos) -> dict:
    n = d.n_anios
    anios = [d.anio_inicial + i for i in range(n)]

    # --- Nomina ---
    nomina = liquidar_nomina(d.empleados, d.parametros_nomina)
    nomina["referencia_minimo"] = costo_empleado_minimo(d.parametros_nomina)

    # --- Demanda e ingresos ---
    precio: list[float] = []
    for t in range(n):
        precio.append(d.precio_inicial if t == 0 else precio[t - 1] * (1 + d.crecimiento[t]))
    ingreso = [d.cantidad[t] * precio[t] for t in range(n)]
    provision = [x * d.pct_provision for x in ingreso]
    ventas_credito = [x * d.pct_credito for x in ingreso]
    ventas_contado = [x * d.pct_contado for x in ingreso]

    # --- Materia prima ---
    mp_lineas = []
    for m in d.materias_primas:
        costo_und = m.costo_unitario * m.cantidad
        serie: list[float] = []
        for t in range(n):
            serie.append(costo_und * d.cantidad[0] if t == 0 else serie[t - 1] * (1 + d.ipc[t]))
        mp_lineas.append({"nombre": m.nombre, "cantidad": m.cantidad, "costo_unitario": m.costo_unitario,
                          "costo_por_und": costo_und, "valores": serie})
    mp_total = [sum(l["valores"][t] for l in mp_lineas) for t in range(n)]
    mp_cantidad_total = sum(l["cantidad"] for l in mp_lineas)
    mp_costo_und_total = sum(l["costo_por_und"] for l in mp_lineas)
    margen_bruto = [_div(ingreso[t] - mp_total[t], ingreso[t]) for t in range(n)]
    pago_mp_contado = [x * d.pct_pago_contado for x in mp_total]
    pago_mp_credito = [x * d.pct_pago_credito for x in mp_total]

    # --- Mano de obra, CIF, gastos ---
    mo = d.mano_obra if d.mano_obra is not None else [x * 0.05 for x in mp_total]
    cif_total = [sum(l.valores[t] for l in d.cif) for t in range(n)]
    gastos_total = [sum(l.valores[t] for l in d.gastos) for t in range(n)]

    # --- Inversion ---
    inv_activos = sum(i.valor for i in d.inversiones)
    capital_mes = [d.capital_mano_obra[i] + d.capital_gastos[i] for i in range(3)]
    inversion_total = inv_activos + sum(capital_mes)

    # --- Perdidas y ganancias ---
    cmv = [-mp_total[t] - mo[t] for t in range(n)]
    utilidad_bruta = [ingreso[t] + cmv[t] for t in range(n)]
    gastos_pyg = [-g for g in gastos_total]
    prov_pyg = [-p for p in provision]
    uai = [utilidad_bruta[t] + gastos_pyg[t] + prov_pyg[t] for t in range(n)]
    renta = [-u * d.pct_renta for u in uai]
    utilidad_neta = [uai[t] + renta[t] for t in range(n)]
    reserva = [-u * d.pct_reserva for u in utilidad_neta]
    dividendos = [-u * d.pct_dividendos for u in utilidad_neta]
    utilidad_final = [utilidad_neta[t] + reserva[t] + dividendos[t] for t in range(n)]

    # --- Flujo de caja ---
    ingresos_caja = ventas_contado
    egresos = [pago_mp_contado[t] + mo[t] + cif_total[t] + gastos_total[t] - renta[t] for t in range(n)]
    efectivo = [ingresos_caja[t] - egresos[t] for t in range(n)]
    flujo = [-inversion_total] + efectivo

    tir = irr(flujo, d.tasa_oportunidad)
    vpn = npv_excel(d.tasa_oportunidad, flujo)

    return {
        "anios": anios,
        "inversion": {"activos": inv_activos, "capital_trabajo_mes": capital_mes, "total": inversion_total},
        "demanda": {"cantidad": d.cantidad, "precio": precio, "ingreso": ingreso, "provision": provision,
                    "ventas_credito": ventas_credito, "ventas_contado": ventas_contado},
        "materia_prima": {"lineas": mp_lineas, "total": mp_total, "cantidad_total": mp_cantidad_total,
                          "costo_und_total": mp_costo_und_total, "margen_bruto": margen_bruto,
                          "pago_contado": pago_mp_contado, "pago_credito": pago_mp_credito},
        "mano_obra": {"valores": mo, "manual": d.mano_obra is not None},
        "cif": {"total": cif_total},
        "gastos": {"total": gastos_total},
        "pyg": {"ventas": ingreso, "cmv": cmv, "utilidad_bruta": utilidad_bruta, "gastos": gastos_pyg,
                "provision": prov_pyg, "uai": uai, "renta": renta, "utilidad_neta": utilidad_neta,
                "reserva": reserva, "dividendos": dividendos, "utilidad_final": utilidad_final},
        "flujo": {"ingresos": ingresos_caja, "pago_mp_contado": pago_mp_contado, "mano_obra": mo,
                  "cif": cif_total, "gastos": gastos_total, "renta": [-r for r in renta],
                  "egresos": egresos, "efectivo": efectivo, "serie": flujo},
        "evaluacion": {"tasa": d.tasa_oportunidad, "tir": tir, "vpn": vpn},
        "nomina": nomina,
        "observaciones": observaciones(d, ingreso, uai, tir),
    }


def observaciones(d: PlanDatos, ingreso: list[float], uai: list[float], tir: Optional[float]) -> list[dict]:
    """Avisos informativos. No cambian ningun numero: describen como funciona la plantilla."""
    obs: list[dict] = []
    if len(set(d.cantidad)) > 1:
        obs.append({"nivel": "info", "titulo": "Costo de materia prima",
                    "texto": "Desde el segundo año el costo de materia prima solo sube con el IPC, "
                             "no con la cantidad vendida (así lo calcula la plantilla). "
                             "Si la demanda crece, el margen bruto se infla."})
    if any(l.valores[t] for l in d.cif for t in range(d.n_anios)):
        obs.append({"nivel": "info", "titulo": "CIF fuera del estado de resultados",
                    "texto": "Los costos indirectos de fabricación entran al flujo de caja pero no al "
                             "estado de pérdidas y ganancias, como en la plantilla."})
    if d.pct_credito > 0:
        obs.append({"nivel": "info", "titulo": "Cartera sin cobrar",
                    "texto": "El flujo de caja solo cuenta ventas de contado y pagos de contado a proveedores; "
                             "las ventas y compras a crédito nunca se cobran ni se pagan."})
    obs.append({"nivel": "info", "titulo": "VPN",
                "texto": "El VPN usa NPV de Excel sobre el año 0 y los años proyectados, por lo que la inversión "
                         "inicial se descuenta un periodo (igual que la plantilla)."})
    if abs(d.pct_credito + d.pct_contado - 1) > 1e-9:
        obs.append({"nivel": "alerta", "titulo": "Ventas crédito + contado",
                    "texto": "Los porcentajes de venta a crédito y de contado no suman 100 %."})
    if abs(d.pct_pago_credito + d.pct_pago_contado - 1) > 1e-9:
        obs.append({"nivel": "alerta", "titulo": "Pago a proveedores",
                    "texto": "Los porcentajes de pago de contado y a crédito no suman 100 %."})
    perdidas = [d.anio_inicial + t for t, u in enumerate(uai) if u < 0]
    if perdidas:
        obs.append({"nivel": "alerta", "titulo": "Años con pérdida",
                    "texto": f"Hay pérdida antes de impuestos en {', '.join(map(str, perdidas))}. "
                             "La plantilla calcula un impuesto negativo (que entra como ingreso) en esos años."})
    if sum(ingreso) == 0:
        obs.append({"nivel": "alerta", "titulo": "Sin ventas",
                    "texto": "Cantidad o precio en cero: los indicadores no son significativos."})
    if tir is None:
        obs.append({"nivel": "alerta", "titulo": "TIR",
                    "texto": "La TIR no aplica: el flujo no cambia de signo."})
    return obs
