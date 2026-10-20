"""initial migration: content and auth schemas

Revision ID: 0001_initial_schemas
Revises: 
Create Date: 2026-10-18 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Identificadores de Alembic
revision = '0001_initial_schemas'
down_revision = None  # Es la raíz del árbol de migraciones
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # 1. Crear los esquemas en PostgreSQL si no existen
    # =========================================================================
    op.execute("CREATE SCHEMA IF NOT EXISTS content")
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # =========================================================================
    # 2. Esquema AUTH: Tabla de Autenticación
    # =========================================================================
    op.create_table(
        'usuario',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        schema='auth'
    )

    # =========================================================================
    # 3. Esquema CONTENT: Tablas del Restaurante
    # =========================================================================
    
    # 3.1. Tabla de Usuarios / Clientes del restaurante
    op.create_table(
        'usuario',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('telefono', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        schema='content'
    )

    # 3.2. Tabla de Mesas
    op.create_table(
        'mesa',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('capacidad', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero'),
        schema='content'
    )

    # 3.3. Tabla de Productos del Menú
    op.create_table(
        'producto',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('categoria_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('ingredientes', sa.Text(), nullable=True),
        sa.Column('precio', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='content'
    )

    # 3.4. Tabla de Recibos de Venta
    op.create_table(
        'recibo',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cliente_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mesero_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mesa_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tipo_pedido', sa.String(length=50), nullable=True),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('metodo_pago', sa.String(length=50), nullable=True),
        sa.Column('creation_date', sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='content'
    )


def downgrade():
    # En downgrade borramos en orden inverso para respetar dependencias
    op.drop_table('recibo', schema='content')
    op.drop_table('producto', schema='content')
    op.drop_table('mesa', schema='content')
    op.drop_table('usuario', schema='content')
    op.drop_table('usuario', schema='auth')
