"""
Logística — Mark·Inc
Proyecto independiente para entrega de equipos e instalaciones.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from .models import Base
from .auth import router as auth_router
from .routes import router as entregas_router

app = FastAPI(
    title="Logística — Mark·Inc",
    description="Entrega de equipos e instalaciones: checklist administrable, "
                 "firma del receptor, estatus de entrega e instaladores.",
    version="1.0.0",
)

# En desarrollo puedes dejar "*"; en producción restringe al dominio real
# de tu frontend (ej. la PWA en tu subdominio de Logística).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(entregas_router)


@app.on_event("startup")
def crear_tablas():
    # Igual que en la app de tickets: crea las tablas si no existen.
    # Si más adelante usas Alembic, puedes quitar esta línea.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def raiz():
    return {"app": "Logística", "empresa": "Mark·Inc", "estatus": "ok"}
