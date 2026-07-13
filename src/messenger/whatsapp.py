"""
Messenger: Envío de mensajes por WhatsApp via Twilio.
"""

from twilio.rest import Client


class WhatsAppSender:
    """Envía mensajes por WhatsApp usando Twilio."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Número WhatsApp de Twilio (ej: "whatsapp:+14155238886")
        """
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def send_message(self, to_number: str, body: str) -> str:
        """
        Envía un mensaje de WhatsApp.
        
        Args:
            to_number: Número destino (ej: "whatsapp:+569XXXXXXXX")
            body: Texto del mensaje (máximo ~4096 chars)
            
        Returns:
            SID del mensaje enviado
        """
        # WhatsApp tiene límite de ~4096 caracteres
        if len(body) > 4000:
            body = body[:3997] + "..."

        message = self.client.messages.create(
            from_=self.from_number,
            to=to_number,
            body=body,
        )
        return message.sid
