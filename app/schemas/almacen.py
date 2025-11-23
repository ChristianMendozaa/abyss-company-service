# app/schemas/almacen.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlmacenBase(BaseModel):
    nombre: str = Field(..., max_length=70)
    descripcion: Optional[str] = Field(None, max_length=300)
    es_principal: bool = False
    estado: Optional[bool] = True


class AlmacenCreate(AlmacenBase):
    # 👇 nueva propiedad: sucursal a la que se asigna al crearse
    sucursal_id: int = Field(..., description="ID de la sucursal a la que se asigna este almacén al crearse")


class AlmacenUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=70)
    descripcion: Optional[str] = Field(None, max_length=300)
    es_principal: Optional[bool] = None
    estado: Optional[bool] = None


class AlmacenResponse(AlmacenBase):
    id_almacen: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
