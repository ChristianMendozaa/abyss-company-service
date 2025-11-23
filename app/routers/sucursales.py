# app/routers/sucursales.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.deps import require_permission, CurrentUser
from app.models.sucursal import Sucursal
from app.models.usuario_sucursal import UsuarioSucursal
from app.schemas.sucursal import (
    SucursalCreate,
    SucursalUpdate,
    SucursalResponse,
)
from app.schemas.usuario_sucursal import (
    UsuarioSucursalCreate,
    UsuarioSucursalResponse,
    UsuarioEnSucursalResponse,
)
from app.schemas.almacen import AlmacenResponse


router = APIRouter(prefix="/sucursales", tags=["sucursales"])


# =========================
#  CRUD SUCURSALES
# =========================

@router.get(
    "/{sucursal_id}/almacenes",
    response_model=List[AlmacenResponse],
)
async def list_almacenes_de_sucursal(
    sucursal_id: int,
    current_user: CurrentUser = Depends(require_permission("read", "sucursales_almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista los **almacenes** que atienden a una sucursal de la empresa actual.

    Devuelve la info completa del almacén (id, nombre, descripción, etc.),
    no solo los IDs de la tabla intermedia.
    """

    # 1) Verificar que la sucursal pertenece a la empresa del usuario
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found in your company",
        )

    # 2) JOIN sucursales_almacenes + almacenes para traer datos del almacén
    sql = text(
        """
        SELECT 
            a.id_almacen,
            a.nombre,
            a.descripcion,
            a.es_principal,
            a.estado,
            a.fecha_creacion
        FROM sucursales_almacenes sa
        JOIN almacenes a
          ON a.id_almacen = sa.almacenes_id_almacen
        WHERE sa.sucursales_id_sucursal = :sucursal_id
          AND a.empresas_id_empresa = :id_empresa
        ORDER BY a.id_almacen
        """
    )

    result = await db.execute(
        sql,
        {
            "sucursal_id": sucursal_id,
            "id_empresa": current_user.empresa.id_empresa,
        },
    )
    rows = result.mappings().all()

    return [
        AlmacenResponse(
            id_almacen=r["id_almacen"],
            nombre=r["nombre"],
            descripcion=r["descripcion"],
            es_principal=r["es_principal"],
            estado=r["estado"],
            fecha_creacion=r["fecha_creacion"],
        )
        for r in rows
    ]


@router.post("", response_model=SucursalResponse, status_code=status.HTTP_201_CREATED)
async def create_sucursal(
    sucursal_create: SucursalCreate,
    current_user: CurrentUser = Depends(require_permission("create", "sucursales")),
    db: AsyncSession = Depends(get_db),
):
    sucursal = Sucursal(
        nombre=sucursal_create.nombre,
        direccion=sucursal_create.direccion,
        telefono=sucursal_create.telefono,
        estado=sucursal_create.estado if sucursal_create.estado is not None else True,
        empresas_id_empresa=current_user.empresa.id_empresa,
    )
    db.add(sucursal)
    await db.flush()
    await db.refresh(sucursal)
    return SucursalResponse.model_validate(sucursal)

@router.get("", response_model=List[SucursalResponse])
async def list_sucursales(
    current_user: CurrentUser = Depends(require_permission("read", "sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todas las sucursales de la empresa del usuario actual.
    """
    q = (
        select(Sucursal)
        .where(Sucursal.empresas_id_empresa == current_user.empresa.id_empresa)
    )
    result = await db.execute(q)
    rows = result.scalars().all()
    return [SucursalResponse.model_validate(r) for r in rows]


@router.get("/{sucursal_id}", response_model=SucursalResponse)
async def get_sucursal(
    sucursal_id: int,
    current_user: CurrentUser = Depends(require_permission("read", "sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene una sucursal específica de la empresa actual.
    """
    q = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    result = await db.execute(q)
    sucursal = result.scalar_one_or_none()

    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    return SucursalResponse.model_validate(sucursal)


@router.post(
    "/{sucursal_id}/usuarios",
    response_model=UsuarioSucursalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_usuario_to_sucursal(
    sucursal_id: int,
    payload: UsuarioSucursalCreate,
    current_user: CurrentUser = Depends(require_permission("create", "usuarios_sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Asigna un empleado a una sucursal, validando que ambos
    pertenezcan a la empresa actual.

    - sucursal_id viene del path
    - usuario_id viene en el body
    """

    # 1) Validar que la sucursal pertenezca a la empresa del usuario
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sucursal does not belong to your company or does not exist",
        )

    # 2) Validar que el usuario pertenezca a la misma empresa
    sql_user = text(
        """
        SELECT id_usuario
        FROM usuarios
        WHERE id_usuario = :id_usuario
          AND empresas_id_empresa = :id_empresa
        """
    )
    res_u = await db.execute(
        sql_user,
        {
            "id_usuario": payload.usuario_id,
            "id_empresa": current_user.empresa.id_empresa,
        },
    )
    user_row = res_u.fetchone()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to your company or does not exist",
        )

    # 3) Crear la asignación
    asign = UsuarioSucursal(
        usuarios_id_usuario=payload.usuario_id,
        sucursales_id_sucursal=sucursal_id,
    )
    db.add(asign)
    await db.flush()

    return UsuarioSucursalResponse(
        usuarios_id_usuario=payload.usuario_id,
        sucursales_id_sucursal=sucursal_id,
    )


@router.patch("/{sucursal_id}", response_model=SucursalResponse)
async def update_sucursal(
    sucursal_id: int,
    sucursal_update: SucursalUpdate,
    current_user: CurrentUser = Depends(require_permission("update", "sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza una sucursal de la empresa actual.
    """
    q = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    result = await db.execute(q)
    sucursal = result.scalar_one_or_none()

    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    data = sucursal_update.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(sucursal, field, value)

    await db.flush()
    await db.refresh(sucursal)
    return SucursalResponse.model_validate(sucursal)


@router.delete("/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sucursal(
    sucursal_id: int,
    current_user: CurrentUser = Depends(require_permission("delete", "sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina lógicamente una sucursal (estado = False).
    """
    q = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    result = await db.execute(q)
    sucursal = result.scalar_one_or_none()

    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    sucursal.estado = False
    await db.flush()
    return None


# =========================
#  ASIGNACIÓN USUARIOS-SUCURSALES
#  (tabla usuarios_sucursales)
# =========================

@router.get(
    "/{sucursal_id}/usuarios",
    response_model=List[UsuarioEnSucursalResponse],
)
async def list_usuarios_de_sucursal(
    sucursal_id: int,
    current_user: CurrentUser = Depends(require_permission("read", "usuarios_sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista los **usuarios** asignados a una sucursal de la empresa actual.

    Devuelve la info completa del usuario (id, nombre, apellido, email, etc.),
    no solo los IDs de la tabla intermedia.
    """
    # Verificar que la sucursal pertenece a la empresa
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found in your company",
        )

    # JOIN usuarios_sucursales + usuarios para traer los datos del usuario
    sql = text(
        """
        SELECT 
            u.id_usuario,
            u.nombre,
            u.apellido,
            u.email,
            u.es_dueno,
            u.estado,
            u.fecha_creacion
        FROM usuarios_sucursales us
        JOIN usuarios u
          ON u.id_usuario = us.usuarios_id_usuario
        WHERE us.sucursales_id_sucursal = :sucursal_id
          AND u.empresas_id_empresa = :id_empresa
        ORDER BY u.id_usuario
        """
    )

    result = await db.execute(
        sql,
        {
            "sucursal_id": sucursal_id,
            "id_empresa": current_user.empresa.id_empresa,
        },
    )

    rows = result.mappings().all()

    return [
        UsuarioEnSucursalResponse(
            id_usuario=r["id_usuario"],
            nombre=r["nombre"],
            apellido=r["apellido"],
            email=r["email"],
            es_dueno=r["es_dueno"],
            estado=r["estado"],
            fecha_creacion=r["fecha_creacion"],
        )
        for r in rows
    ]

@router.post(
    "/{sucursal_id}/usuarios",
    response_model=UsuarioSucursalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_usuario_to_sucursal(
    sucursal_id: int,
    payload: UsuarioSucursalCreate,
    current_user: CurrentUser = Depends(require_permission("create", "usuarios_sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Asigna un empleado a una sucursal, validando que ambos
    pertenezcan a la empresa actual.
    El body contiene usuarios_id_usuario y sucursales_id_sucursal,
    pero sucursales_id_sucursal debe coincidir con el path.
    """
    if payload.sucursales_id_sucursal != sucursal_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sucursales_id_sucursal must match path parameter",
        )

    # Validar sucursal de la empresa
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sucursal does not belong to your company or does not exist",
        )

    # Validar usuario de la empresa
    sql_user = text(
        """
        SELECT id_usuario
        FROM usuarios
        WHERE id_usuario = :id_usuario
          AND empresas_id_empresa = :id_empresa
        """
    )
    res_u = await db.execute(
        sql_user,
        {
            "id_usuario": payload.usuarios_id_usuario,
            "id_empresa": current_user.empresa.id_empresa,
        },
    )
    user_row = res_u.fetchone()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to your company or does not exist",
        )

    asign = UsuarioSucursal(
        usuarios_id_usuario=payload.usuarios_id_usuario,
        sucursales_id_sucursal=sucursal_id,
    )
    db.add(asign)
    await db.flush()

    return UsuarioSucursalResponse(
        usuarios_id_usuario=payload.usuarios_id_usuario,
        sucursales_id_sucursal=sucursal_id,
    )


@router.delete(
    "/{sucursal_id}/usuarios/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_usuario_from_sucursal(
    sucursal_id: int,
    usuario_id: int,
    current_user: CurrentUser = Depends(require_permission("delete", "usuarios_sucursales")),
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina una asignación usuario-sucursal.
    """
    # Verificar sucursal de la empresa
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found in your company",
        )

    q = select(UsuarioSucursal).where(
        UsuarioSucursal.usuarios_id_usuario == usuario_id,
        UsuarioSucursal.sucursales_id_sucursal == sucursal_id,
    )
    result = await db.execute(q)
    asign = result.scalar_one_or_none()

    if not asign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    await db.delete(asign)
    return None
