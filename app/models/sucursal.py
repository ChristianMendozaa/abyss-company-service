# app/models/sucursal.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime

from app.database import Base


class Sucursal(Base):
    __tablename__ = "sucursales"

    id_sucursal = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    direccion = Column(String(100), nullable=False)
    telefono = Column(String(15), nullable=True)
    estado = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    empresas_id_empresa = Column(Integer, nullable=False, index=True)
