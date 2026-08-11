"""
Script para crear el primer usuario ADMIN del proyecto Logística.

Cómo usarlo:

1. Local (apuntando a tu base de Neon):
   Configura la variable de entorno DATABASE_URL con la cadena de
   conexión de tu base de Neon para Logística, luego corre:

       pip install -r requirements.txt
       python crear_admin.py

2. En Render (si prefieres correrlo ahí una sola vez):
   Puedes usar la "Shell" del servicio en Render (una vez desplegado)
   y correr: python crear_admin.py
   Ya tendrá DATABASE_URL configurada porque es la misma variable de
   entorno del servicio.

El script pregunta nombre, username y contraseña por consola. Si el
username ya existe, te avisa y no crea un duplicado.
"""

import getpass
import sys

from app.database import SessionLocal, engine
from app.models import Base, Usuario, RolUsuario
from app.auth import hash_password


def main():
    print("== Crear primer usuario admin — Logística ==")

    # Asegura que las tablas existan (por si corres esto antes del primer arranque de la app)
    Base.metadata.create_all(bind=engine)

    nombre = input("Nombre completo: ").strip()
    username = input("Username: ").strip()

    if not nombre or not username:
        print("Nombre y username son obligatorios.")
        sys.exit(1)

    password = getpass.getpass("Contraseña: ")
    password_confirm = getpass.getpass("Confirma la contraseña: ")

    if password != password_confirm:
        print("Las contraseñas no coinciden.")
        sys.exit(1)

    if len(password) < 6:
        print("La contraseña debe tener al menos 6 caracteres.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existente = db.query(Usuario).filter_by(username=username).first()
        if existente:
            print(f"Ya existe un usuario con username '{username}'. No se creó nada.")
            sys.exit(1)

        admin = Usuario(
            nombre=nombre,
            username=username,
            password_hash=hash_password(password),
            rol=RolUsuario.admin,
            activo=True,
        )
        db.add(admin)
        db.commit()
        print(f"\n✅ Usuario admin '{username}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
