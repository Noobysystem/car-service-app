from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plate_number = Column(String, nullable=True)
    current_mileage = Column(Integer, default=0)
    engine = Column(String, nullable=True)

    services = relationship("ServiceLog", back_populates="vehicle", cascade="all, delete-orphan")
    rules = relationship("MaintenanceRule", back_populates="vehicle", cascade="all, delete-orphan")
    parts = relationship("PartReference", back_populates="vehicle", cascade="all, delete-orphan")

class ServiceLog(Base):
    __tablename__ = "service_logs"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    date = Column(Date, nullable=False)
    mileage = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    cost = Column(Float, default=0.0)

    vehicle = relationship("Vehicle", back_populates="services")

class MaintenanceRule(Base):
    __tablename__ = "maintenance_rules"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    title = Column(String, nullable=False)
    interval_km = Column(Integer, nullable=False)
    last_mileage = Column(Integer, nullable=False)

    vehicle = relationship("Vehicle", back_populates="rules")

class PartReference(Base):
    __tablename__ = "part_references"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    category = Column(String, nullable=False)
    part_number = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    description = Column(String, nullable=True)

    vehicle = relationship("Vehicle", back_populates="parts")
