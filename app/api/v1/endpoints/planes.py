from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.proyecciones.calculo import PlanDatos, calcular
from app.domain.proyecciones.plantilla import plan_nuevo
from app.models import models
from app.services import reportes_plan

router = APIRouter(prefix="/planes", tags=["planes"])


class PlanCrear(BaseModel):
    nombre: str
    empresa: str = ""
    producto: str = ""


class PlanResumen(BaseModel):
    id: int
    nombre: str
    model_config = {"from_attributes": True}


class PlanOut(PlanResumen):
    datos: PlanDatos


class PlanActualizar(BaseModel):
    nombre: Optional[str] = None
    datos: PlanDatos


def _get(db: Session, plan_id: int) -> models.Plan:
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan


@router.get("/", response_model=List[PlanResumen])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Plan).order_by(models.Plan.id.desc()).all()


@router.post("/", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def crear(body: PlanCrear, db: Session = Depends(get_db)):
    datos = plan_nuevo(body.empresa, body.producto)
    plan = models.Plan(nombre=body.nombre, datos=datos.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return PlanOut(id=plan.id, nombre=plan.nombre, datos=PlanDatos(**plan.datos))


@router.post("/calcular")
def calcular_sin_guardar(datos: PlanDatos):
    """Recalcula en vivo sin guardar (la pantalla lo usa mientras se edita)."""
    return calcular(datos)


@router.get("/{plan_id}", response_model=PlanOut)
def obtener(plan_id: int, db: Session = Depends(get_db)):
    plan = _get(db, plan_id)
    return PlanOut(id=plan.id, nombre=plan.nombre, datos=PlanDatos(**plan.datos))


@router.put("/{plan_id}", response_model=PlanOut)
def actualizar(plan_id: int, body: PlanActualizar, db: Session = Depends(get_db)):
    plan = _get(db, plan_id)
    plan.datos = body.datos.model_dump()
    if body.nombre:
        plan.nombre = body.nombre
    db.commit()
    db.refresh(plan)
    return PlanOut(id=plan.id, nombre=plan.nombre, datos=PlanDatos(**plan.datos))


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(plan_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, plan_id))
    db.commit()


@router.get("/{plan_id}/resultados")
def resultados(plan_id: int, db: Session = Depends(get_db)):
    return calcular(PlanDatos(**_get(db, plan_id).datos))


@router.get("/{plan_id}/reporte")
def reporte(plan_id: int, formato: str = Query("xlsx", pattern="^(xlsx|pdf)$"), db: Session = Depends(get_db)):
    plan = _get(db, plan_id)
    datos = PlanDatos(**plan.datos)
    contenido, media, ext = reportes_plan.generar(datos, formato)
    nombre = "".join(c if c.isalnum() or c in "-_" else "_" for c in plan.nombre) or "plan"
    return Response(content=contenido, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="Plan_{nombre}.{ext}"'})
