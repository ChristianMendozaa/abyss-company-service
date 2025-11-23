# app/models/almacen.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime

from app.database import Base


class Almacen(Base):
    __tablename__ = "almacenes"

    id_almacen = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(70), nullable=False)
    descripcion = Column(String(300), nullable=True)
    es_principal = Column(Boolean, nullable=False, default=False)
    estado = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    empresas_id_empresa = Column(Integer, nullable=False, index=True)
