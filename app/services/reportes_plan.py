"""Reporte del plan de negocio: Excel con el aspecto de la plantilla (con formulas) y PDF.

Los nombres de los estudiantes se dejan en blanco a proposito: se completan a mano al entregar.
"""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from app.domain.proyecciones.calculo import PlanDatos, calcular

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"

AZUL = PatternFill("solid", fgColor="CAEDFB")     # entradas
VERDE = PatternFill("solid", fgColor="D9F2D0")    # calculos
GRIS = PatternFill("solid", fgColor="D0D0D0")     # encabezados
GRIS2 = PatternFill("solid", fgColor="D8D8D8")    # totales
NAVY = PatternFill("solid", fgColor="0E2841")     # indicadores finales
NEGRITA = Font(bold=True)
BLANCA = Font(bold=True, color="FFFFFF")
FIN = Side(style="thin", color="999999")
BORDE = Border(left=FIN, right=FIN, top=FIN, bottom=FIN)
MONEDA = '#,##0;[Red]-#,##0'
PCT = '0.0%'


def generar(datos: PlanDatos, formato: str) -> tuple[bytes, str, str]:
    if formato == "pdf":
        return _pdf(datos), PDF, "pdf"
    return _xlsx(datos), XLSX, "xlsx"


# ---------------------------------------------------------------- Excel

class _Hoja:
    def __init__(self, ws):
        self.ws = ws

    def put(self, ref, valor, fill=None, fmt=None, bold=False, borde=True, white=False):
        c = self.ws[ref]
        c.value = valor
        if fill is not None:
            c.fill = fill
        if fmt:
            c.number_format = fmt
        if bold or white:
            c.font = BLANCA if white else NEGRITA
        if borde:
            c.border = BORDE
        return c

    def entrada(self, ref, valor, fmt=None):
        return self.put(ref, valor, AZUL, fmt)

    def calculo(self, ref, formula, fmt=MONEDA, fill=VERDE):
        return self.put(ref, formula, fill, fmt)

    def titulo(self, fila, texto, hasta=10):
        for col in range(1, hasta + 1):
            self.put(f"{L(col)}{fila}", None, GRIS)
        self.put(f"A{fila}", texto, GRIS, bold=True)


