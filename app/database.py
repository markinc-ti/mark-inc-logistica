"""
Conexión a base de datos del proyecto Logística.

Es un proyecto INDEPENDIENTE de la app de tickets de TI: usa su propia
base de datos Postgres (puedes crear otro proyecto en Neon, gratis,
igual que hiciste con tickets) y se despliega como un Web Service
aparte en Render.

Configura la variable de entorno DATABASE_URL en Render con la cadena
de conexión de tu nueva base de Neon para "Logística".
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://usuario:password@localhost:5432/logistica"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
