"""
Endpoints FastAPI del proyecto "Logística" (Mark·Inc) — proyecto
independiente de la app de tickets de TI, con su propio login,
base de datos y despliegue.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .models import (
    Usuario, RolUsuario, ChecklistPlantilla, ChecklistItemPlantilla,
    Entrega, EntregaChecklistItem, EntregaInstalador, Firma,
    EntregaHistorial, EstatusEntrega, TRANSICIONES_VALIDAS,
)
from .schemas import (
    InstaladorCrear, InstaladorEditar, InstaladorOut,
    ChecklistPlantillaCrear, ChecklistPlantillaEditar, ChecklistPlantillaOut,
    EntregaCrear, EntregaOut, ChecklistItemAgregarEnSitio, ChecklistItemMarcar,
    ChecklistItemEditarTexto, CambioEstatus, AsignarInstaladores, FirmaCrear,
)
from .database import get_db
from .auth import get_current_user, hash_password
from .notificaciones import enviar_whatsapp

router = APIRouter(prefix="/entregas", tags=["Entregas e Instalaciones"])


def requiere_rol(*roles: RolUsuario):
    def _dep(usuario: Usuario = Depends(get_current_user)):
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return usuario
    return _dep


def generar_folio(db: Session) -> str:
    total = db.query(Entrega).count() + 1
    return f"LOG-{total:06d}"


# ---------------------------------------------------------------------------
# Instaladores (usuarios) — solo admin
# ---------------------------------------------------------------------------

@router.post("/instaladores", response_model=InstaladorOut)
def crear_instalador(
    datos: InstaladorCrear,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requiere_rol(RolUsuario.admin)),
):
    if db.query(Usuario).filter_by(username=datos.username).first():
        raise HTTPException(400, "Ese username ya existe")
    nuevo = Usuario(
        nombre=datos.nombre,
        username=datos.username,
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/instaladores", response_model=list[InstaladorOut])
def listar_instaladores(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requiere_rol(RolUsuario.admin, RolUsuario.ventas_almacen)),
):
    return db.query(Usuario).filter(
        Usuario.rol.in_([RolUsuario.instalador])
    ).order_by(Usuario.nombre).all()


@router.patch("/instaladores/{instalador_id}", response_model=InstaladorOut)
def editar_instalador(
    instalador_id: str,
    datos: InstaladorEditar,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requiere_rol(RolUsuario.admin)),
):
    instalador = db.query(Usuario).get(instalador_id)
    if not instalador:
        raise HTTPException(404, "Instalador no encontrado")
    if datos.nombre is not None:
        instalador.nombre = datos.nombre
    if datos.activo is not None:
        instalador.activo = datos.activo
    if datos.password:
        instalador.password_hash = hash_password(datos.password)
    db.commit()
    db.refresh(instalador)
    return instalador


# ---------------------------------------------------------------------------
# Checklists — plantillas administrables (solo admin)
# ---------------------------------------------------------------------------

@router.post("/checklists", response_model=ChecklistPlantillaOut)
def crear_plantilla(
    datos: ChecklistPlantillaCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requiere_rol(RolUsuario.admin)),
):
    plantilla = ChecklistPlantilla(
        nombre=datos.nombre, descripcion=datos.descripcion, creado_por_id=admin.id
    )
    db.add(plantilla)
    db.flush()  # para obtener plantilla.id antes del commit
    for item in datos.items:
        db.add(ChecklistItemPlantilla(
            plantilla_id=plantilla.id, texto=item.texto,
            orden=item.orden, obligatorio=item.obligatorio,
        ))
    db.commit()
    db.refresh(plantilla)
    return plantilla


@router.get("/checklists", response_model=list[ChecklistPlantillaOut])
def listar_plantillas(
    db: Session = Depends(get_db),
    _u: Usuario = Depends(get_current_user),
):
    return db.query(ChecklistPlantilla).filter_by(activa=True).all()


@router.patch("/checklists/{plantilla_id}", response_model=ChecklistPlantillaOut)
def editar_plantilla(
    plantilla_id: str,
    datos: ChecklistPlantillaEditar,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requiere_rol(RolUsuario.admin)),
):
    plantilla = db.query(ChecklistPlantilla).get(plantilla_id)
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")
    if datos.nombre is not None:
        plantilla.nombre = datos.nombre
    if datos.descripcion is not None:
        plantilla.descripcion = datos.descripcion
    if datos.activa is not None:
        plantilla.activa = datos.activa
    if datos.items is not None:
        # reemplaza todos los items de la plantilla
        for item in list(plantilla.items):
            db.delete(item)
        db.flush()
        for item in datos.items:
            db.add(ChecklistItemPlantilla(
                plantilla_id=plantilla.id, texto=item.texto,
                orden=item.orden, obligatorio=item.obligatorio,
            ))
    db.commit()
    db.refresh(plantilla)
    return plantilla


# ---------------------------------------------------------------------------
# Entregas
# ---------------------------------------------------------------------------

@router.post("", response_model=EntregaOut)
def crear_entrega(
    datos: EntregaCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(RolUsuario.admin, RolUsuario.ventas_almacen)),
):
    entrega = Entrega(
        folio=generar_folio(db),
        cliente_nombre=datos.cliente_nombre,
        cliente_direccion=datos.cliente_direccion,
        cliente_telefono=datos.cliente_telefono,
        equipo_descripcion=datos.equipo_descripcion,
        plantilla_origen_id=datos.plantilla_origen_id,
        fecha_programada=datos.fecha_programada,
        creado_por_id=usuario.id,
        estatus=EstatusEntrega.pendiente,
    )
    db.add(entrega)
    db.flush()

    # copia el checklist desde la plantilla, o usa uno manual
    items_fuente = []
    if datos.plantilla_origen_id:
        plantilla = db.query(ChecklistPlantilla).get(datos.plantilla_origen_id)
        if not plantilla:
            raise HTTPException(404, "Plantilla de checklist no encontrada")
        items_fuente = plantilla.items
    elif datos.checklist_manual:
        items_fuente = datos.checklist_manual

    for item in items_fuente:
        db.add(EntregaChecklistItem(
            entrega_id=entrega.id, texto=item.texto,
            orden=item.orden, obligatorio=item.obligatorio,
        ))

    # asigna instaladores si se mandaron desde la creación
    for instalador_id in datos.instaladores_ids:
        db.add(EntregaInstalador(entrega_id=entrega.id, instalador_id=instalador_id))
    if datos.instaladores_ids:
        entrega.estatus = EstatusEntrega.asignada

    db.add(EntregaHistorial(
        entrega_id=entrega.id, estatus_anterior=None,
        estatus_nuevo=entrega.estatus, usuario_id=usuario.id,
        comentario="Entrega creada",
    ))
    db.commit()
    db.refresh(entrega)

    _notificar_instaladores(db, entrega, "Se te asignó una nueva entrega")
    return entrega


@router.get("", response_model=list[EntregaOut])
def listar_entregas(
    estatus: EstatusEntrega | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    q = db.query(Entrega)
    if usuario.rol == RolUsuario.instalador:
        q = q.join(EntregaInstalador).filter(EntregaInstalador.instalador_id == usuario.id)
    if estatus:
        q = q.filter(Entrega.estatus == estatus)
    return q.order_by(Entrega.creado_en.desc()).all()


@router.get("/{entrega_id}", response_model=EntregaOut)
def obtener_entrega(
    entrega_id: str, db: Session = Depends(get_db),
    _u: Usuario = Depends(get_current_user),
):
    entrega = db.query(Entrega).get(entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega no encontrada")
    return entrega


@router.post("/{entrega_id}/instaladores")
def asignar_instaladores(
    entrega_id: str, datos: AsignarInstaladores,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(RolUsuario.admin, RolUsuario.ventas_almacen)),
):
    entrega = db.query(Entrega).get(entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega no encontrada")

    # reemplaza la lista de instaladores asignados
    for asignacion in list(entrega.instaladores):
        db.delete(asignacion)
    for instalador_id in datos.instaladores_ids:
        db.add(EntregaInstalador(entrega_id=entrega.id, instalador_id=instalador_id))

    if entrega.estatus == EstatusEntrega.pendiente and datos.instaladores_ids:
        entrega.estatus = EstatusEntrega.asignada
        db.add(EntregaHistorial(
            entrega_id=entrega.id, estatus_anterior=EstatusEntrega.pendiente,
            estatus_nuevo=EstatusEntrega.asignada, usuario_id=usuario.id,
        ))
    db.commit()
    _notificar_instaladores(db, entrega, "Se actualizó tu asignación de entrega")
    return {"ok": True}


# --- checklist en sitio -----------------------------------------------------

@router.post("/{entrega_id}/checklist/items")
def agregar_item_en_sitio(
    entrega_id: str, datos: ChecklistItemAgregarEnSitio,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(RolUsuario.instalador, RolUsuario.admin)),
):
    entrega = db.query(Entrega).get(entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega no encontrada")
    orden = len(entrega.checklist_items) + 1
    item = EntregaChecklistItem(
        entrega_id=entrega.id, texto=datos.texto, orden=orden,
        obligatorio=datos.obligatorio, agregado_en_sitio=True,
    )
    db.add(item)
    db.commit()
    return {"ok": True, "item_id": item.id}


@router.patch("/{entrega_id}/checklist/items/{item_id}/texto")
def editar_texto_item(
    entrega_id: str, item_id: str, datos: ChecklistItemEditarTexto,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(requiere_rol(RolUsuario.instalador, RolUsuario.admin)),
):
    item = db.query(EntregaChecklistItem).filter_by(id=item_id, entrega_id=entrega_id).first()
    if not item:
        raise HTTPException(404, "Ítem no encontrado")
    item.texto = datos.texto
    db.commit()
    return {"ok": True}


@router.patch("/{entrega_id}/checklist/items/{item_id}/marcar")
def marcar_item(
    entrega_id: str, item_id: str, datos: ChecklistItemMarcar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(RolUsuario.instalador, RolUsuario.admin)),
):
    item = db.query(EntregaChecklistItem).filter_by(id=item_id, entrega_id=entrega_id).first()
    if not item:
        raise HTTPException(404, "Ítem no encontrado")
    item.completado = datos.completado
    item.completado_por_id = usuario.id if datos.completado else None
    item.completado_en = datetime.utcnow() if datos.completado else None
    db.commit()

    entrega = item.entrega
    if entrega.estatus in (EstatusEntrega.asignada, EstatusEntrega.en_camino):
        entrega.estatus = EstatusEntrega.en_proceso
        db.commit()
    return {"ok": True}


# --- cambio de estatus -------------------------------------------------------

@router.post("/{entrega_id}/estatus")
def cambiar_estatus(
    entrega_id: str, datos: CambioEstatus,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    entrega = db.query(Entrega).get(entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega no encontrada")

    permitidos = TRANSICIONES_VALIDAS.get(entrega.estatus, set())
    if datos.nuevo_estatus not in permitidos:
        raise HTTPException(
            400,
            f"No se puede pasar de '{entrega.estatus.value}' a '{datos.nuevo_estatus.value}'",
        )

    if datos.nuevo_estatus == EstatusEntrega.rechazada and not datos.motivo_rechazo:
        raise HTTPException(400, "motivo_rechazo es obligatorio para rechazar la entrega")
    if datos.nuevo_estatus == EstatusEntrega.reagendada and not datos.motivo_reagenda:
        raise HTTPException(400, "motivo_reagenda es obligatorio para reagendar")

    anterior = entrega.estatus
    entrega.estatus = datos.nuevo_estatus
    if datos.motivo_rechazo:
        entrega.motivo_rechazo = datos.motivo_rechazo
    if datos.motivo_reagenda:
        entrega.motivo_reagenda = datos.motivo_reagenda
    if datos.nueva_fecha_programada:
        entrega.fecha_programada = datos.nueva_fecha_programada

    db.add(EntregaHistorial(
        entrega_id=entrega.id, estatus_anterior=anterior,
        estatus_nuevo=datos.nuevo_estatus, usuario_id=usuario.id,
        comentario=datos.comentario,
    ))
    db.commit()

    if datos.nuevo_estatus == EstatusEntrega.reagendada:
        _notificar_instaladores(db, entrega, "La entrega fue reagendada")
    return {"ok": True, "estatus": entrega.estatus}


# --- firma de conformidad ----------------------------------------------------

@router.post("/{entrega_id}/firma")
def firmar_entrega(
    entrega_id: str, datos: FirmaCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(RolUsuario.instalador, RolUsuario.admin)),
):
    entrega = db.query(Entrega).get(entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega no encontrada")
    if entrega.estatus not in (EstatusEntrega.en_proceso, EstatusEntrega.en_camino):
        raise HTTPException(400, "La entrega debe estar en proceso para poder firmarse")

    pendientes = [i for i in entrega.checklist_items if i.obligatorio and not i.completado]
    if pendientes:
        raise HTTPException(
            400,
            f"Hay {len(pendientes)} ítem(s) obligatorio(s) sin completar en el checklist",
        )

    firma = Firma(
        entrega_id=entrega.id,
        receptor_nombre=datos.receptor_nombre,
        receptor_puesto=datos.receptor_puesto,
        firma_imagen_base64=datos.firma_imagen_base64,
        latitud=datos.latitud,
        longitud=datos.longitud,
    )
    db.add(firma)

    anterior = entrega.estatus
    entrega.estatus = EstatusEntrega.entregada
    db.add(EntregaHistorial(
        entrega_id=entrega.id, estatus_anterior=anterior,
        estatus_nuevo=EstatusEntrega.entregada, usuario_id=usuario.id,
        comentario=f"Firmada por {datos.receptor_nombre}",
    ))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Notificaciones WhatsApp
# ---------------------------------------------------------------------------

def _notificar_instaladores(db: Session, entrega: Entrega, mensaje: str):
    """
    Reutiliza la misma función enviar_whatsapp() que ya tienes lista en la
    app de tickets (pendiente de activar la cuenta de Twilio). No falla la
    petición si el envío falla — solo lo registra.
    """
    for asignacion in entrega.instaladores:
        instalador = asignacion.instalador
        try:
            enviar_whatsapp(
                instalador,  # tu función ya sabe sacar el teléfono del usuario
                f"{mensaje}: {entrega.folio} — {entrega.cliente_nombre}",
            )
        except Exception:
            # no interrumpe el flujo si Twilio aún no está configurado
            pass
