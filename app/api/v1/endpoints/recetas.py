from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services.costos import calcular_costo_receta

router = APIRouter(prefix="/recetas", tags=["recetas"])


@router.get("/", response_model=List[schemas.Receta])
def listar_recetas(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    activa: bool = None,
):
    query = db.query(models.Receta)
    if activa is not None:
        query = query.filter(models.Receta.activa == activa)
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.RecetaDetail, status_code=status.HTTP_201_CREATED)
def crear_receta(receta: schemas.RecetaCreate, db: Session = Depends(get_db)):
    db_receta = models.Receta(
        nombre=receta.nombre,
        version=receta.version,
        activa=receta.activa,
    )
    db.add(db_receta)
    db.flush()

    for insumo in receta.insumos:
        db.add(models.RecetaInsumo(
            receta_id=db_receta.id,
            insumo_id=insumo.insumo_id,
            cantidad=insumo.cantidad,
        ))

    db.commit()
    db.refresh(db_receta)
    return db_receta


@router.get("/{receta_id}", response_model=schemas.RecetaDetail)
def obtener_receta(receta_id: int, db: Session = Depends(get_db)):
    receta = db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return receta


@router.patch("/{receta_id}", response_model=schemas.Receta)
def actualizar_receta(
    receta_id: int,
    receta_in: schemas.RecetaUpdate,
    db: Session = Depends(get_db),
):
    receta = db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    for key, value in receta_in.model_dump(exclude_unset=True).items():
        setattr(receta, key, value)
    db.commit()
    db.refresh(receta)
    return receta


@router.delete("/{receta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_receta(receta_id: int, db: Session = Depends(get_db)):
    receta = db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    db.delete(receta)
    db.commit()
    return None


@router.post("/{receta_id}/insumos", response_model=schemas.RecetaInsumo, status_code=status.HTTP_201_CREATED)
def agregar_insumo_a_receta(
    receta_id: int,
    insumo_in: schemas.RecetaInsumoCreate,
    db: Session = Depends(get_db),
):
    receta = db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    db_ri = models.RecetaInsumo(
        receta_id=receta_id,
        insumo_id=insumo_in.insumo_id,
        cantidad=insumo_in.cantidad,
    )
    db.add(db_ri)
    db.commit()
    db.refresh(db_ri)
    return db_ri


@router.patch("/{receta_id}/insumos/{receta_insumo_id}", response_model=schemas.RecetaInsumo)
def actualizar_insumo_receta(
    receta_id: int,
    receta_insumo_id: int,
    insumo_in: schemas.RecetaInsumoUpdate,
    db: Session = Depends(get_db),
):
    ri = db.query(models.RecetaInsumo).filter(
        models.RecetaInsumo.id == receta_insumo_id,
        models.RecetaInsumo.receta_id == receta_id,
    ).first()
    if not ri:
        raise HTTPException(status_code=404, detail="Insumo de receta no encontrado")
    for key, value in insumo_in.model_dump(exclude_unset=True).items():
        setattr(ri, key, value)
    db.commit()
    db.refresh(ri)
    return ri


@router.delete("/{receta_id}/insumos/{receta_insumo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_insumo_receta(
    receta_id: int,
    receta_insumo_id: int,
    db: Session = Depends(get_db),
):
    ri = db.query(models.RecetaInsumo).filter(
        models.RecetaInsumo.id == receta_insumo_id,
        models.RecetaInsumo.receta_id == receta_id,
    ).first()
    if not ri:
        raise HTTPException(status_code=404, detail="Insumo de receta no encontrado")
    db.delete(ri)
    db.commit()
    return None


@router.get("/{receta_id}/costo-estimado")
def costo_estimado_receta(receta_id: int, db: Session = Depends(get_db)):
    try:
        return calcular_costo_receta(db, receta_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{receta_id}/productos/{producto_id}", response_model=schemas.ProductoReceta, status_code=status.HTTP_201_CREATED)
def asociar_receta_a_producto(
    receta_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
):
    receta = db.query(models.Receta).filter(models.Receta.id == receta_id).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    existente = (
        db.query(models.ProductoReceta)
        .filter(
            models.ProductoReceta.receta_id == receta_id,
            models.ProductoReceta.producto_id == producto_id,
        )
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="La receta ya esta asociada a este producto")

    db_pr = models.ProductoReceta(receta_id=receta_id, producto_id=producto_id)
    db.add(db_pr)
    db.commit()
    db.refresh(db_pr)
    return db_pr
