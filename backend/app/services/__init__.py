from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from app.models import Product, Batch, Tank, Receipt, Consumption, ProcessUnit, ProcessRun, User, AuditLog, TankMeasurement
from app.schemas import ProductCreate, ProductUpdate, BatchCreate, TankCreate, TankUpdate, ReceiptCreate, ConsumptionCreate


class ProductService:
    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
        result = await db.execute(select(Product).where(Product.is_active == True).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, product: ProductCreate) -> Product:
        db_product = Product(**product.model_dump())
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        return db_product

    @staticmethod
    async def update(db: AsyncSession, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
        db_product = await ProductService.get_by_id(db, product_id)
        if not db_product:
            return None
        
        update_data = product_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        await db.commit()
        await db.refresh(db_product)
        return db_product

    @staticmethod
    async def delete(db: AsyncSession, product_id: int) -> bool:
        db_product = await ProductService.get_by_id(db, product_id)
        if not db_product:
            return False
        
        db_product.is_active = False
        await db.commit()
        return True


class BatchService:
    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Batch]:
        result = await db.execute(select(Batch).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, batch_id: int) -> Optional[Batch]:
        result = await db.execute(select(Batch).where(Batch.id == batch_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, batch: BatchCreate) -> Batch:
        db_batch = Batch(**batch.model_dump())
        db.add(db_batch)
        await db.commit()
        await db.refresh(db_batch)
        return db_batch


class TankService:
    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Tank]:
        result = await db.execute(select(Tank).where(Tank.is_active == True).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, tank_id: int) -> Optional[Tank]:
        result = await db.execute(select(Tank).where(Tank.id == tank_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, tank: TankCreate) -> Tank:
        db_tank = Tank(
            **tank.model_dump(),
            current_volume=0.0,
            level_percent=0.0,
            pressure_atm=1.0
        )
        db.add(db_tank)
        await db.commit()
        await db.refresh(db_tank)
        return db_tank

    @staticmethod
    async def update(db: AsyncSession, tank_id: int, tank_update: TankUpdate) -> Optional[Tank]:
        db_tank = await TankService.get_by_id(db, tank_id)
        if not db_tank:
            return None
        
        update_data = tank_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_tank, field, value)
        
        db_tank.last_updated = datetime.utcnow()
        await db.commit()
        await db.refresh(db_tank)
        return db_tank

    @staticmethod
    async def update_volume(db: AsyncSession, tank_id: int, volume_change: float) -> Optional[Tank]:
        db_tank = await TankService.get_by_id(db, tank_id)
        if not db_tank:
            return None
        
        new_volume = db_tank.current_volume + volume_change
        if new_volume < 0 or new_volume > db_tank.capacity_m3:
            raise ValueError(f"Volume change would exceed tank capacity (0-{db_tank.capacity_m3} m³)")
        
        db_tank.current_volume = new_volume
        db_tank.level_percent = (new_volume / db_tank.capacity_m3) * 100
        db_tank.last_updated = datetime.utcnow()
        
        await db.commit()
        await db.refresh(db_tank)
        return db_tank

    @staticmethod
    async def get_measurements(db: AsyncSession, tank_id: int, hours: int = 24) -> List[TankMeasurement]:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(TankMeasurement)
            .where(TankMeasurement.tank_id == tank_id)
            .where(TankMeasurement.time >= cutoff_time)
            .order_by(TankMeasurement.time.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_measurement(db: AsyncSession, tank_id: int, volume: float, level: float, 
                             temperature: Optional[float] = None, pressure: Optional[float] = None) -> TankMeasurement:
        measurement = TankMeasurement(
            tank_id=tank_id,
            volume_m3=volume,
            level_percent=level,
            temperature_celsius=temperature,
            pressure_atm=pressure
        )
        db.add(measurement)
        await db.commit()
        await db.refresh(measurement)
        return measurement

    @staticmethod
    async def get_critical_tanks(db: AsyncSession) -> List[Tank]:
        result = await db.execute(
            select(Tank).where(
                or_(
                    Tank.level_percent > 90,
                    Tank.level_percent < 10,
                    and_(Tank.temperature_celsius != None, Tank.temperature_celsius > 50)
                )
            )
        )
        return list(result.scalars().all())


class ReceiptService:
    @staticmethod
    async def calculate_mass(volume_m3: float, density: float, temperature: float) -> float:
        """Calculate mass using GOST R 8.599-2003 formula"""
        # mass = volume * density * (1 - 0.0008 * (t - 20))
        temperature_coefficient = 1 - 0.0008 * (temperature - 20)
        return volume_m3 * density * temperature_coefficient

    @staticmethod
    async def create_receipt(db: AsyncSession, receipt_data: ReceiptCreate, user_id: int) -> Receipt:
        batch = await BatchService.get_by_id(db, receipt_data.batch_id)
        if not batch:
            raise ValueError("Batch not found")
        
        product = await ProductService.get_by_id(db, batch.product_id)
        if not product:
            raise ValueError("Product not found")
        
        temperature = receipt_data.temperature_celsius or 20.0
        mass = await ReceiptService.calculate_mass(
            receipt_data.volume_m3,
            product.density,
            temperature
        )
        
        receipt_number = f"RCP-{datetime.utcnow().strftime('%Y%m%d')}-{await db.execute(select(func.count(Receipt.id)))}"
        
        db_receipt = Receipt(
            receipt_number=receipt_number,
            batch_id=receipt_data.batch_id,
            tank_id=receipt_data.tank_id,
            source_type=receipt_data.source_type,
            source_name=receipt_data.source_name,
            volume_m3=receipt_data.volume_m3,
            temperature_celsius=temperature,
            mass_kg=mass,
            created_by=user_id
        )
        
        db.add(db_receipt)
        
        # Update tank volume
        await TankService.update_volume(db, receipt_data.tank_id, receipt_data.volume_m3)
        
        await db.commit()
        await db.refresh(db_receipt)
        return db_receipt

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Receipt]:
        result = await db.execute(
            select(Receipt)
            .where(Receipt.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class ConsumptionService:
    @staticmethod
    async def create_consumption(db: AsyncSession, consumption_data: ConsumptionCreate, user_id: int) -> Consumption:
        tank = await TankService.get_by_id(db, consumption_data.tank_id)
        if not tank:
            raise ValueError("Tank not found")
        
        product = await ProductService.get_by_id(db, consumption_data.product_id)
        if not product:
            raise ValueError("Product not found")
        
        # Calculate mass from volume
        temperature = tank.temperature_celsius or 20.0
        mass = consumption_data.volume_m3 * product.density * (1 - 0.0008 * (temperature - 20))
        
        consumption_number = f"CNS-{datetime.utcnow().strftime('%Y%m%d')}-{await db.execute(select(func.count(Consumption.id)))}"
        
        db_consumption = Consumption(
            consumption_number=consumption_number,
            tank_id=consumption_data.tank_id,
            product_id=consumption_data.product_id,
            volume_m3=consumption_data.volume_m3,
            mass_kg=mass,
            consumption_type=consumption_data.consumption_type,
            reference_id=consumption_data.reference_id,
            created_by=user_id
        )
        
        db.add(db_consumption)
        
        # Update tank volume (decrease)
        await TankService.update_volume(db, consumption_data.tank_id, -consumption_data.volume_m3)
        
        await db.commit()
        await db.refresh(db_consumption)
        return db_consumption

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Consumption]:
        result = await db.execute(
            select(Consumption)
            .where(Consumption.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class BalanceCalculatorService:
    @staticmethod
    async def calculate_balance(inputs: List[dict], outputs: List[dict]) -> dict:
        total_input = sum(item['mass_kg'] for item in inputs)
        total_output = sum(item['mass_kg'] for item in outputs)
        discrepancy = total_input - total_output
        discrepancy_percent = (discrepancy / total_input * 100) if total_input > 0 else 0
        
        # Acceptable discrepancy is typically <= 0.5%
        is_balanced = abs(discrepancy_percent) <= 0.5
        
        return {
            "total_input_kg": total_input,
            "total_output_kg": total_output,
            "discrepancy_kg": discrepancy,
            "discrepancy_percent": round(discrepancy_percent, 4),
            "is_balanced": is_balanced
        }
