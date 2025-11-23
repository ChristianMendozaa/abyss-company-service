# app/schemas/usuario_sucursal.py
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UsuarioSucursalCreate(BaseModel):
    """Body para asignar un empleado a una sucursal."""
    usuario_id: int = Field(..., description="ID del usuario a asignar")


class UsuarioEnSucursalResponse(BaseModel):
    """Usuario completo que pertenece a la sucursal seleccionada."""
    id_usuario: int
    nombre: str
    apellido: str
    email: EmailStr
    es_dueno: bool
    estado: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class UsuarioSucursalResponse(BaseModel):
    """Solo la relación, por si la quieres usar en otros endpoints."""
    usuarios_id_usuario: int
    sucursales_id_sucursal: int

    class Config:
        from_attributes = True
