# app/schemas/sucursal.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SucursalBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    direccion: str = Field(..., max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    estado: Optional[bool] = True


class SucursalCreate(SucursalBase):
    # 👇 almacén existente que atenderá esta sucursal (opcional)
    almacen_id: Optional[int] = Field(
        None,
        description="ID de un almacén existente que atenderá esta sucursal al crearse",
    )


class SucursalUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=50)
    direccion: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    estado: Optional[bool] = None


class SucursalResponse(SucursalBase):
    id_sucursal: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
