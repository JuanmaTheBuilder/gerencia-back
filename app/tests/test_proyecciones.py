"""Pruebas del motor de calculo. Los valores esperados se verificaron recalculando la plantilla
original de Excel con los mismos datos (TIR, VPN, inversion y utilidades coinciden)."""
import pytest

from app.domain.proyecciones.calculo import (
    Inversion, LineaAnual, MateriaPrima, PlanDatos, calcular, irr,
)
from app.domain.proyecciones.nomina import Empleado, ParametrosNomina, liquidar_empleado


def plan_base() -> PlanDatos:
    return PlanDatos(
        inversiones=[Inversion(valor=v) for v in [1e6, 2e6, 3e5, 0, 4e5, 5e5]],
        capital_mano_obra=[1e5, 2e5, 3e5], capital_gastos=[5e4, 1e5, 1.5e5],
        crecimiento=[0, .05, .04, .06, .05, .05], ipc=[0, .04, .03, .05, .04, .04],
        cantidad=[1000, 1100, 1250, 1400, 1500, 1600], precio_inicial=8000, pct_provision=.02,
        materias_primas=[MateriaPrima(nombre="Fruta", cantidad=100, costo_unitario=.01),
                         MateriaPrima(nombre="Azucar", cantidad=80, costo_unitario=.004),
                         MateriaPrima(nombre="Pectinas", cantidad=5, costo_unitario=.05)],
        mano_obra=[40000 * 1.04 ** t for t in range(6)],
        cif=[LineaAnual(valores=[50000 * (1 + .03 * t) for t in range(6)]),
             LineaAnual(valores=[20000 * (1 + .02 * t) for t in range(6)])],
        gastos=[LineaAnual(valores=[300000 * (1 + .05 * t) for t in range(6)]),
                LineaAnual(valores=[80000] * 6), LineaAnual(valores=[40000] * 6)],
        pct_renta=.35, pct_reserva=.1, pct_dividendos=.3,
    )


def test_coincide_con_plantilla():
    r = calcular(plan_base())
    assert r["inversion"]["total"] == pytest.approx(5_100_000)
    assert r["evaluacion"]["tir"] == pytest.approx(0.5847844860545928, rel=1e-9)
    assert r["evaluacion"]["vpn"] == pytest.approx(8994815.34995158, rel=1e-9)


def test_costo_mp_solo_crece_con_ipc_como_la_plantilla():
    r = calcular(plan_base())
    mp = r["materia_prima"]["total"]
    assert mp[0] == pytest.approx((100 * .01 + 80 * .004 + 5 * .05) * 1000)
    assert mp[1] == pytest.approx(mp[0] * 1.04)


def test_mano_obra_por_defecto_es_5_por_ciento_de_mp():
    d = plan_base()
    d.mano_obra = None
    r = calcular(d)
    assert r["mano_obra"]["valores"][0] == pytest.approx(r["materia_prima"]["total"][0] * 0.05)


def test_sin_ventas_no_falla():
    r = calcular(PlanDatos())
    assert r["materia_prima"]["margen_bruto"][0] is None
    assert r["evaluacion"]["tir"] is None
    assert any(o["titulo"] == "Sin ventas" for o in r["observaciones"])


def test_perdida_genera_impuesto_negativo_como_la_plantilla():
    d = PlanDatos(cantidad=[10] * 6, precio_inicial=100, pct_renta=.35,
                  gastos=[LineaAnual(valores=[5000] * 6)])
    r = calcular(d)
    assert r["pyg"]["uai"][0] < 0
    assert r["pyg"]["renta"][0] > 0
    assert any(o["titulo"] == "Años con pérdida" for o in r["observaciones"])


def test_irr_sin_cambio_de_signo():
    assert irr([100, 50, 50]) is None
    assert irr([-100, 60, 60]) == pytest.approx(0.1306623863, rel=1e-6)


