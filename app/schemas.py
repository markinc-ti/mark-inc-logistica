"""
Esquemas Pydantic (request/response) del módulo de entregas e instalaciones.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .models import EstatusEntrega, RolUsuario


# ---------------------------------------------------------------------------
# Instaladores (usuarios)
# ---------------------------------------------------------------------------

class InstaladorCrear(BaseModel):
    nombre: str
    username: str
    password: str = Field(..., min_length=6)
    rol: RolUsuario = RolUsuario.instalador


class InstaladorEditar(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class InstaladorOut(BaseModel):
    id: str
    nombre: str
    username: str
    rol: RolUsuario
    activo: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Checklist — plantillas
# ---------------------------------------------------------------------------

class ChecklistItemPlantillaIn(BaseModel):
    texto: str
    orden: int = 0
    obligatorio: bool = True


class ChecklistPlantillaCrear(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    items: list[ChecklistItemPlantillaIn] = []


class ChecklistPlantillaEditar(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activa: Optional[bool] = None
    items: Optional[list[ChecklistItemPlantillaIn]] = None  # si se manda, reemplaza los items


class ChecklistItemPlantillaOut(ChecklistItemPlantillaIn):
    id: str

    class Config:
        from_attributes = True


class ChecklistPlantillaOut(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str]
    activa: bool
    items: list[ChecklistItemPlantillaOut]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Entregas
# ---------------------------------------------------------------------------

class EntregaCrear(BaseModel):
    cliente_nombre: str
    cliente_direccion: Optional[str] = None
    cliente_telefono: Optional[str] = None
    equipo_descripcion: str
    plantilla_origen_id: Optional[str] = None  # si se manda, copia esos items
    checklist_manual: Optional[list[ChecklistItemPlantillaIn]] = None  # o arma un checklist manual
    fecha_programada: Optional[datetime] = None
    instaladores_ids: list[str] = []
    folio_pedido_microsip: Optional[str] = None  # folio del pedido importado de Microsip, si aplica


class EntregaChecklistItemOut(BaseModel):
    id: str
    texto: str
    orden: int
    obligatorio: bool
    completado: bool
    agregado_en_sitio: bool

    class Config:
        from_attributes = True


class ChecklistItemAgregarEnSitio(BaseModel):
    texto: str
    obligatorio: bool = True


class ChecklistItemMarcar(BaseModel):
    completado: bool


class ChecklistItemEditarTexto(BaseModel):
    texto: str


class CambioEstatus(BaseModel):
    nuevo_estatus: EstatusEntrega
    comentario: Optional[str] = None
    # requerido si nuevo_estatus == rechazada
    motivo_rechazo: Optional[str] = None
    # requerido si nuevo_estatus == reagendada
    motivo_reagenda: Optional[str] = None
    nueva_fecha_programada: Optional[datetime] = None


class AsignarInstaladores(BaseModel):
    instaladores_ids: list[str]


class FirmaCrear(BaseModel):
    receptor_nombre: str
    receptor_puesto: Optional[str] = None
    firma_imagen_base64: str
    latitud: Optional[str] = None
    longitud: Optional[str] = None


class EntregaOut(BaseModel):
    id: str
    folio: str
    folio_pedido_microsip: Optional[str]
    cliente_nombre: str
    cliente_direccion: Optional[str]
    cliente_telefono: Optional[str]
    equipo_descripcion: str
    estatus: EstatusEntrega
    fecha_programada: Optional[datetime]
    creado_en: datetime
    motivo_rechazo: Optional[str]
    motivo_reagenda: Optional[str]
    checklist_items: list[EntregaChecklistItemOut] = []

    class Config:
        from_attributes = True
