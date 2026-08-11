"""
Modelos SQLAlchemy del proyecto "Logística" (Mark·Inc).

Proyecto INDEPENDIENTE de la app de tickets de TI: tiene su propia
tabla de usuarios, su propia base de datos y su propio despliegue.
"""

from datetime import datetime
import enum
import uuid

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Roles y estatus
# ---------------------------------------------------------------------------

class RolUsuario(str, enum.Enum):
    admin = "admin"
    instalador = "instalador"
    ventas_almacen = "ventas_almacen"


class EstatusEntrega(str, enum.Enum):
    pendiente = "pendiente"
    asignada = "asignada"
    en_camino = "en_camino"
    en_proceso = "en_proceso"
    entregada = "entregada"
    rechazada = "rechazada"
    reagendada = "reagendada"
    cancelada = "cancelada"


TRANSICIONES_VALIDAS = {
    EstatusEntrega.pendiente: {EstatusEntrega.asignada, EstatusEntrega.cancelada},
    EstatusEntrega.asignada: {EstatusEntrega.en_camino, EstatusEntrega.reagendada, EstatusEntrega.cancelada},
    EstatusEntrega.en_camino: {EstatusEntrega.en_proceso, EstatusEntrega.rechazada, EstatusEntrega.reagendada},
    EstatusEntrega.en_proceso: {EstatusEntrega.entregada, EstatusEntrega.rechazada, EstatusEntrega.reagendada},
    EstatusEntrega.rechazada: {EstatusEntrega.reagendada, EstatusEntrega.cancelada},
    EstatusEntrega.reagendada: {EstatusEntrega.asignada, EstatusEntrega.en_camino},
    EstatusEntrega.entregada: set(),
    EstatusEntrega.cancelada: set(),
}


# ---------------------------------------------------------------------------
# Usuario (propio de este proyecto)
# ---------------------------------------------------------------------------

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nombre = Column(String(150), nullable=False)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    telefono = Column(String(30), nullable=True)  # para notificaciones WhatsApp
    rol = Column(SAEnum(RolUsuario), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    entregas_asignadas = relationship("EntregaInstalador", back_populates="instalador")


# ---------------------------------------------------------------------------
# Checklists administrables (plantillas)
# ---------------------------------------------------------------------------

class ChecklistPlantilla(Base):
    __tablename__ = "checklist_plantillas"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)
    creado_por_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship(
        "ChecklistItemPlantilla", back_populates="plantilla",
        order_by="ChecklistItemPlantilla.orden", cascade="all, delete-orphan",
    )


class ChecklistItemPlantilla(Base):
    __tablename__ = "checklist_items_plantilla"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    plantilla_id = Column(UUID(as_uuid=False), ForeignKey("checklist_plantillas.id"), nullable=False)
    texto = Column(String(300), nullable=False)
    orden = Column(Integer, default=0, nullable=False)
    obligatorio = Column(Boolean, default=True, nullable=False)

    plantilla = relationship("ChecklistPlantilla", back_populates="items")


# ---------------------------------------------------------------------------
# Entregas
# ---------------------------------------------------------------------------

class Entrega(Base):
    __tablename__ = "entregas"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    folio = Column(String(20), unique=True, nullable=False)
    folio_pedido_microsip = Column(String(30), unique=True, nullable=True, index=True)

    cliente_nombre = Column(String(200), nullable=False)
    cliente_direccion = Column(Text, nullable=True)
    cliente_telefono = Column(String(30), nullable=True)
    equipo_descripcion = Column(Text, nullable=False)

    plantilla_origen_id = Column(UUID(as_uuid=False), ForeignKey("checklist_plantillas.id"), nullable=True)
    estatus = Column(SAEnum(EstatusEntrega), default=EstatusEntrega.pendiente, nullable=False)

    creado_por_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fecha_programada = Column(DateTime, nullable=True)
    motivo_rechazo = Column(Text, nullable=True)
    motivo_reagenda = Column(Text, nullable=True)

    checklist_items = relationship(
        "EntregaChecklistItem", back_populates="entrega",
        cascade="all, delete-orphan", order_by="EntregaChecklistItem.orden",
    )
    instaladores = relationship(
        "EntregaInstalador", back_populates="entrega", cascade="all, delete-orphan"
    )
    firma = relationship(
        "Firma", back_populates="entrega", uselist=False, cascade="all, delete-orphan"
    )
    historial = relationship(
        "EntregaHistorial", back_populates="entrega",
        cascade="all, delete-orphan", order_by="EntregaHistorial.creado_en",
    )


class EntregaInstalador(Base):
    __tablename__ = "entrega_instaladores"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entrega_id = Column(UUID(as_uuid=False), ForeignKey("entregas.id"), nullable=False)
    instalador_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    asignado_en = Column(DateTime, default=datetime.utcnow)

    entrega = relationship("Entrega", back_populates="instaladores")
    instalador = relationship("Usuario", back_populates="entregas_asignadas")


class EntregaChecklistItem(Base):
    __tablename__ = "entrega_checklist_items"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entrega_id = Column(UUID(as_uuid=False), ForeignKey("entregas.id"), nullable=False)
    texto = Column(String(300), nullable=False)
    orden = Column(Integer, default=0, nullable=False)
    obligatorio = Column(Boolean, default=True, nullable=False)
    completado = Column(Boolean, default=False, nullable=False)
    completado_por_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=True)
    completado_en = Column(DateTime, nullable=True)
    agregado_en_sitio = Column(Boolean, default=False, nullable=False)

    entrega = relationship("Entrega", back_populates="checklist_items")


class Firma(Base):
    __tablename__ = "firmas"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entrega_id = Column(UUID(as_uuid=False), ForeignKey("entregas.id"), unique=True, nullable=False)

    receptor_nombre = Column(String(200), nullable=False)
    receptor_puesto = Column(String(150), nullable=True)
    firma_imagen_base64 = Column(Text, nullable=False)
    firmado_en = Column(DateTime, default=datetime.utcnow)
    latitud = Column(String(30), nullable=True)
    longitud = Column(String(30), nullable=True)

    entrega = relationship("Entrega", back_populates="firma")


class EntregaHistorial(Base):
    __tablename__ = "entrega_historial"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entrega_id = Column(UUID(as_uuid=False), ForeignKey("entregas.id"), nullable=False)
    estatus_anterior = Column(SAEnum(EstatusEntrega), nullable=True)
    estatus_nuevo = Column(SAEnum(EstatusEntrega), nullable=False)
    comentario = Column(Text, nullable=True)
    usuario_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    entrega = relationship("Entrega", back_populates="historial")
