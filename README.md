# Logística — Mark·Inc

Proyecto **independiente** de la app de tickets de TI (aunque es de la
misma empresa): entrega de equipos e instalaciones, con checklist
administrable, firma del receptor, estatus de entrega e instaladores
con usuario/contraseña propios.

## Estructura

```
logistica/
├── app/
│   ├── main.py            # punto de entrada FastAPI
│   ├── database.py        # conexión a Postgres (propia, separada de tickets)
│   ├── auth.py             # login, JWT, hashing de contraseñas
│   ├── models.py           # modelos SQLAlchemy
│   ├── schemas.py          # esquemas Pydantic
│   ├── routes.py           # endpoints de entregas/checklists/instaladores
│   └── notificaciones.py   # envío de WhatsApp (Twilio)
├── branding.css            # paleta de colores azul/naranja
└── requirements.txt
```

## Colores de marca

Azul y naranja — distintos al rojo/gris de la app de tickets. Están
definidos como variables CSS en `branding.css`:

- **Azul primario** `#1B4F91` — header, botones principales, links.
- **Naranja** `#FF7A29` — acciones, badge de "en camino".
- Cada estatus de entrega tiene su propio color de acento (ver el
  archivo) para que se distingan de un vistazo en la lista de entregas.

## Cómo desplegarlo (mismo patrón que usaste con tickets)

1. **Base de datos**: crea un proyecto **nuevo** en Neon (gratis) — no
   uses la misma base que tickets, para mantenerlos independientes.
   Copia la cadena de conexión.

2. **Repositorio**: sube esta carpeta a un repo nuevo en GitHub (ej.
   `mark-inc-logistica`).

3. **Render**: crea un **nuevo Web Service** apartado del de tickets,
   conectado a ese repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Variables de entorno:
     - `DATABASE_URL` → la cadena de conexión de tu nuevo Neon
     - `LOGISTICA_SECRET_KEY` → una clave secreta larga y aleatoria
     - (opcional, cuando actives Twilio) `TWILIO_ACCOUNT_SID`,
       `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`

4. Al arrancar, la app crea las tablas automáticamente
   (`Base.metadata.create_all`), igual que hiciste en tickets antes de
   pasar a Alembic si decides usarlo después.

5. **Primer usuario admin**: como aún no hay nadie en la base, crea el
   primer admin directamente en Neon (SQL) o agrega un script único de
   arranque — dime si quieres que te lo prepare.

6. Igual que con tickets, puedes convertirla en **PWA instalable**
   desde el celular más adelante.

## Endpoints principales

Ver el detalle completo de rutas en el código (`app/routes.py` y
`app/auth.py`). En resumen:

- `POST /auth/login` — login, devuelve JWT
- `POST /entregas/instaladores` — admin crea instaladores
- `POST /entregas/checklists` — admin crea/edita plantillas de checklist
- `POST /entregas` — admin o ventas/almacén crea una entrega
- `POST /entregas/{id}/instaladores` — asigna uno o varios instaladores
- `PATCH /entregas/{id}/checklist/items/{item_id}/marcar` — marcar ítem
- `POST /entregas/{id}/estatus` — cambia estatus (valida transición)
- `POST /entregas/{id}/firma` — firma del receptor, cierra la entrega

## Pendientes / siguientes pasos

- Frontend (PWA) con la paleta azul/naranja: pantalla de instalador con
  checklist y `<canvas>` para firma.
- Activar Twilio para que las notificaciones de WhatsApp salgan de
  verdad (puedes usar la misma cuenta que planeaste para tickets).
- Script para crear el primer usuario admin.
