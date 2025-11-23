# app/models/sucursal_almacen.py
from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class SucursalAlmacen(Base):
    __tablename__ = "sucursales_almacenes"

    sucursales_id_sucursal = Column(Integer, ForeignKey("sucursales.id_sucursal"), primary_key=True)
    almacenes_id_almacen = Column(Integer, ForeignKey("almacenes.id_almacen"), primary_key=True)