def test_nomina_empleado_minimo():
    p = ParametrosNomina()
    r = liquidar_empleado(Empleado(salario=p.smlv, riesgo="III"), p)
    assert r["auxilio"] == pytest.approx(200_000)
    assert r["devengado"] == pytest.approx(p.smlv + 200_000)
    assert r["total_deducciones"] == pytest.approx(p.smlv * .08)
    # ICBF y SENA se cobran tambien a salarios bajos (como en el Excel), sobre la base sin auxilio
    assert r["provisiones"]["icbf"] == pytest.approx(p.smlv * .03)
    assert r["provisiones"]["sena"] == pytest.approx(p.smlv * .02)


def test_icbf_sena_exoneracion_solo_menores_de_10_smlv():
    p = ParametrosNomina(exonerar_parafiscales=True)
    bajo = liquidar_empleado(Empleado(salario=p.smlv * 3), p)
    alto = liquidar_empleado(Empleado(salario=p.smlv * 10, riesgo="I"), p)
    assert bajo["provisiones"]["icbf"] == 0 and bajo["provisiones"]["sena"] == 0
    assert alto["provisiones"]["icbf"] == pytest.approx(p.smlv * 10 * .03)
    assert alto["provisiones"]["sena"] == pytest.approx(p.smlv * 10 * .02)


def test_nomina_con_novedades_e_icbf_sena_desde_10_smlv():
    p = ParametrosNomina()
    r = liquidar_empleado(Empleado(salario=15_000_000, dias=30, comisiones=500_000, riesgo="I"), p)
    assert r["auxilio"] == 0
    base = r["devengado"]  # base de aportes = devengado sin auxilio (incluye comisiones), como el Excel
    assert r["provisiones"]["icbf"] == pytest.approx(base * .03)
    assert r["provisiones"]["sena"] == pytest.approx(base * .02)
    assert r["costo_empleado"] == pytest.approx(r["devengado"] + r["total_provisiones"])


def test_nomina_del_excel_mani_aburra():
    """Los 5 empleados de la plantilla (hoja 'Nomina global'): total 17.516.888,87 y por area."""
    p = ParametrosNomina(smlv=1_750_905, auxilio_transporte=249_095, horas_mes=240,
                         pct_vacaciones=0.0416, pct_cesantias=0.0833, pct_prima=0.0833)
    emps = [
        Empleado(nombre="Operario", area="produccion", salario=2_000_000, riesgo="III"),
        Empleado(nombre="Administrador", area="administracion", salario=2_800_000, riesgo="I"),
        Empleado(nombre="Encargado ventas", area="ventas", salario=2_200_000, riesgo="I"),
        Empleado(nombre="Auxiliar 1", area="produccion", salario=1_750_905, riesgo="III"),
        Empleado(nombre="Auxiliar 2", area="produccion", salario=1_750_905, riesgo="III"),
    ]
    from app.domain.proyecciones.nomina import liquidar_nomina
    nm = liquidar_nomina(emps, p)
    assert nm["costo_total_mensual"] == pytest.approx(17_516_888.87, abs=0.05)
    assert nm["costo_mensual_por_area"]["produccion"] == pytest.approx(9_338_618.52, abs=0.05)
    assert nm["costo_mensual_por_area"]["administracion"] == pytest.approx(4_544_661.18, abs=0.05)
    assert nm["costo_mensual_por_area"]["ventas"] == pytest.approx(3_633_609.18, abs=0.05)


def test_reportes_se_generan():
    from app.services.reportes_plan import generar
    d = plan_base()
    d.empleados = [Empleado(nombre="Operario", salario=1_423_500), Empleado(nombre="Gerente", area="administracion", salario=15_000_000)]
    xlsx, media, ext = generar(d, "xlsx")
    assert xlsx[:2] == b"PK" and ext == "xlsx"
    pdf, media, ext = generar(d, "pdf")
    assert pdf[:4] == b"%PDF" and ext == "pdf"
