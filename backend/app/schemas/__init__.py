from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    TECH = "tech"
    STOREKEEPER = "storekeeper"
    LOGISTICIAN = "logistician"
    AUDITOR = "auditor"


class ProductTypeEnum(str, Enum):
    CRUDE_OIL = "crude_oil"
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    KEROSENE = "kerosene"
    MAZUT = "mazut"
    LPG = "lpg"
    OTHER = "other"


class ProcessUnitTypeEnum(str, Enum):
    AT = "at"
    REFORMING = "reforming"
    HYDROTREATING = "hydrotreating"
    BLENDING = "blending"


class OrderStatusEnum(str, Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    IN_TRANSIT = "in_transit"
    LOADING = "loading"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    role: UserRoleEnum = UserRoleEnum.STOREKEEPER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


# Product schemas
class ProductBase(BaseModel):
    name: str
    density: float = Field(..., gt=0)
    sulfur_content: Optional[float] = Field(None, ge=0, le=100)
    octane_number: Optional[float] = Field(None, ge=0, le=100)
    cetane_number: Optional[float] = Field(None, ge=0, le=100)
    product_type: ProductTypeEnum = ProductTypeEnum.OTHER
    color: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    density: Optional[float] = None
    sulfur_content: Optional[float] = None
    octane_number: Optional[float] = None
    cetane_number: Optional[float] = None
    product_type: Optional[ProductTypeEnum] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Batch schemas
class BatchBase(BaseModel):
    batch_number: str
    product_id: int
    passport_quality: Optional[Dict[str, Any]] = None
    production_date: datetime
    volume_m3: float = Field(..., gt=0)
    mass_kg: float = Field(..., gt=0)
    temperature_celsius: Optional[float] = None


class BatchCreate(BatchBase):
    pass


class BatchResponse(BatchBase):
    id: int
    is_consumed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Tank schemas
class TankBase(BaseModel):
    name: str
    capacity_m3: float = Field(..., gt=0)
    max_level_m: float = Field(..., gt=0)
    product_id: Optional[int] = None


class TankCreate(TankBase):
    pass


class TankUpdate(BaseModel):
    name: Optional[str] = None
    capacity_m3: Optional[float] = None
    current_volume: Optional[float] = None
    product_id: Optional[int] = None
    level_percent: Optional[float] = None
    max_level_m: Optional[float] = None
    temperature_celsius: Optional[float] = None
    pressure_atm: Optional[float] = None
    is_active: Optional[bool] = None


class TankResponse(TankBase):
    id: int
    current_volume: float
    level_percent: float
    temperature_celsius: Optional[float]
    pressure_atm: float
    last_updated: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TankMeasurementResponse(BaseModel):
    id: int
    tank_id: int
    time: datetime
    volume_m3: float
    level_percent: float
    temperature_celsius: Optional[float]
    pressure_atm: Optional[float]

    model_config = ConfigDict(from_attributes=True)


# Receipt schemas
class ReceiptBase(BaseModel):
    batch_id: int
    tank_id: int
    source_type: str
    source_name: Optional[str] = None
    volume_m3: float = Field(..., gt=0)
    temperature_celsius: Optional[float] = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptResponse(ReceiptBase):
    id: int
    receipt_number: str
    mass_kg: float
    created_by: int
    created_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# Consumption schemas
class ConsumptionBase(BaseModel):
    tank_id: int
    product_id: int
    volume_m3: float = Field(..., gt=0)
    consumption_type: str
    reference_id: Optional[int] = None


class ConsumptionCreate(ConsumptionBase):
    pass


class ConsumptionResponse(ConsumptionBase):
    id: int
    consumption_number: str
    mass_kg: float
    created_by: int
    created_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# Process Unit schemas
class ProcessUnitBase(BaseModel):
    name: str
    unit_type: ProcessUnitTypeEnum
    input_products: Optional[List[int]] = None
    output_coefficients: Optional[Dict[str, float]] = None
    max_capacity_kg_per_hour: Optional[float] = None


class ProcessUnitCreate(ProcessUnitBase):
    pass


class ProcessUnitResponse(ProcessUnitBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Process Run schemas
class ProcessRunBase(BaseModel):
    unit_id: int
    start_time: datetime
    input_batch_id: int
    output_batches: Optional[List[int]] = None
    efficiency_percent: Optional[float] = None
    loss_kg: Optional[float] = 0.0


class ProcessRunCreate(ProcessRunBase):
    pass


class ProcessRunResponse(ProcessRunBase):
    id: int
    end_time: Optional[datetime]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Balance calculation schemas
class BalanceItem(BaseModel):
    product_id: int
    mass_kg: float


class BalanceCalculationRequest(BaseModel):
    inputs: List[BalanceItem]
    outputs: List[BalanceItem]


class BalanceCalculationResponse(BaseModel):
    total_input_kg: float
    total_output_kg: float
    discrepancy_kg: float
    discrepancy_percent: float
    is_balanced: bool


# Carrier schemas
class CarrierBase(BaseModel):
    name: str
    inn: Optional[str] = None
    contact_phone: Optional[str] = None


class CarrierCreate(CarrierBase):
    pass


class CarrierResponse(CarrierBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# Vehicle schemas
class VehicleBase(BaseModel):
    carrier_id: int
    vehicle_number: str
    capacity_m3: float = Field(..., gt=0)
    vehicle_type: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleResponse(VehicleBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# Order schemas
class OrderBase(BaseModel):
    customer_name: str
    product_id: int
    requested_volume_m3: float = Field(..., gt=0)
    tank_id: Optional[int] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: Optional[OrderStatusEnum] = None
    tank_id: Optional[int] = None


class OrderResponse(OrderBase):
    id: int
    order_number: str
    status: OrderStatusEnum
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Waybill schemas
class WaybillBase(BaseModel):
    order_id: int
    vehicle_id: int
    loaded_volume_m3: float
    loaded_mass_kg: float


class WaybillCreate(WaybillBase):
    pass


class WaybillResponse(WaybillBase):
    id: int
    waybill_number: str
    departure_time: Optional[datetime]
    arrival_time: Optional[datetime]
    route_data: Optional[Dict[str, Any]]
    pdf_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Audit log schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    entity_type: str
    entity_id: Optional[int]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Dashboard schemas
class DashboardSummary(BaseModel):
    total_products: int
    total_tanks: int
    total_volume_m3: float
    critical_tanks: List[Dict[str, Any]]
    recent_receipts: int
    recent_consumptions: int


class TankAlert(BaseModel):
    tank_id: int
    tank_name: str
    alert_type: str  # high_level, low_level, high_temperature
    current_value: float
    threshold_value: float


# Pagination schemas
class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    skip: int
    limit: int
