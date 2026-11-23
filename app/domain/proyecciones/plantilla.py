"""Plan nuevo con los renglones que trae la plantilla de Excel."""
from .calculo import Inversion, LineaAnual, MateriaPrima, PlanDatos

CATEGORIAS_INVERSION = [
    "Edificaciones", "Maquinaria y equipo", "Muebles y enseres", "Vehículos",
    "Equipos de cómputo y telecomunicaciones", "Diferidos",
]
INSUMOS_PLANTILLA = ["Fruta", "Azúcar", "Pectinas", "Acidulante", "Jugo", "Panela", "Caramelo"]
CIF_PLANTILLA = ["Energía eléctrica", "Agua", "Teléfono"]
GASTOS_PLANTILLA = [("Nómina administración", "nomina_administracion"), ("Nómina ventas", "nomina_ventas"),
                    ("Publicidad", None), ("Comisiones ventas", None)]


def plan_nuevo(empresa: str = "", producto: str = "") -> PlanDatos:
    return PlanDatos(
        empresa=empresa, producto=producto,
        inversiones=[Inversion(categoria=c) for c in CATEGORIAS_INVERSION],
        materias_primas=[MateriaPrima(nombre=n) for n in INSUMOS_PLANTILLA],
        cif=[LineaAnual(nombre=n) for n in CIF_PLANTILLA],
        gastos=[LineaAnual(nombre=n, origen=o) for n, o in GASTOS_PLANTILLA],
        pct_renta=0.35, pct_reserva=0.1, pct_dividendos=0.3,
    )
