# app/deps.py
from dataclasses import dataclass
from typing import List, Optional

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID

from app.database import get_db
from app.config import get_settings
from app.services.supabase_service import get_supabase_auth_client

settings = get_settings()


@dataclass
class EmpresaData:
    id_empresa: int
    nombre: str
    razon_social: str
    nit: str
    estado: bool


@dataclass
class UsuarioData:
    id_usuario: int
    auth_uid: UUID
    nombre: str
    apellido: str
    email: str
    es_dueno: bool
    estado: bool
    empresa: EmpresaData


@dataclass(frozen=True)
class PermisoData:
    id_permiso: int
    accion: str
    recurso: str


@dataclass
class RolData:
    id_rol: int
    nombre: str
    descripcion: Optional[str]


class CurrentUser:
    """Container para el usuario actual + empresa + roles + permisos."""

    def __init__(
        self,
        usuario: UsuarioData,
        empresa: EmpresaData,
        roles: List[RolData],
        permisos: List[PermisoData],
    ):
        self.usuario = usuario
        self.empresa = empresa
        self.roles = roles
        self.permisos = permisos

    def has_permission(self, action: str, resource: str) -> bool:
        # dueños tienen todo
        if self.usuario.es_dueno:
            return True
        for p in self.permisos:
            if p.accion == action and p.recurso == resource:
                return True
        return False


async def _get_current_user_from_token(
    access_token: str,
    db: AsyncSession,
) -> CurrentUser:
    """
    Valida el access_token con Supabase y arma el CurrentUser
    consultando directamente las tablas de auth en la BD:
    - usuarios
    - empresas
    - roles, usuarios_roles
    - permisos, roles_permisos
    """
    supabase = get_supabase_auth_client()

    try:
        # 1) Validar token con Supabase
        user_response = supabase.auth.get_user(access_token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        auth_uid = UUID(user_response.user.id)

        # 2) Buscar usuario + empresa en la base de datos
        user_sql = text(
            """
            SELECT 
                u.id_usuario,
                u.auth_uid,
                u.nombre,
                u.apellido,
                u.email,
                u.es_dueno,
                u.estado AS usuario_estado,
                e.id_empresa,
                e.nombre AS empresa_nombre,
                e.razon_social,
                e.nit,
                e.estado AS empresa_estado
            FROM usuarios u
            JOIN empresas e
                ON u.empresas_id_empresa = e.id_empresa
            WHERE u.auth_uid = :auth_uid
            LIMIT 1
            """
        )

        result = await db.execute(user_sql, {"auth_uid": str(auth_uid)})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not row.usuario_estado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        if not row.empresa_estado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company account is disabled",
            )

        empresa = EmpresaData(
            id_empresa=row.id_empresa,
            nombre=row.empresa_nombre,
            razon_social=row.razon_social,
            nit=row.nit,
            estado=row.empresa_estado,
        )

        usuario = UsuarioData(
            id_usuario=row.id_usuario,
            auth_uid=auth_uid,
            nombre=row.nombre,
            apellido=row.apellido,
            email=row.email,
            es_dueno=row.es_dueno,
            estado=row.usuario_estado,
            empresa=empresa,
        )

        # 3) Roles del usuario en esa empresa
        roles_sql = text(
            """
            SELECT 
                r.id_rol,
                r.nombre,
                r.descripcion
            FROM roles r
            JOIN usuarios_roles ur
                ON ur.roles_id_rol = r.id_rol
            WHERE ur.usuarios_id_usuario = :id_usuario
              AND r.empresas_id_empresa = :id_empresa
            """
        )

        roles_result = await db.execute(
            roles_sql,
            {
                "id_usuario": usuario.id_usuario,
                "id_empresa": empresa.id_empresa,
            },
        )
        roles_rows = roles_result.fetchall()

        roles: List[RolData] = [
            RolData(
                id_rol=r.id_rol,
                nombre=r.nombre,
                descripcion=r.descripcion,
            )
            for r in roles_rows
        ]

        # 4) Permisos desde roles
        permisos: List[PermisoData] = []
        if roles:
            roles_ids = [r.id_rol for r in roles]
            # Usamos ANY con array de ints (PostgreSQL)
            permisos_sql = text(
                """
                SELECT DISTINCT
                    p.id_permiso,
                    p.accion,
                    p.recurso
                FROM permisos p
                JOIN roles_permisos rp
                    ON rp.permisos_id_permiso = p.id_permiso
                WHERE rp.roles_id_rol = ANY(:roles_ids)
                """
            )
            permisos_result = await db.execute(
                permisos_sql,
                {"roles_ids": roles_ids},
            )
            permisos_rows = permisos_result.fetchall()
            permisos = [
                PermisoData(
                    id_permiso=p.id_permiso,
                    accion=p.accion,
                    recurso=p.recurso,
                )
                for p in permisos_rows
            ]

        return CurrentUser(
            usuario=usuario,
            empresa=empresa,
            roles=roles,
            permisos=permisos,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Lee el access_token desde la cookie y devuelve CurrentUser.
    """
    cookie_name = settings.cookie_name
    access_token = request.cookies.get(cookie_name)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - missing cookie",
        )

    return await _get_current_user_from_token(access_token, db)


def require_permission(action: str, resource: str):
    """
    Dependency factory para exigir un permiso (acción + recurso).
    Ejemplo:
        current_user: CurrentUser = Depends(require_permission("read", "sucursales"))
    """

    async def permission_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_permission(action, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action} on {resource}",
            )
        return current_user

    return permission_checker
