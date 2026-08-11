"""
Notificaciones por WhatsApp del proyecto Logística.

Usa Twilio, igual que dejaste planeado en la app de tickets. Puedes usar
la MISMA cuenta de Twilio (cuando la actives) para ambos proyectos, solo
configura estas variables de entorno aquí también:

    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_WHATSAPP_FROM   (ej. "whatsapp:+14155238886")

Mientras no esté configurado, enviar_whatsapp() simplemente no hace nada
(no truena la app).
"""

import os
from .models import Usuario

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")


def enviar_whatsapp(usuario: Usuario, mensaje: str) -> None:
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
        return  # Twilio aún no configurado — no truena, solo no envía

    from twilio.rest import Client  # import perezoso para no exigir el paquete si no se usa

    telefono = getattr(usuario, "telefono", None)
    if not telefono:
        return

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=f"whatsapp:{telefono}",
        body=mensaje,
    )
