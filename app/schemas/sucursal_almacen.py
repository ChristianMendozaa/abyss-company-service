# app/schemas/sucursal_almacen.py
from pydantic import BaseModel, Field


class SucursalAlmacenCreate(BaseModel):
    """Body para vincular un almacén con una sucursal."""
    sucursal_id: int = Field(..., description="ID de la sucursal a vincular")


class SucursalAlmacenResponse(BaseModel):
    sucursales_id_sucursal: int
    almacenes_id_almacen: int

    class Config:
        from_attributes = True