def _xlsx(d: PlanDatos) -> bytes:
    wb = Workbook()
    _hoja_proyecciones(wb.active, d)
    _hoja_nomina_adjunto(wb.create_sheet("Nómina (adjunto)"), d)
    _hoja_nomina_global(wb.create_sheet("Nomina global"), d)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _hoja_proyecciones(ws, d: PlanDatos):
    ws.title = "Proyecciones"
    h = _Hoja(ws)
    n = d.n_anios
    yc = [L(5 + t) for t in range(n)]          # columnas de los anos (E, F, ...)
    ult = yc[-1]
    ws.column_dimensions["A"].width = 46
    for col in "BCD":
        ws.column_dimensions[col].width = 16
    for c in yc:
        ws.column_dimensions[c].width = 16
    ws.column_dimensions[L(6 + n)].width = 36

    h.put("A1", "Empresa", GRIS, bold=True)
    ws.merge_cells(f"B1:{ult}1")
    h.entrada("B1", d.empresa)
    for i in range(2, 6):
        h.put(f"A{i}", "Nombre Completo Estudiante", GRIS, bold=True)
        ws.merge_cells(f"B{i}:F{i}")
        h.entrada(f"B{i}", None)
    h.put("A6", "Producto", GRIS, bold=True)
    ws.merge_cells("B6:F6")
    h.entrada("B6", d.producto)
    ws.merge_cells("G2:J6")
    h.put("G2", "Rellenar sólo campos en azul", None, bold=True)
    ws["G2"].alignment = Alignment(horizontal="center", vertical="center")

    # --- Inversiones ---
    r = 8
    h.put(f"A{r}", "INVERSIONES", VERDE, bold=True)
    fila_total_inv = r
    r += 1
    primera_inv = r
    for inv in d.inversiones:
        h.put(f"A{r}", (inv.categoria + (" - " + inv.concepto if inv.concepto else "")).upper() or "OTRO")
        h.entrada(f"B{r}", inv.valor, MONEDA)
        r += 1
    cap = r
    h.put(f"A{cap}", "CAPITAL DE TRABAJO", VERDE, bold=True)
    for col in "BCD":
        h.calculo(f"{col}{cap}", f"=SUM({col}{cap + 1}:{col}{cap + 2})")
    h.put(f"A{cap + 1}", "MANO DE OBRA")
    h.put(f"A{cap + 2}", "GASTOS DE ADMINISTRACIÓN Y VENTAS")
    for i, col in enumerate("BCD"):
        h.entrada(f"{col}{cap + 1}", d.capital_mano_obra[i], MONEDA)
        h.entrada(f"{col}{cap + 2}", d.capital_gastos[i], MONEDA)
        h.put(f"{col}{cap + 3}", f"Mes {i + 1}", GRIS, bold=True)
    h.put(f"E{cap + 1}", "Adjuntar la nómina", borde=False)
    h.put(f"E{cap + 2}", "Adjuntar la nómina", borde=False)
    h.calculo(f"B{fila_total_inv}", f"=SUM(B{primera_inv}:B{cap})+C{cap}+D{cap}", fill=VERDE)
    r = cap + 5

    # --- Demanda ---
    fila_crec = r
    h.put(f"A{r}", "Crecimiento del sector", GRIS, bold=True)
    for t in range(1, n):
        h.entrada(f"{yc[t]}{r}", d.crecimiento[t], PCT)
    r += 2
    h.put(f"A{r}", "Proyección de demanda", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    f_cant = r
    h.put(f"A{r}", "Cantidad")
    for t in range(n):
        h.entrada(f"{yc[t]}{r}", d.cantidad[t], MONEDA)
    r += 1
    f_precio = r
    h.put(f"A{r}", "Precio de venta")
    h.entrada(f"E{r}", d.precio_inicial, MONEDA)
    for t in range(1, n):
        h.calculo(f"{yc[t]}{r}", f"={yc[t - 1]}{r}*(1+{yc[t]}{fila_crec})")
    r += 1
    f_ing = r
    h.put(f"A{r}", "Total ingreso (cantidad x venta)")
    for t in range(n):
        h.calculo(f"{yc[t]}{r}", f"={yc[t]}{f_cant}*{yc[t]}{f_precio}")
    r += 1
    f_prov = r
    h.put(f"A{r}", "Provisión para deudas malas")
    h.entrada(f"B{r}", d.pct_provision, PCT)
    for t in range(n):
        h.calculo(f"{yc[t]}{r}", f"={yc[t]}{f_ing}*$B${r}")
    r += 1
    for etiqueta, pct in (("Ventas crédito", d.pct_credito), ("Ventas Contado", d.pct_contado)):
        h.put(f"A{r}", etiqueta)
        h.entrada(f"B{r}", pct, PCT)
        for t in range(n):
            h.calculo(f"{yc[t]}{r}", f"={yc[t]}{f_ing}*$B${r}")
        if etiqueta == "Ventas Contado":
            f_contado = r
        r += 1
    r += 1

    # --- Materia prima ---
    h.put(f"E{r}", "IPC", None, bold=True)
    r += 1
    f_ipc = r
    h.put(f"A{r}", "IPC (variación anual)")
    for t in range(1, n):
        h.entrada(f"{yc[t]}{r}", d.ipc[t], PCT)
    r += 1
    h.put(f"A{r}", "COSTO", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    h.put(f"A{r}", "Materia Prima", GRIS, bold=True)
    h.put(f"B{r}", "Gramos / ml", GRIS, bold=True)
    h.put(f"C{r}", "Costo (gr) Proveedor", GRIS, bold=True)
    h.put(f"D{r}", "Costo por UND", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", "Costo total MP", GRIS, bold=True)
    r += 1
    mp0 = r
    for m in d.materias_primas:
        h.put(f"A{r}", m.nombre, GRIS2)
        h.entrada(f"B{r}", m.cantidad, "#,##0.####")
        h.entrada(f"C{r}", m.costo_unitario, "#,##0.######")
        h.calculo(f"D{r}", f"=C{r}*B{r}", "#,##0.####")
        h.calculo(f"E{r}", f"=D{r}*$E${f_cant}")
        for t in range(1, n):
            h.calculo(f"{yc[t]}{r}", f"={yc[t - 1]}{r}*(1+{yc[t]}${f_ipc})")
        r += 1
    mp1 = r - 1
    f_mp = r
    h.put(f"A{r}", "TOTAL", GRIS2, bold=True)
    if d.materias_primas:
        h.calculo(f"B{r}", f"=SUM(B{mp0}:B{mp1})", "#,##0.####", GRIS2)
        h.calculo(f"D{r}", f"=SUM(D{mp0}:D{mp1})", "#,##0.####", GRIS2)
        for c in yc:
            h.calculo(f"{c}{r}", f"=SUM({c}{mp0}:{c}{mp1})", fill=GRIS2)
    else:
        for c in yc:
            h.calculo(f"{c}{r}", 0, fill=GRIS2)
    r += 1
    h.put(f"A{r}", "Margen Bruto ")
    for c in yc:
        h.calculo(f"{c}{r}", f'=IF({c}{f_ing}=0,"",({c}{f_ing}-{c}{f_mp})/{c}{f_ing})', PCT)
    r += 1
    f_pago_contado = r
    for etiqueta, pct in (("Pago Contado", d.pct_pago_contado), ("Pago Crédito", d.pct_pago_credito)):
        h.put(f"A{r}", etiqueta)
        h.entrada(f"B{r}", pct, PCT)
        for c in yc:
            h.calculo(f"{c}{r}", f"={c}{f_mp}*$B${r}")
        r += 1
    r += 1

    # --- Mano de obra ---
    h.put(f"A{r}", "COSTO DE VENTAS MANO DE OBRA", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    f_mo = r
    h.put(f"A{r}", "Mano de obra por producción")
    for t, c in enumerate(yc):
        if d.mano_obra is None:
            h.calculo(f"{c}{r}", f"={c}{f_mp}*5%")
        else:
            h.entrada(f"{c}{r}", d.mano_obra[t], MONEDA)
    r += 1
    f_mo_total = r
    h.put(f"A{r}", "TOTAL", GRIS2, bold=True)
    for c in yc:
        h.calculo(f"{c}{r}", f"=SUM({c}{f_mo})", fill=GRIS2)
    r += 2

    # --- CIF ---
    h.put(f"A{r}", "COSTOS INDIRECTOS DE FABRICACIÓN", GRIS, bold=True)
    for col, txt in zip("BCD", ("Consumo mes", "Costo", "Consumo año")):
        h.put(f"{col}{r}", txt, GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    c0 = r
    for ln in d.cif:
        h.put(f"A{r}", ln.nombre)
        h.entrada(f"B{r}", ln.consumo_mes, MONEDA)
        h.entrada(f"C{r}", ln.costo, MONEDA)
        h.entrada(f"D{r}", ln.consumo_anio, MONEDA)
        for t, c in enumerate(yc):
            h.entrada(f"{c}{r}", ln.valores[t], MONEDA)
        r += 1
    c1 = r - 1
    f_cif = r
    h.put(f"A{r}", "TOTAL", GRIS2, bold=True)
    for c in yc:
        h.calculo(f"{c}{r}", f"=SUM({c}{c0}:{c}{c1})" if d.cif else 0, fill=GRIS2)
    r += 2

    # --- Gastos de administracion y ventas ---
    h.put(f"A{r}", "GASTOS ADMINISTRACIÓN Y VENTAS", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    g0 = r
    for ln in d.gastos:
        h.put(f"A{r}", ln.nombre)
        for t, c in enumerate(yc):
            h.entrada(f"{c}{r}", ln.valores[t], MONEDA)
        nota = ("Soportar con la nómina" if ln.origen else ("Justificar: " + ln.justificacion if ln.justificacion else "Justificar:"))
        h.put(f"{L(6 + n)}{r}", nota, borde=False)
        r += 1
    g1 = r - 1
    f_gas = r
    h.put(f"A{r}", "TOTAL", GRIS2, bold=True)
    for c in yc:
        h.calculo(f"{c}{r}", f"=SUM({c}{g0}:{c}{g1})" if d.gastos else 0, fill=GRIS2)
    r += 3

    # --- Perdidas y ganancias ---
    h.put(f"A{r}", "ESTADOS FINANCIEROS: Perdidas y Ganancias", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    p_ventas = r
    h.put(f"A{r}", "Ventas")
    for c in yc:
        h.calculo(f"{c}{r}", f"=+{c}{f_ing}")
    r += 1
    p_cmv = r
    h.put(f"A{r}", "(-) Costo Mercancía Vendida")
    for c in yc:
        h.calculo(f"{c}{r}", f"=-{c}{f_mp}-{c}{f_mo_total}")
    r += 1
    p_ub = r
    h.put(f"A{r}", "(= ) Utilidad Bruta")
    for c in yc:
        h.calculo(f"{c}{r}", f"={c}{p_ventas}+{c}{p_cmv}")
    r += 1
    p_gas = r
    h.put(f"A{r}", "( -) Gastos Administración y Ventas")
    for c in yc:
        h.calculo(f"{c}{r}", f"=-{c}{f_gas}")
    r += 1
    p_prov = r
    h.put(f"A{r}", "( -) Gasto Provisión Deudas Malas")
    for c in yc:
        h.calculo(f"{c}{r}", f"=-{c}{f_prov}")
    r += 1
    p_uai = r
    h.put(f"A{r}", "( = ) Utilidad Antes de Impuestos UAI")
    for c in yc:
        h.calculo(f"{c}{r}", f"={c}{p_ub}+{c}{p_gas}+{c}{p_prov}")
    r += 1
    p_renta = r
    h.put(f"A{r}", "( -) Impuesto de Renta")
    h.entrada(f"B{r}", d.pct_renta, PCT)
    for c in yc:
        h.calculo(f"{c}{r}", f"=-{c}{p_uai}*$B${r}")
    r += 1
    p_un = r
    h.put(f"A{r}", "( = ) Utilidad Neta UN")
    for c in yc:
        h.calculo(f"{c}{r}", f"={c}{p_uai}+{c}{p_renta}")
    r += 1
    for etiqueta, pct in (("Reserva Legal", d.pct_reserva), ("Dividendos", d.pct_dividendos)):
        h.put(f"A{r}", etiqueta)
        h.entrada(f"B{r}", pct, PCT)
        for c in yc:
            h.calculo(f"{c}{r}", f"=-{c}{p_un}*$B${r}")
        r += 1
    h.put(f"A{r}", "U.Neta (después de reserva y dividendos)")
    for c in yc:
        h.calculo(f"{c}{r}", f"={c}{p_un}+{c}{r - 2}+{c}{r - 1}")
    r += 3

    # --- Flujo de caja ---
    h.put(f"A{r}", "PROYECCIÓN FLUJO DE CAJA", GRIS, bold=True)
    for t in range(n):
        h.put(f"{yc[t]}{r}", d.anio_inicial + t, GRIS, bold=True)
    r += 1
    h.put(f"A{r}", "INGRESOS", bold=True)
    r += 1
    k_cont = r
    h.put(f"A{r}", "Ventas de Contado")
    for c in yc:
        h.calculo(f"{c}{r}", f"=+{c}{f_contado}")
    r += 1
    k_ing = r
    h.put(f"A{r}", "TOTAL INGRESOS DEL AÑO", GRIS2, bold=True)
    for c in yc:
        h.calculo(f"{c}{r}", f"=+{c}{k_cont}", fill=GRIS2)
    r += 1
    h.put(f"A{r}", "EGRESOS", bold=True)
    r += 1
    e0 = r
    for etiqueta, formula in (
        ("Pago MP de contado", lambda c: f"=+{c}{f_pago_contado}"),
        ("Mano de Obra", lambda c: f"=+{c}{f_mo_total}"),
        ("CIF (Sin la depreciación)", lambda c: f"=+{c}{f_cif}"),
        ("Gastos de Administración y Ventas", lambda c: f"=+{c}{f_gas}"),
        ("Impuesto de Renta", lambda c: f"=-{c}{p_renta}"),
    ):
        h.put(f"A{r}", etiqueta)
        for c in yc:
            h.calculo(f"{c}{r}", formula(c))
        r += 1
    k_egr = r
    h.put(f"A{r}", "TOTAL EGRESOS DEL AÑO", GRIS2, bold=True)
    for c in yc:
        h.calculo(f"{c}{r}", f"=SUM({c}{e0}:{c}{r - 1})", fill=GRIS2)
    r += 1
    k_ef = r
    h.put(f"A{r}", "EFECTIVO GENERADO EN EL AÑO", GRIS2, bold=True)
    h.calculo(f"D{r}", f"=-B{fila_total_inv}", fill=GRIS2)
    for c in yc:
        h.calculo(f"{c}{r}", f"=+{c}{k_ing}-{c}{k_egr}", fill=GRIS2)
    r += 3

    # --- Evaluacion ---
    for col in "ABCD":
        h.put(f"{col}{r}", None, NAVY)
        h.put(f"{col}{r + 1}", None, NAVY)
        h.put(f"{col}{r + 2}", None, NAVY)
    h.put(f"A{r}", "TASA DE INTERES DE OPORTUNIDAD", NAVY, white=True)
    h.entrada(f"E{r}", d.tasa_oportunidad, PCT)
    h.put(f"F{r}", "Tasa del banco", borde=False)
    h.put(f"A{r + 1}", "TASA INTERNA DE RETORNO", NAVY, white=True)
    h.calculo(f"E{r + 1}", f'=IFERROR(IRR(D{k_ef}:{ult}{k_ef},E{r}),"No aplica")', '0.00%')
    h.put(f"A{r + 2}", "VALOR PRESENTE NETO", NAVY, white=True)
    h.calculo(f"E{r + 2}", f"=NPV(E{r},D{k_ef}:{ult}{k_ef})")
    ws.freeze_panes = "B8"


def _hoja_nomina_adjunto(ws, d: PlanDatos):
    h = _Hoja(ws)
    p = d.parametros_nomina
    ws.column_dimensions["A"].width = 26
    for col in "BCDE":
        ws.column_dimensions[col].width = 18
    h.put("A1", "NOMINA — costo legal de un empleado con salario mínimo", GRIS, bold=True)
    h.put("A3", "SALARIO MÍNIMO")
    h.entrada("B3", p.smlv, MONEDA)
    h.put("A4", "AUXILIO TRANSPORTE")
    h.entrada("B4", p.auxilio_transporte, MONEDA)
    h.calculo("B5", "=+B3+B4")
    h.put("A7", "PRESTACIONES", GRIS, bold=True)
    filas = [
        (8, "CESANTÍA", "=B5*C8", p.pct_cesantias, "Incluye auxilio"),
        (9, "PRIMA", "=B5*C9", p.pct_prima, "Incluye auxilio"),
        (10, "VACACIONES", "=B3*C10", p.pct_vacaciones, "No incluye auxilio"),
        (11, "INTERESES", "=B5*C11", p.pct_intereses, "1 % del devengado"),
    ]
    for fila, nombre, f, pct, nota in filas:
        h.put(f"A{fila}", nombre)
        h.calculo(f"B{fila}", f)
        h.entrada(f"C{fila}", pct, "0.00%")
        h.put(f"D{fila}", nota, borde=False)
    h.put("A13", "PARAFISCAL", GRIS, bold=True)
    for col, txt in zip("BCDE", ("EMPLEADO", "%", "EMPLEADOR", "%")):
        h.put(f"{col}13", txt, GRIS, bold=True)
    h.put("A14", "SALUD")
    h.calculo("B14", "=B3*C14"); h.entrada("C14", p.pct_salud_empleado, "0.00%")
    h.calculo("D14", "=B3*E14"); h.entrada("E14", p.pct_salud_empleador, "0.00%")
    h.put("A15", "PENSIÓN")
    h.calculo("B15", "=B3*C15"); h.entrada("C15", p.pct_pension_empleado, "0.00%")
    h.calculo("D15", "=B3*E15"); h.entrada("E15", p.pct_pension_empleador, "0.00%")
    h.put("A16", "ARL (riesgo III)")
    h.calculo("D16", "=B3*E16"); h.entrada("E16", p.arl.get("III", 0), "0.000%")
    for fila, nombre, pct in ((18, "CONFA", p.pct_caja), (19, "ICBF", 0), (20, "SENA", 0)):
        h.put(f"A{fila}", nombre)
        h.calculo(f"B{fila}", f"=B3*C{fila}")
        h.entrada(f"C{fila}", pct, "0.00%")
    h.put("D19", "Desde 10 SMLV", borde=False)
    h.put("D20", "Desde 10 SMLV", borde=False)
    h.put("H8", "NETO A PAGAR", GRIS, bold=True)
    h.calculo("I8", "=B3+B4-B14-B15")
    h.put("H10", "COSTO", GRIS, bold=True)
    h.calculo("I10", "=B3+B4+B8+B9+B10+B11+D14+D15+D16+B18")
    h.put("H11", "% CARGA", GRIS, bold=True)
    h.calculo("I11", "=I10/B5-1", "0.00%")
    ws.column_dimensions["H"].width = 16
    ws.column_dimensions["I"].width = 18


def _hoja_nomina_global(ws, d: PlanDatos):
    h = _Hoja(ws)
    p = d.parametros_nomina
    ws.column_dimensions["A"].width = 30
    for i in range(2, 17):
        ws.column_dimensions[L(i)].width = 16
    h.put("A1", "NOMINA GLOBAL", GRIS, bold=True)

    # Parametros (cada uno en su celda para que las formulas los referencien)
    h.titulo(3, "PARÁMETROS", 4)
    params = [
        ("SMLV", p.smlv, MONEDA), ("Auxilio de transporte", p.auxilio_transporte, MONEDA),
        ("Horas al mes", p.horas_mes, "0"),
        ("Recargo nocturno (x)", p.f_recargo_nocturno, "0.00"), ("Hora extra diurna (x)", p.f_extra_diurna, "0.00"),
        ("Hora extra nocturna (x)", p.f_extra_nocturna, "0.00"), ("Recargo festivo (x)", p.f_recargo_festivo, "0.00"),
        ("Extra diurna festiva (x)", p.f_extra_diurna_festiva, "0.00"),
        ("Extra nocturna festiva (x)", p.f_extra_nocturna_festiva, "0.00"),
        ("Salud empleado", p.pct_salud_empleado, "0.00%"), ("Pensión empleado", p.pct_pension_empleado, "0.00%"),
        ("Cesantías", p.pct_cesantias, "0.00%"), ("Prima", p.pct_prima, "0.00%"),
        ("Vacaciones", p.pct_vacaciones, "0.00%"), ("Intereses de cesantías", p.pct_intereses, "0.00%"),
        ("Salud empleador", p.pct_salud_empleador, "0.00%"), ("Pensión empleador", p.pct_pension_empleador, "0.00%"),
        ("Caja de compensación", p.pct_caja, "0.00%"), ("ICBF (desde 10 SMLV)", p.pct_icbf, "0.00%"),
        ("SENA (desde 10 SMLV)", p.pct_sena, "0.00%"),
    ]
    ref = {}
    r = 4
    for nombre, valor, fmt in params:
        h.put(f"A{r}", nombre)
        h.entrada(f"B{r}", valor, fmt)
        ref[nombre] = f"$B${r}"
        r += 1
    SM, AUX, HM = ref["SMLV"], ref["Auxilio de transporte"], ref["Horas al mes"]
    r += 1

    emps = d.empleados
    if not emps:
        h.put(f"A{r}", "Sin empleados registrados", borde=False)
        return

    # Bloque 1: datos y novedades
    h.titulo(r, "EMPLEADOS Y NOVEDADES (horas)", 13)
    r += 1
    cab = ["Empleado", "Área", "Salario", "Recargo nocturno", "Extra diurna", "Extra nocturna", "Recargo festivo",
           "Extra diurna festiva", "Extra nocturna festiva", "Comisiones", "Incapacidades", "Días laborados", "Riesgo ARL"]
    for i, t in enumerate(cab):
        h.put(f"{L(i + 1)}{r}", t, GRIS, bold=True)
        ws[f"{L(i + 1)}{r}"].alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    b1 = r
    for e in emps:
        h.entrada(f"A{r}", e.nombre)
        h.entrada(f"B{r}", e.area)
        h.entrada(f"C{r}", e.salario, MONEDA)
        for j, v in enumerate((e.h_recargo_nocturno, e.h_extra_diurna, e.h_extra_nocturna, e.h_recargo_festivo,
                               e.h_extra_diurna_festiva, e.h_extra_nocturna_festiva)):
            h.entrada(f"{L(4 + j)}{r}", v, "0.##")
        h.entrada(f"J{r}", e.comisiones, MONEDA)
        h.entrada(f"K{r}", e.incapacidades, MONEDA)
        h.entrada(f"L{r}", e.dias, "0.##")
        h.entrada(f"M{r}", p.arl.get(e.riesgo, 0), "0.000%")
        r += 1
    n_e = len(emps)
    r += 1

    # Bloque 2: valor de novedades
    h.titulo(r, "VALOR DE RECARGOS Y HORAS EXTRA", 10)
    r += 1
    cab = ["Empleado", "Salario", "Valor hora", "Recargo nocturno", "Extra diurna", "Extra nocturna",
           "Recargo festivo", "Extra diurna festiva", "Extra nocturna festiva", "Total horas extra"]
    for i, t in enumerate(cab):
        h.put(f"{L(i + 1)}{r}", t, GRIS, bold=True)
        ws[f"{L(i + 1)}{r}"].alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    b2 = r
    fx = [ref["Recargo nocturno (x)"], ref["Hora extra diurna (x)"], ref["Hora extra nocturna (x)"],
          ref["Recargo festivo (x)"], ref["Extra diurna festiva (x)"], ref["Extra nocturna festiva (x)"]]
    for i in range(n_e):
        s = b1 + i
        h.calculo(f"A{r}", f"=A{s}", None)
        h.calculo(f"B{r}", f"=C{s}")
        h.calculo(f"C{r}", f"=B{r}/{HM}")
        for j in range(6):
            h.calculo(f"{L(4 + j)}{r}", f"={L(4 + j)}{s}*$C{r}*{fx[j]}")
        h.calculo(f"J{r}", f"=SUM(D{r}:I{r})")
        r += 1
    r += 1

    # Bloque 3: devengado y deducciones
    h.titulo(r, "DEVENGADO, DEDUCCIONES Y NETO", 11)
    r += 1
    cab = ["Empleado", "Sueldo básico", "Días trabajados", "Incapacidades + horas extra", "Comisiones",
           "Auxilio de transporte", "Total devengado", "Aportes salud", "Aportes pensión", "Total deducciones",
           "NETO PAGADO"]
    for i, t in enumerate(cab):
        h.put(f"{L(i + 1)}{r}", t, GRIS, bold=True)
        ws[f"{L(i + 1)}{r}"].alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    b3 = r
    for i in range(n_e):
        s, v = b1 + i, b2 + i
        h.calculo(f"A{r}", f"=A{s}", None)
        h.calculo(f"B{r}", f"=C{s}")
        h.calculo(f"C{r}", f"=L{s}", "0.##")
        h.calculo(f"D{r}", f"=K{s}+J{v}")
        h.calculo(f"E{r}", f"=J{s}")
        h.calculo(f"F{r}", f"=IF(AND(B{r}>0,B{r}<={SM}*2),{AUX}/30*C{r},0)")
        h.calculo(f"G{r}", f"=B{r}/30*C{r}+D{r}+E{r}+F{r}")
        h.calculo(f"H{r}", f"=(G{r}-F{r})*{ref['Salud empleado']}")
        h.calculo(f"I{r}", f"=(G{r}-F{r})*{ref['Pensión empleado']}")
        h.calculo(f"J{r}", f"=SUM(H{r}:I{r})")
        h.calculo(f"K{r}", f"=G{r}-J{r}")
        r += 1
    h.put(f"A{r}", "TOTAL", GRIS2, bold=True)
    for col in "BCDEFGHIJK":
        h.calculo(f"{col}{r}", f"=SUM({col}{b3}:{col}{r - 1})", fill=GRIS2)
    r += 2

    # Bloque 4: provisiones
    h.titulo(r, "PROVISIÓN (carga del empleador)", 13)
    r += 1
    cab = ["Empleado", "Cesantías", "Prima", "Vacaciones", "Intereses cesantías", "Salud", "Pensión", "Caja Compen.",
           "I.C.B.F", "SENA", "Riesgos profesionales", "TOTAL APROP.", "Costo empleado"]
    for i, t in enumerate(cab):
        h.put(f"{L(i + 1)}{r}", t, GRIS, bold=True)
        ws[f"{L(i + 1)}{r}"].alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    b4 = r
    for i in range(n_e):
        s, g = b1 + i, b3 + i
        base = f"(G{g}-F{g})"
        h.calculo(f"A{r}", f"=A{s}", None)
        h.calculo(f"B{r}", f"=G{g}*{ref['Cesantías']}")
        h.calculo(f"C{r}", f"=G{g}*{ref['Prima']}")
        h.calculo(f"D{r}", f"={base}*{ref['Vacaciones']}")
        h.calculo(f"E{r}", f"=G{g}*{ref['Intereses de cesantías']}")
        h.calculo(f"F{r}", f"={base}*{ref['Salud empleador']}")
        h.calculo(f"G{r}", f"={base}*{ref['Pensión empleador']}")
        h.calculo(f"H{r}", f"={base}*{ref['Caja de compensación']}")
        h.calculo(f"I{r}", f"=IF(B{g}>={SM}*10,B{g}*{ref['ICBF (desde 10 SMLV)']},0)")
        h.calculo(f"J{r}", f"=IF(B{g}>={SM}*10,B{g}*{ref['SENA (desde 10 SMLV)']},0)")
        h.calculo(f"K{r}", f"={base}*M{s}")
        h.calculo(f"L{r}", f"=SUM(B{r}:K{r})")
        h.calculo(f"M{r}", f"=L{r}+G{g}")
        r += 1
    h.put(f"A{r}", "TOTALES", GRIS2, bold=True)
    for col in "BCDEFGHIJKLM":
        h.calculo(f"{col}{r}", f"=SUM({col}{b4}:{col}{r - 1})", fill=GRIS2)
    r += 2
    h.put(f"A{r}", "Costo mensual por área", GRIS, bold=True)
    r += 1
    for area, nombre in (("produccion", "Producción"), ("administracion", "Administración"), ("ventas", "Ventas")):
        h.put(f"A{r}", nombre)
        h.calculo(f"B{r}", f'=SUMIF($B${b1}:$B${b1 + n_e - 1},"{area}",$M${b4}:$M${b4 + n_e - 1})')
        r += 1


# ---------------------------------------------------------------- PDF

def _m(v) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", ".")


def _p(v) -> str:
    return "—" if v is None else f"{v * 100:.1f} %".replace(".", ",")


def _pdf(d: PlanDatos) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    r = calcular(d)
    n = d.n_anios
    anios = r["anios"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title=f"Plan de negocio y proyecciones - {d.empresa or d.producto}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=20, textColor=colors.HexColor("#0E2841"))
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, textColor=colors.HexColor("#0E2841"), spaceBefore=10)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9)
    cel = ParagraphStyle("c", parent=ss["BodyText"], fontSize=8, leading=9)
    GRISC, AZULC = colors.HexColor("#D0D0D0"), colors.HexColor("#CAEDFB")

    def tabla(cabecera, filas, anchos=None, resaltar=(), total=()):
        data = [cabecera] + filas
        t = Table(data, colWidths=anchos, repeatRows=1)
        est = [("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), GRISC),
               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
               ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
        for i in total:
            est += [("FONTNAME", (0, i + 1), (-1, i + 1), "Helvetica-Bold"), ("BACKGROUND", (0, i + 1), (-1, i + 1), colors.HexColor("#D9F2D0"))]
        t.setStyle(TableStyle(est))
        return t

    ya = ["Concepto"] + [str(a) for a in anios]
    ancho_c = [7 * cm] + [(27.7 * cm - 7 * cm) / n] * n
    el = []
    el.append(Paragraph("Plan de Negocio — Proyecciones", h1))
    el.append(Paragraph(f"<b>Empresa:</b> {d.empresa or '—'} &nbsp;&nbsp; <b>Producto:</b> {d.producto or '—'}", body))
    el.append(Spacer(1, 0.3 * cm))
    for _ in range(4):
        el.append(Paragraph("Nombre completo estudiante: ______________________________________________", body))
    el.append(Spacer(1, 0.4 * cm))

    ev = r["evaluacion"]
    el.append(Paragraph("Resumen de la evaluación", h2))
    el.append(tabla(["Indicador", "Valor"], [
        ["Inversión total", _m(r["inversion"]["total"])],
        ["Tasa de interés de oportunidad", _p(ev["tasa"])],
        ["Tasa interna de retorno (TIR)", _p(ev["tir"]) if ev["tir"] is not None else "No aplica"],
        ["Valor presente neto (VPN)", _m(ev["vpn"])],
    ], [9 * cm, 5 * cm]))

    el.append(Paragraph("Inversiones", h2))
    filas = [[(i.categoria + (" - " + i.concepto if i.concepto else "")) or "Otro", _m(i.valor)] for i in d.inversiones]
    filas.append(["Capital de trabajo (3 meses)", _m(sum(r["inversion"]["capital_trabajo_mes"]))])
    filas.append(["TOTAL INVERSIONES", _m(r["inversion"]["total"])])
    el.append(tabla(["Concepto", "Valor"], filas, [9 * cm, 5 * cm], total=[len(filas) - 1]))
    el.append(PageBreak())

    dm = r["demanda"]
    el.append(Paragraph("Proyección de demanda y cartera", h2))
    el.append(tabla(ya, [
        ["Cantidad"] + [_m(x) for x in dm["cantidad"]],
        ["Precio de venta"] + [_m(x) for x in dm["precio"]],
        ["Total ingreso"] + [_m(x) for x in dm["ingreso"]],
        [f"Provisión deudas malas ({_p(d.pct_provision)})"] + [_m(x) for x in dm["provision"]],
        [f"Ventas crédito ({_p(d.pct_credito)})"] + [_m(x) for x in dm["ventas_credito"]],
        [f"Ventas contado ({_p(d.pct_contado)})"] + [_m(x) for x in dm["ventas_contado"]],
    ], ancho_c, total=[2]))

    mp = r["materia_prima"]
    el.append(Paragraph("Costo de materia prima", h2))
    filas = [[l["nombre"] or "—"] + [_m(x) for x in l["valores"]] for l in mp["lineas"]]
    filas.append(["TOTAL"] + [_m(x) for x in mp["total"]])
    filas.append(["Margen bruto"] + [_p(x) for x in mp["margen_bruto"]])
    filas.append([f"Pago contado ({_p(d.pct_pago_contado)})"] + [_m(x) for x in mp["pago_contado"]])
    filas.append([f"Pago crédito ({_p(d.pct_pago_credito)})"] + [_m(x) for x in mp["pago_credito"]])
    el.append(tabla(ya, filas, ancho_c, total=[len(mp["lineas"])]))
    el.append(PageBreak())

    el.append(Paragraph("Mano de obra, CIF y gastos de administración y ventas", h2))
    filas = [["Mano de obra por producción"] + [_m(x) for x in r["mano_obra"]["valores"]]]
    filas += [["CIF — " + (l.nombre or "—")] + [_m(x) for x in l.valores] for l in d.cif]
    filas.append(["TOTAL CIF"] + [_m(x) for x in r["cif"]["total"]])
    filas += [["Gasto — " + (l.nombre or "—")] + [_m(x) for x in l.valores] for l in d.gastos]
    filas.append(["TOTAL GASTOS ADM. Y VENTAS"] + [_m(x) for x in r["gastos"]["total"]])
    totales = [len(d.cif) + 1, len(filas) - 1]
    el.append(tabla(ya, filas, ancho_c, total=totales))

    py = r["pyg"]
    el.append(Paragraph("Estado de pérdidas y ganancias", h2))
    filas = [
        ["Ventas", py["ventas"]], ["(-) Costo mercancía vendida", py["cmv"]], ["(=) Utilidad bruta", py["utilidad_bruta"]],
        ["(-) Gastos administración y ventas", py["gastos"]], ["(-) Provisión deudas malas", py["provision"]],
        ["(=) Utilidad antes de impuestos", py["uai"]], [f"(-) Impuesto de renta ({_p(d.pct_renta)})", py["renta"]],
        ["(=) Utilidad neta", py["utilidad_neta"]], [f"Reserva legal ({_p(d.pct_reserva)})", py["reserva"]],
        [f"Dividendos ({_p(d.pct_dividendos)})", py["dividendos"]], ["U. neta final", py["utilidad_final"]],
    ]
    el.append(tabla(ya, [[a] + [_m(x) for x in v] for a, v in filas], ancho_c, total=[2, 5, 7, 10]))
    el.append(PageBreak())

    fl = r["flujo"]
    el.append(Paragraph("Proyección del flujo de caja", h2))
    filas = [
        ["Ventas de contado", fl["ingresos"]], ["Pago MP de contado", fl["pago_mp_contado"]],
        ["Mano de obra", fl["mano_obra"]], ["CIF (sin depreciación)", fl["cif"]],
        ["Gastos de administración y ventas", fl["gastos"]], ["Impuesto de renta", fl["renta"]],
        ["TOTAL EGRESOS", fl["egresos"]], ["EFECTIVO GENERADO EN EL AÑO", fl["efectivo"]],
    ]
    el.append(tabla(ya, [[a] + [_m(x) for x in v] for a, v in filas], ancho_c, total=[6, 7]))

    nm = r["nomina"]
    if nm["empleados"]:
        el.append(Paragraph("Nómina (valores mensuales)", h2))
        cab = ["Empleado", "Área", "Devengado", "Deducciones", "Neto pagado", "Provisiones", "Costo empleado"]
        filas = [[Paragraph(e["nombre"], cel), e["area"], _m(e["devengado"]), _m(e["total_deducciones"]),
                  _m(e["neto_pagado"]), _m(e["total_provisiones"]), _m(e["costo_empleado"])] for e in nm["empleados"]]
        filas.append(["TOTAL", "", _m(nm["total_devengado"]), "", _m(nm["total_neto"]),
                      _m(nm["total_provisiones"]), _m(nm["costo_total_mensual"])])
        el.append(tabla(cab, filas, [7 * cm, 3 * cm] + [3.5 * cm] * 5, total=[len(filas) - 1]))

    obs = r["observaciones"]
    if obs:
        el.append(Paragraph("Observaciones del modelo", h2))
        for o in obs:
            el.append(Paragraph(f"<b>{o['titulo']}.</b> {o['texto']}", body))
    doc.build(el)
    return buf.getvalue()
