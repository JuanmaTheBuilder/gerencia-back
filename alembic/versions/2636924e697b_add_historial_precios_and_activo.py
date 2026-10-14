"""add_historial_precios_and_activo

Revision ID: 2636924e697b
Revises: 
Create Date: 2026-10-14 06:49:41.068666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2636924e697b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla de historial de precios de insumos
    op.create_table(
        'historial_precios_insumos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('insumo_id', sa.Integer(), nullable=False),
        sa.Column('precio', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('fecha', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('compra_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['compra_id'], ['compras.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['insumo_id'], ['insumos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Agregar columna activo a insumos con valor por defecto true
    op.add_column(
        'insumos',
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )

    # Agregar columna activo a productos con valor por defecto true
    op.add_column(
        'productos',
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )


def downgrade() -> None:
    op.drop_column('productos', 'activo')
    op.drop_column('insumos', 'activo')
    op.drop_table('historial_precios_insumos')
