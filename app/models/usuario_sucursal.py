from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class UsuarioSucursal(Base):
    __tablename__ = "usuarios_sucursales"

    usuarios_id_usuario = Column(Integer, primary_key=True, index=True)

    sucursales_id_sucursal = Column(
        Integer,
        ForeignKey("sucursales.id_sucursal"),
        primary_key=True,
    )
