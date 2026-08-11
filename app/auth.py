"""
Autenticación propia del proyecto Logística (independiente de tickets).

Login con usuario/contraseña -> devuelve un JWT. Cada usuario tiene un
rol: admin, instalador, ventas_almacen.
"""

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario

SECRET_KEY = os.environ.get("LOGISTICA_SECRET_KEY", "cambia-esta-clave-en-produccion")
ALGORITHM = "HS256"
TOKEN_EXPIRA_MINUTOS = 60 * 12  # 12 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def crear_token(usuario: Usuario) -> str:
    payload = {
        "sub": usuario.id,
        "username": usuario.username,
        "rol": usuario.rol.value,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRA_MINUTOS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    credenciales_invalidas = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "No se pudo validar la sesión",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("sub")
        if usuario_id is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    usuario = db.query(Usuario).get(usuario_id)
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas
    return usuario


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter_by(username=form_data.username).first()
    if not usuario or not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")
    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario desactivado")

    return {
        "access_token": crear_token(usuario),
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "rol": usuario.rol.value,
        },
    }
