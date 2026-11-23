"""agrega planes de negocio y amplia precision de precio_compra

Revision ID: a1c4e9b27d10
Revises: 70b03f93814e
Create Date: 2026-11-23 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1c4e9b27d10'
down_revision: Union[str, None] = '70b03f93814e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VISTAS = ['v_recetas_costos', 'v_recetas_costo_total', 'v_evolucion_costos']  # orden de creacion


def _cambiar_precision(antes, despues) -> None:
    """Postgres no deja alterar una columna usada por vistas: se guardan, se borran y se recrean."""
    bind = op.get_bind()
    definiciones = {}
    for v in VISTAS:
        d = bind.execute(sa.text("SELECT pg_get_viewdef(to_regclass(:v), true)"), {"v": v}).scalar()
        if d:
            definiciones[v] = d
    for v in reversed(VISTAS):
        if v in definiciones:
            op.execute(f"DROP VIEW IF EXISTS {v}")
    op.alter_column('insumos', 'precio_compra', existing_type=antes, type_=despues, existing_nullable=False)
    for v in VISTAS:
        if v in definiciones:
            op.execute(f"CREATE VIEW {v} AS {definiciones[v]}")


def upgrade() -> None:
    op.create_table(
        'planes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('datos', sa.JSON(), nullable=False),
        sa.Column('creado', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('actualizado', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_planes_id'), 'planes', ['id'], unique=False)
    # El costo por gramo/ml necesita mas de 2 decimales
    _cambiar_precision(sa.Numeric(12, 2), sa.Numeric(14, 6))


def downgrade() -> None:
    _cambiar_precision(sa.Numeric(14, 6), sa.Numeric(12, 2))
    op.drop_index(op.f('ix_planes_id'), table_name='planes')
    op.drop_table('planes')
