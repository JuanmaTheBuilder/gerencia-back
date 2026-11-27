"""Liquidacion de nomina. Replica las formulas de la hoja 'Nomina global' de la plantilla.

Diferencia deliberada con el Excel: cada empleado usa sus propios datos (en el Excel hay
referencias desalineadas entre filas). Decisiones acordadas: salud patronal 8,5 % para todos
e intereses de cesantias = 1 % del devengado.

ICBF y SENA se cobran a todos los empleados, como en el Excel. Solo la exoneracion legal
(art. 114-1 E.T.: empleadores exonerados y salarios menores de 10 SMLV) los deja en cero,
y solo si el plan la activa con `exonerar_parafiscales`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Area = Literal["produccion", "administracion", "ventas"]


class ParametrosNomina(BaseModel):
    smlv: float = 1_423_500
    auxilio_transporte: float = 200_000
    horas_mes: float = 240
    # Factores de la plantilla (fila 25 de 'Nomina global')
    f_recargo_nocturno: float = 0.35
    f_extra_diurna: float = 1.25
    f_extra_nocturna: float = 1.75
    f_recargo_festivo: float = 0.75
    f_extra_diurna_festiva: float = 2.0
    f_extra_nocturna_festiva: float = 2.5
    # Porcentajes
    pct_salud_empleado: float = 0.04
    pct_pension_empleado: float = 0.04
    pct_cesantias: float = 0.0833
    pct_prima: float = 0.0833
    pct_vacaciones: float = 0.0417
    pct_intereses: float = 0.01
    pct_salud_empleador: float = 0.085
    pct_pension_empleador: float = 0.12
    pct_caja: float = 0.04
    pct_icbf: float = 0.03
    pct_sena: float = 0.02
    # Exoneracion de ICBF y SENA para salarios menores de 10 SMLV (art. 114-1 E.T.). Apagada por defecto.
    exonerar_parafiscales: bool = False
    # ARL por nivel de riesgo (I a III vienen de la plantilla; IV y V son las tarifas legales)
    arl: dict[str, float] = Field(
        default_factory=lambda: {"I": 0.00522, "II": 0.01044, "III": 0.02436, "IV": 0.0435, "V": 0.0696}
    )


class Empleado(BaseModel):
    nombre: str = "Empleado"
    area: Area = "produccion"
    salario: float = 0
    dias: float = 30
    incapacidades: float = 0
    comisiones: float = 0
    riesgo: str = "III"
    h_recargo_nocturno: float = 0
    h_extra_diurna: float = 0
    h_extra_nocturna: float = 0
    h_recargo_festivo: float = 0
    h_extra_diurna_festiva: float = 0
    h_extra_nocturna_festiva: float = 0


def liquidar_empleado(e: Empleado, p: ParametrosNomina) -> dict:
    valor_hora = e.salario / p.horas_mes if p.horas_mes else 0.0
    extras = {
        "recargo_nocturno": e.h_recargo_nocturno * valor_hora * p.f_recargo_nocturno,
        "extra_diurna": e.h_extra_diurna * valor_hora * p.f_extra_diurna,
        "extra_nocturna": e.h_extra_nocturna * valor_hora * p.f_extra_nocturna,
        "recargo_festivo": e.h_recargo_festivo * valor_hora * p.f_recargo_festivo,
        "extra_diurna_festiva": e.h_extra_diurna_festiva * valor_hora * p.f_extra_diurna_festiva,
        "extra_nocturna_festiva": e.h_extra_nocturna_festiva * valor_hora * p.f_extra_nocturna_festiva,
    }
    total_extras = sum(extras.values())

    # Auxilio de transporte: solo si 0 < salario <= 2 SMLV, proporcional a los dias
    aplica_aux = 0 < e.salario <= p.smlv * 2
    auxilio = p.auxilio_transporte / 30 * e.dias if aplica_aux else 0.0
    # En la plantilla la columna 'Incapacidades' recibe el valor de horas extra
    devengado = e.salario / 30 * e.dias + e.incapacidades + total_extras + e.comisiones + auxilio
    base = devengado - auxilio  # base de aportes (sin auxilio)

    salud_emp = base * p.pct_salud_empleado
    pension_emp = base * p.pct_pension_empleado
    deducciones = salud_emp + pension_emp

    # ICBF y SENA: se cobran sobre la base de aportes, salvo exoneracion (salario < 10 SMLV)
    exonerado = p.exonerar_parafiscales and e.salario < p.smlv * 10
    prov = {
        "cesantias": devengado * p.pct_cesantias,
        "prima": devengado * p.pct_prima,
        "vacaciones": base * p.pct_vacaciones,
        "intereses_cesantias": devengado * p.pct_intereses,
        "salud": base * p.pct_salud_empleador,
        "pension": base * p.pct_pension_empleador,
        "caja": base * p.pct_caja,
        "icbf": 0.0 if exonerado else base * p.pct_icbf,
        "sena": 0.0 if exonerado else base * p.pct_sena,
        "arl": base * p.arl.get(e.riesgo, 0.0),
    }
    total_prov = sum(prov.values())
    return {
        "nombre": e.nombre,
        "area": e.area,
        "salario": e.salario,
        "dias": e.dias,
        "valor_hora": valor_hora,
        "extras": extras,
        "total_extras": total_extras,
        "devengado": devengado,
        "auxilio": auxilio,
        "salud_empleado": salud_emp,
        "pension_empleado": pension_emp,
        "total_deducciones": deducciones,
        "neto_pagado": devengado - deducciones,
        "provisiones": prov,
        "total_provisiones": total_prov,
        "costo_empleado": devengado + total_prov,
    }


def liquidar_nomina(empleados: list[Empleado], p: ParametrosNomina) -> dict:
    filas = [liquidar_empleado(e, p) for e in empleados]
    por_area = {a: 0.0 for a in ("produccion", "administracion", "ventas")}
    for f in filas:
        por_area[f["area"]] += f["costo_empleado"]
    return {
        "empleados": filas,
        "total_devengado": sum(f["devengado"] for f in filas),
        "total_neto": sum(f["neto_pagado"] for f in filas),
        "total_provisiones": sum(f["total_provisiones"] for f in filas),
        "costo_total_mensual": sum(f["costo_empleado"] for f in filas),
        "costo_mensual_por_area": por_area,
    }


def costo_empleado_minimo(p: ParametrosNomina, riesgo: str = "III") -> dict:
    """Equivalente a la hoja 'Nomina (adjunto)': costo legal de un empleado con SMLV."""
    r = liquidar_empleado(Empleado(nombre="Salario minimo", salario=p.smlv, riesgo=riesgo), p)
    r["porcentaje_carga"] = r["costo_empleado"] / (p.smlv + p.auxilio_transporte) - 1 if p.smlv else 0.0
    return r
