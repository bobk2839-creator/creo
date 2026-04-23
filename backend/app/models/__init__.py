from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TECH = "tech"
    STOREKEEPER = "storekeeper"
    LOGISTICIAN = "logistician"
    AUDITOR = "auditor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STOREKEEPER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    receipts = relationship("Receipt", back_populates="created_by")
    consumptions = relationship("Consumption", back_populates="created_by")
    orders = relationship("Order", back_populates="created_by")


class ProductType(str, enum.Enum):
    CRUDE_OIL = "crude_oil"
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    KEROSENE = "kerosene"
    MAZUT = "mazut"
    LPG = "lpg"
    OTHER = "other"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    density = Column(Float, nullable=False)  # kg/m³ at 20°C
    sulfur_content = Column(Float, nullable=True)  # %
    octane_number = Column(Float, nullable=True)  # for gasoline
    cetane_number = Column(Float, nullable=True)  # for diesel
    product_type = Column(Enum(ProductType), default=ProductType.OTHER)
    color = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    batches = relationship("Batch", back_populates="product")
    tanks = relationship("Tank", back_populates="product")


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(100), unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    passport_quality = Column(JSON, nullable=True)  # Quality certificate data
    production_date = Column(DateTime(timezone=True), nullable=False)
    volume_m3 = Column(Float, nullable=False)
    mass_kg = Column(Float, nullable=False)
    temperature_celsius = Column(Float, nullable=True)
    is_consumed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="batches")
    receipts = relationship("Receipt", back_populates="batch")
    process_runs_input = relationship("ProcessRun", foreign_keys="ProcessRun.input_batch_id", back_populates="input_batch")


class Tank(Base):
    __tablename__ = "tanks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    capacity_m3 = Column(Float, nullable=False)
    current_volume = Column(Float, default=0.0)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    level_percent = Column(Float, default=0.0)
    max_level_m = Column(Float, nullable=False)
    temperature_celsius = Column(Float, nullable=True)
    pressure_atm = Column(Float, default=1.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    product = relationship("Product", back_populates="tanks")
    measurements = relationship("TankMeasurement", back_populates="tank")
    receipts = relationship("Receipt", back_populates="tank")


class TankMeasurement(Base):
    __tablename__ = "tank_measurements"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tank_id = Column(Integer, ForeignKey("tanks.id"), nullable=False)
    volume_m3 = Column(Float, nullable=False)
    level_percent = Column(Float, nullable=False)
    temperature_celsius = Column(Float, nullable=True)
    pressure_atm = Column(Float, nullable=True)

    # Relationships
    tank = relationship("Tank", back_populates="measurements")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(100), unique=True, index=True, nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    tank_id = Column(Integer, ForeignKey("tanks.id"), nullable=False)
    source_type = Column(String(50), nullable=False)  # tanker, rail, pipeline
    source_name = Column(String(255), nullable=True)
    volume_m3 = Column(Float, nullable=False)
    temperature_celsius = Column(Float, nullable=True)
    mass_kg = Column(Float, nullable=False)  # Calculated by formula
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationships
    batch = relationship("Batch", back_populates="receipts")
    tank = relationship("Tank", back_populates="receipts")
    created_by_user = relationship("User", back_populates="receipts")


class Consumption(Base):
    __tablename__ = "consumptions"

    id = Column(Integer, primary_key=True, index=True)
    consumption_number = Column(String(100), unique=True, index=True, nullable=False)
    tank_id = Column(Integer, ForeignKey("tanks.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    volume_m3 = Column(Float, nullable=False)
    mass_kg = Column(Float, nullable=False)
    consumption_type = Column(String(50), nullable=False)  # shipment, processing, loss
    reference_id = Column(Integer, nullable=True)  # Order ID or ProcessRun ID
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationships
    tank = relationship("Tank")
    product = relationship("Product")
    created_by_user = relationship("User", back_populates="consumptions")


class ProcessUnitType(str, enum.Enum):
    AT = "at"  # Atmospheric distillation
    REFORMING = "reforming"
    HYDROTREATING = "hydrotreating"
    BLENDING = "blending"


class ProcessUnit(Base):
    __tablename__ = "process_units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    unit_type = Column(Enum(ProcessUnitType), nullable=False)
    input_products = Column(JSON, nullable=True)  # List of acceptable input product IDs
    output_coefficients = Column(JSON, nullable=True)  # Dict of output product coefficients
    max_capacity_kg_per_hour = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    process_runs = relationship("ProcessRun", back_populates="unit")


class ProcessRun(Base):
    __tablename__ = "process_runs"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("process_units.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    input_batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    output_batches = Column(JSON, nullable=True)  # List of output batch IDs
    efficiency_percent = Column(Float, nullable=True)
    loss_kg = Column(Float, default=0.0)
    status = Column(String(50), default="running")  # running, completed, stopped
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    unit = relationship("ProcessUnit", back_populates="process_runs")
    input_batch = relationship("Batch", foreign_keys=[input_batch_id], back_populates="process_runs_input")


class Carrier(Base):
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    inn = Column(String(20), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    vehicle_number = Column(String(20), unique=True, nullable=False)
    capacity_m3 = Column(Float, nullable=False)
    vehicle_type = Column(String(50), nullable=True)  # tanker, truck
    is_active = Column(Boolean, default=True)

    # Relationships
    carrier = relationship("Carrier")
    waybills = relationship("Waybill", back_populates="vehicle")


class OrderStatus(str, enum.Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    IN_TRANSIT = "in_transit"
    LOADING = "loading"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(100), unique=True, index=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    requested_volume_m3 = Column(Float, nullable=False)
    tank_id = Column(Integer, ForeignKey("tanks.id"), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.CREATED)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product")
    tank = relationship("Tank")
    created_by_user = relationship("User", back_populates="orders")
    waybills = relationship("Waybill", back_populates="order")


class Waybill(Base):
    __tablename__ = "waybills"

    id = Column(Integer, primary_key=True, index=True)
    waybill_number = Column(String(100), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    loaded_volume_m3 = Column(Float, nullable=False)
    loaded_mass_kg = Column(Float, nullable=False)
    departure_time = Column(DateTime(timezone=True), nullable=True)
    arrival_time = Column(DateTime(timezone=True), nullable=True)
    route_data = Column(JSON, nullable=True)  # Route coordinates and distance
    pdf_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="waybills")
    vehicle = relationship("Vehicle", back_populates="waybills")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)  # volume, mass, temperature, pressure
    conversion_factor = Column(Float, default=1.0)  # To base unit
    is_active = Column(Boolean, default=True)


class GOSTCoefficient(Base):
    __tablename__ = "gost_coefficients"

    id = Column(Integer, primary_key=True, index=True)
    coefficient_name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    gost_standard = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
