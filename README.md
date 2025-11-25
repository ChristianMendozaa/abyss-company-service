# Company Service

Microservicio encargado de la gestión de:
- Sucursales
- Almacenes
- Asignaciones Usuario–Sucursal
- Asignaciones Sucursal–Almacén

Incluye autorización RBAC mediante comunicación con el Auth Service.

---

## 1. Descripción General

El Company Service forma parte de un ecosistema de microservicios junto con el Auth Service.
Su responsabilidad es administrar toda la estructura organizacional de una empresa:

- Crear, listar, actualizar y eliminar sucursales
- Crear, listar, actualizar y eliminar almacenes
- Asignar empleados a sucursales
- Asignar almacenes a sucursales
- Consultar qué usuarios están en una sucursal
- Consultar qué almacenes están vinculados a una sucursal y viceversa

### Seguridad

El acceso a cada endpoint se controla por permisos usando el Auth Service.
Los permisos se reciben en el JWT y se evalúan antes de cada operación.

---

## 2. Arquitectura y Estructura del Proyecto

```
company-service/
├── app/
│   ├── main.py               → Inicializa FastAPI y monta routers
│   ├── config.py             → Configuración de entorno
│   ├── database.py           → Conexión async con SQLAlchemy
│   ├── deps.py               → Comunicación con Auth Service + permisos
│   ├── models/               → Modelos SQLAlchemy
│   │   ├── sucursal.py
│   │   ├── almacen.py
│   │   ├── usuario_sucursal.py
│   │   ├── sucursal_almacen.py
│   ├── schemas/              → Schemas Pydantic
│   ├── routers/
│   │   ├── sucursales.py
│   │   └── almacenes.py
└── requirements.txt
```

---

## 3. Base de Datos

### Tablas esperadas:

#### SUCURSALES
- `id_sucursal` (PK)
- `nombre`
- `direccion`
- `telefono`
- `estado`
- `fecha_creacion`
- `empresas_id_empresa` (FK)

#### ALMACENES
- `id_almacen` (PK)
- `nombre`
- `descripcion`
- `es_principal`
- `estado`
- `fecha_creacion`
- `empresas_id_empresa` (FK)

#### USUARIOS_SUCURSALES
- `usuarios_id_usuario` (PK, FK → usuarios.id_usuario del Auth Service)
- `sucursales_id_sucursal` (PK, FK → sucursales.id_sucursal)

#### SUCURSALES_ALMACENES
- `sucursales_id_sucursal` (PK)
- `almacenes_id_almacen` (PK)

---

## 4. Auth Service Integration (RBAC)

Cada request pasa por:

- **`get_current_user()`**
    → valida token del Auth Service
    → obtiene:
        - usuario
        - empresa
        - permisos

- **`require_permission(accion, recurso)`**
    → valida que el usuario tenga:
        - `accion`: `"create"`, `"read"`, `"update"`, `"delete"`
        - `recurso`: nombre de tabla (`"sucursales"`, `"almacenes"`, etc.)

**Nota:** Dueños (`es_dueno=true`) tienen acceso completo.

---

## 5. Endpoints del Microservicio

### 5.1 Sucursales (`/sucursales`)

#### `POST /sucursales`
- **Permiso:** `create` → `sucursales`
- **Descripción:** Crea una sucursal perteneciente a la empresa del usuario.

#### `GET /sucursales`
- **Permiso:** `read` → `sucursales`
- **Descripción:** Lista todas las sucursales de la empresa.

#### `GET /sucursales/{id}`
- **Permiso:** `read` → `sucursales`
- **Descripción:** Obtiene una sucursal específica.

#### `PATCH /sucursales/{id}`
- **Permiso:** `update` → `sucursales`
- **Descripción:** Actualiza campos de una sucursal.

#### `DELETE /sucursales/{id}`
- **Permiso:** `delete` → `sucursales`
- **Descripción:** Soft delete: cambia estado a `false`.

### Asignación Usuario–Sucursal

#### `POST /sucursales/{id}/usuarios`
- **Permiso:** `create` → `usuarios_sucursales`
- **Descripción:** Asigna un usuario a una sucursal.

#### `GET /sucursales/{id}/usuarios`
- **Permiso:** `read` → `usuarios_sucursales`
- **Descripción:** Devuelve la lista completa de empleados asignados.

#### `DELETE /sucursales/{id}/usuarios/{usuario_id}`
- **Permiso:** `delete` → `usuarios_sucursales`
- **Descripción:** Quita un usuario de una sucursal.

### Listado de almacenes para una sucursal

#### `GET /sucursales/{id}/almacenes`
- **Permiso:** `read` → `sucursales_almacenes`
- **Descripción:** Devuelve almacenes vinculados a esa sucursal.

---

### 5.2 Almacenes (`/almacenes`)

#### `POST /almacenes`
- **Permiso:** `create` → `almacenes`
- **Descripción:** Crea un almacén y lo asigna a una sucursal.

#### `GET /almacenes`
- **Permiso:** `read` → `almacenes`
- **Descripción:** Lista todos los almacenes de la empresa.

#### `GET /almacenes/{id}`
- **Permiso:** `read` → `almacenes`
- **Descripción:** Obtiene un almacén específico.

#### `PATCH /almacenes/{id}`
- **Permiso:** `update` → `almacenes`
- **Descripción:** Actualiza un almacén.

#### `DELETE /almacenes/{id}`
- **Permiso:** `delete` → `almacenes`
- **Descripción:** Soft delete: `estado = false`.

### Asignación Sucursal–Almacén

#### `POST /almacenes/{id}/sucursales`
- **Permiso:** `create` → `sucursales_almacenes`
- **Descripción:** Asigna un almacén a una sucursal.

#### `GET /almacenes/{id}/sucursales`
- **Permiso:** `read` → `sucursales_almacenes`
- **Descripción:** Lista sucursales atendidas por ese almacén.

#### `DELETE /almacenes/{id}/sucursales/{sucursal_id}`
- **Permiso:** `delete` → `sucursales_almacenes`
- **Descripción:** Elimina la asignación.

---

## 6. Ejemplos de Requests

### Crear sucursal

```http
POST /sucursales
```

```json
{
  "nombre": "Sucursal Central",
  "direccion": "Av. Siempre Viva 123",
  "telefono": "78945612"
}
```

### Crear almacén asignado a sucursal

```http
POST /almacenes
```

```json
{
  "nombre": "Almacén Principal",
  "descripcion": "Central",
  "es_principal": true,
  "sucursal_id": 1
}
```

### Asignar usuario a sucursal

```http
POST /sucursales/1/usuarios
```

```json
{
  "usuarios_id_usuario": 6,
  "sucursales_id_sucursal": 1
}
```

---

## 7. Errores Comunes

- **`404 Branch not found in your company`**  
  La sucursal no pertenece al usuario autenticado.

- **`400 Sucursal does not belong to your company`**  
  Intento de asignar entidades entre empresas distintas.

- **`403 Permission denied`**  
  El usuario no tiene permisos suficientes.

---

## 8. Notas Importantes

- Los IDs de empresa nunca vienen del cliente → siempre del Auth Service.
- Dueños tienen permisos completos sin excepción.
- Los permisos deben declararse en el Auth Service.
- El servicio no gestiona usuarios → solo recibe IDs.
