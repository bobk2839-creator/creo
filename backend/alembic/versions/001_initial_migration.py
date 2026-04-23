"""initial migration

Revision ID: initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable TimescaleDB extension
    op.execute('CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE')
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'TECH', 'STOREKEEPER', 'LOGISTICIAN', 'AUDITOR', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=True),
        sa.Column('two_factor_secret', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Create products table
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('density', sa.Float(), nullable=False),
        sa.Column('sulfur_content', sa.Float(), nullable=True),
        sa.Column('octane_number', sa.Float(), nullable=True),
        sa.Column('cetane_number', sa.Float(), nullable=True),
        sa.Column('product_type', sa.Enum('CRUDE_OIL', 'GASOLINE', 'DIESEL', 'KEROSENE', 'MAZUT', 'LPG', 'OTHER', name='producttype'), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    
    # Create tanks table
    op.create_table('tanks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('capacity_m3', sa.Float(), nullable=False),
        sa.Column('current_volume', sa.Float(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('level_percent', sa.Float(), nullable=True),
        sa.Column('max_level_m', sa.Float(), nullable=False),
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('pressure_atm', sa.Float(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_tanks_id'), 'tanks', ['id'], unique=False)
    
    # Create tank_measurements table (hypertable)
    op.create_table('tank_measurements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('tank_id', sa.Integer(), nullable=False),
        sa.Column('volume_m3', sa.Float(), nullable=False),
        sa.Column('level_percent', sa.Float(), nullable=False),
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('pressure_atm', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['tank_id'], ['tanks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tank_measurements_id'), 'tank_measurements', ['id'], unique=False)
    op.create_index(op.f('ix_tank_measurements_time'), 'tank_measurements', ['time'], unique=False)
    
    # Create batches table
    op.create_table('batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.String(length=100), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('passport_quality', sa.JSON(), nullable=True),
        sa.Column('production_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('volume_m3', sa.Float(), nullable=False),
        sa.Column('mass_kg', sa.Float(), nullable=False),
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('is_consumed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_batches_batch_number'), 'batches', ['batch_number'], unique=True)
    op.create_index(op.f('ix_batches_id'), 'batches', ['id'], unique=False)
    
    # Create receipts table
    op.create_table('receipts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('receipt_number', sa.String(length=100), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('tank_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=True),
        sa.Column('volume_m3', sa.Float(), nullable=False),
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('mass_kg', sa.Float(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tank_id'], ['tanks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipts_id'), 'receipts', ['id'], unique=False)
    op.create_index(op.f('ix_receipts_receipt_number'), 'receipts', ['receipt_number'], unique=True)
    
    # Create consumptions table
    op.create_table('consumptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('consumption_number', sa.String(length=100), nullable=False),
        sa.Column('tank_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('volume_m3', sa.Float(), nullable=False),
        sa.Column('mass_kg', sa.Float(), nullable=False),
        sa.Column('consumption_type', sa.String(length=50), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['tank_id'], ['tanks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consumptions_consumption_number'), 'consumptions', ['consumption_number'], unique=True)
    op.create_index(op.f('ix_consumptions_id'), 'consumptions', ['id'], unique=False)
    
    # Create process_units table
    op.create_table('process_units',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('unit_type', sa.Enum('AT', 'REFORMING', 'HYDROTREATING', 'BLENDING', name='processunittype'), nullable=False),
        sa.Column('input_products', sa.JSON(), nullable=True),
        sa.Column('output_coefficients', sa.JSON(), nullable=True),
        sa.Column('max_capacity_kg_per_hour', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_process_units_id'), 'process_units', ['id'], unique=False)
    
    # Create process_runs table
    op.create_table('process_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('input_batch_id', sa.Integer(), nullable=False),
        sa.Column('output_batches', sa.JSON(), nullable=True),
        sa.Column('efficiency_percent', sa.Float(), nullable=True),
        sa.Column('loss_kg', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['input_batch_id'], ['batches.id'], ),
        sa.ForeignKeyConstraint(['unit_id'], ['process_units.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_process_runs_id'), 'process_runs', ['id'], unique=False)
    
    # Create carriers table
    op.create_table('carriers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('inn', sa.String(length=20), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_carriers_id'), 'carriers', ['id'], unique=False)
    
    # Create vehicles table
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('carrier_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_number', sa.String(length=20), nullable=False),
        sa.Column('capacity_m3', sa.Float(), nullable=False),
        sa.Column('vehicle_type', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['carrier_id'], ['carriers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vehicle_number')
    )
    op.create_index(op.f('ix_vehicles_id'), 'vehicles', ['id'], unique=False)
    
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_number', sa.String(length=100), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('requested_volume_m3', sa.Float(), nullable=False),
        sa.Column('tank_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('CREATED', 'CONFIRMED', 'IN_TRANSIT', 'LOADING', 'SHIPPED', 'COMPLETED', 'CANCELLED', name='orderstatus'), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['tank_id'], ['tanks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)
    op.create_index(op.f('ix_orders_order_number'), 'orders', ['order_number'], unique=True)
    
    # Create waybills table
    op.create_table('waybills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('waybill_number', sa.String(length=100), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('loaded_volume_m3', sa.Float(), nullable=False),
        sa.Column('loaded_mass_kg', sa.Float(), nullable=False),
        sa.Column('departure_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrival_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('route_data', sa.JSON(), nullable=True),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_waybills_id'), 'waybills', ['id'], unique=False)
    op.create_index(op.f('ix_waybills_waybill_number'), 'waybills', ['waybill_number'], unique=True)
    
    # Create audit_log table
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_id'), 'audit_log', ['id'], unique=False)
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'], unique=False)
    
    # Create units_of_measure table
    op.create_table('units_of_measure',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('conversion_factor', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_units_of_measure_id'), 'units_of_measure', ['id'], unique=False)
    
    # Create gost_coefficients table
    op.create_table('gost_coefficients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coefficient_name', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('gost_standard', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gost_coefficients_id'), 'gost_coefficients', ['id'], unique=False)


def downgrade():
    op.drop_table('gost_coefficients')
    op.drop_table('units_of_measure')
    op.drop_table('audit_log')
    op.drop_table('waybills')
    op.drop_table('orders')
    op.drop_table('vehicles')
    op.drop_table('carriers')
    op.drop_table('process_runs')
    op.drop_table('process_units')
    op.drop_table('consumptions')
    op.drop_table('receipts')
    op.drop_table('batches')
    op.drop_table('tank_measurements')
    op.drop_table('tanks')
    op.drop_table('products')
    op.drop_table('users')
