# app/routers/almacenes.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.schemas.sucursal import SucursalResponse

from app.database import get_db
from app.deps import require_permission, CurrentUser
from app.models.almacen import Almacen
from app.models.sucursal import Sucursal
from app.models.sucursal_almacen import SucursalAlmacen
from app.schemas.almacen import (
    AlmacenCreate,
    AlmacenUpdate,
    AlmacenResponse,
)
from app.schemas.sucursal_almacen import (
    SucursalAlmacenCreate,
    SucursalAlmacenResponse,
)

router = APIRouter(prefix="/almacenes", tags=["almacenes"])


# =========================
#  CRUD ALMACENES
# =========================

@router.get("", response_model=List[AlmacenResponse])
async def list_almacenes(
    current_user: CurrentUser = Depends(require_permission("read", "almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todos los almacenes de la empresa del usuario actual.
    """
    q = select(Almacen).where(
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa
    )
    result = await db.execute(q)
    rows = result.scalars().all()
    return [AlmacenResponse.model_validate(r) for r in rows]


@router.get("/{almacen_id}", response_model=AlmacenResponse)
async def get_almacen(
    almacen_id: int,
    current_user: CurrentUser = Depends(require_permission("read", "almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene un almacén específico de la empresa actual.
    """
    q = select(Almacen).where(
        Almacen.id_almacen == almacen_id,
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    result = await db.execute(q)
    almacen = result.scalar_one_or_none()

    if not almacen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    return AlmacenResponse.model_validate(almacen)


@router.post("", response_model=AlmacenResponse, status_code=status.HTTP_201_CREATED)
async def create_almacen(
    almacen_create: AlmacenCreate,
    current_user: CurrentUser = Depends(require_permission("create", "almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un nuevo almacén para la empresa actual y lo asigna
    a una sucursal (sucursal_id) al momento de crearse.
    """

    # 1) Validar que la sucursal pertenezca a la empresa
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == almacen_create.sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sucursal does not belong to your company or does not exist",
        )

    # 2) Crear el almacén
    almacen = Almacen(
        nombre=almacen_create.nombre,
        descripcion=almacen_create.descripcion,
        es_principal=almacen_create.es_principal,
        estado=almacen_create.estado if almacen_create.estado is not None else True,
        empresas_id_empresa=current_user.empresa.id_empresa,
    )
    db.add(almacen)
    await db.flush()          # para obtener id_almacen
    await db.refresh(almacen)

    # 3) Crear el vínculo sucursal_almacen
    vinculo = SucursalAlmacen(
        sucursales_id_sucursal=almacen_create.sucursal_id,
        almacenes_id_almacen=almacen.id_almacen,
    )
    db.add(vinculo)
    await db.flush()

    return AlmacenResponse.model_validate(almacen)


@router.patch("/{almacen_id}", response_model=AlmacenResponse)
async def update_almacen(
    almacen_id: int,
    almacen_update: AlmacenUpdate,
    current_user: CurrentUser = Depends(require_permission("update", "almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza un almacén de la empresa actual.
    """
    q = select(Almacen).where(
        Almacen.id_almacen == almacen_id,
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    result = await db.execute(q)
    almacen = result.scalar_one_or_none()

    if not almacen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    data = almacen_update.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(almacen, field, value)

    await db.flush()
    await db.refresh(almacen)
    return AlmacenResponse.model_validate(almacen)


@router.delete("/{almacen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_almacen(
    almacen_id: int,
    current_user: CurrentUser = Depends(require_permission("delete", "almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina lógicamente un almacén (estado = False).
    """
    q = select(Almacen).where(
        Almacen.id_almacen == almacen_id,
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    result = await db.execute(q)
    almacen = result.scalar_one_or_none()

    if not almacen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    almacen.estado = False
    await db.flush()
    return None


# =========================
#  ASIGNACIÓN SUCURSALES-ALMACENES
#  (tabla sucursales_almacenes)
# =========================


@router.get(
    "/{almacen_id}/sucursales",
    response_model=List[SucursalResponse],
)
async def list_sucursales_de_almacen(
    almacen_id: int,
    current_user: CurrentUser = Depends(require_permission("read", "sucursales_almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista las **sucursales** atendidas por un almacén de la empresa actual.

    Devuelve la info completa de la sucursal (id, nombre, dirección, etc.),
    no solo los IDs de la tabla intermedia.
    """
    # Verificar que el almacén pertenece a la empresa
    q_a = select(Almacen).where(
        Almacen.id_almacen == almacen_id,
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_a = await db.execute(q_a)
    almacen = res_a.scalar_one_or_none()
    if not almacen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found in your company",
        )

    sql = text(
        """
        SELECT 
            s.id_sucursal,
            s.nombre,
            s.direccion,
            s.telefono,
            s.estado,
            s.fecha_creacion
        FROM sucursales_almacenes sa
        JOIN sucursales s
          ON s.id_sucursal = sa.sucursales_id_sucursal
        WHERE sa.almacenes_id_almacen = :almacen_id
          AND s.empresas_id_empresa = :id_empresa
        ORDER BY s.id_sucursal
        """
    )

    result = await db.execute(
        sql,
        {
            "almacen_id": almacen_id,
            "id_empresa": current_user.empresa.id_empresa,
        },
    )
    rows = result.mappings().all()

    return [
        SucursalResponse(
            id_sucursal=r["id_sucursal"],
            nombre=r["nombre"],
            direccion=r["direccion"],
            telefono=r["telefono"],
            estado=r["estado"],
            fecha_creacion=r["fecha_creacion"],
        )
        for r in rows
    ]


@router.post(
    "/{almacen_id}/sucursales",
    response_model=SucursalAlmacenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_sucursal_to_almacen(
    almacen_id: int,
    payload: SucursalAlmacenCreate,
    current_user: CurrentUser = Depends(require_permission("create", "sucursales_almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Asigna un almacén a una sucursal (qué almacén atiende qué sucursal),
    validando que ambos pertenezcan a la empresa actual.

    - almacen_id viene del path
    - sucursal_id viene en el body
    """

    # Validar almacén de la empresa
    q_a = select(Almacen).where(
        Almacen.id_almacen == almacen_id,
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_a = await db.execute(q_a)
    almacen = res_a.scalar_one_or_none()
    if not almacen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Almacen does not belong to your company or does not exist",
        )

    # Validar sucursal de la empresa
    q_s = select(Sucursal).where(
        Sucursal.id_sucursal == payload.sucursal_id,
        Sucursal.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_s = await db.execute(q_s)
    sucursal = res_s.scalar_one_or_none()
    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sucursal does not belong to your company or does not exist",
        )

    # Crear el vínculo
    vinculo = SucursalAlmacen(
        sucursales_id_sucursal=payload.sucursal_id,
        almacenes_id_almacen=almacen_id,
    )
    db.add(vinculo)
    await db.flush()

    return SucursalAlmacenResponse(
        sucursales_id_sucursal=payload.sucursal_id,
        almacenes_id_almacen=almacen_id,
    )


@router.delete(
    "/{almacen_id}/sucursales/{sucursal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_sucursal_from_almacen(
    almacen_id: int,
    sucursal_id: int,
    current_user: CurrentUser = Depends(require_permission("delete", "sucursales_almacenes")),
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina un vínculo sucursal-almacén.
    """
    # Validar almacén de la empresa
    q_a = select(Almacen).where(
        Almacen.id_almacen == almacen_id,
        Almacen.empresas_id_empresa == current_user.empresa.id_empresa,
    )
    res_a = await db.execute(q_a)
    almacen = res_a.scalar_one_or_none()
    if not almacen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found in your company",
        )

    q = select(SucursalAlmacen).where(
        SucursalAlmacen.almacenes_id_almacen == almacen_id,
        SucursalAlmacen.sucursales_id_sucursal == sucursal_id,
    )
    result = await db.execute(q)
    vinculo = result.scalar_one_or_none()

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    await db.delete(vinculo)
    return None
