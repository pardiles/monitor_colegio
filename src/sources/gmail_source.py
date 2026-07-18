"""
Fuente: Gmail API.
Lee correos de remitentes del colegio.
Incluye extracción de adjuntos PDF.
"""

import os
import base64
import re
from typing import List, Dict
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.utils.pdf_reader import read_pdf_from_bytes


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

SCHOOL_DOMAINS = [
    "colegiodelsagradocorazon.cl",
    "colegium.com",
]


class GmailClient:
    """Cliente para leer correos del colegio via Gmail API."""

    def __init__(self, credentials_file: str, token_file: str):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None

    def authenticate(self):
        """Autenticar con Gmail API (usa token guardado si existe)."""
        creds = None

        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(
                self.token_file, SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w") as f:
                f.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)

    def get_school_emails(self, days: int = 7, max_results: int = 20) -> List[Dict]:
        """
        Obtener correos del colegio de los últimos N días.
        
        Returns:
            Lista de dicts con: id, fecha, de, asunto, body_preview
        """
        if not self.service:
            raise RuntimeError("No autenticado. Llama authenticate() primero.")

        query_parts = [f"from:{domain}" for domain in SCHOOL_DOMAINS]
        query = f"({' OR '.join(query_parts)}) newer_than:{days}d"

        result = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = result.get("messages", [])
        emails = []

        for msg in messages:
            detail = self.service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()

            headers = {
                h["name"]: h["value"] for h in detail["payload"]["headers"]
            }

            # Parsear fecha
            fecha_str = headers.get("Date", "")
            try:
                fecha = parsedate_to_datetime(fecha_str)
                fecha_fmt = fecha.strftime("%Y-%m-%d %H:%M")
            except Exception:
                fecha_fmt = fecha_str[:20]

            emails.append({
                "id": msg["id"],
                "fecha": fecha_fmt,
                "de": headers.get("From", ""),
                "asunto": headers.get("Subject", ""),
                "snippet": detail.get("snippet", ""),
                "body": self._extract_body(detail["payload"]),
                "adjuntos_pdf": self._extract_pdf_attachments(
                    msg["id"], detail["payload"]
                ),
            })

        return emails

    def _extract_body(self, payload: Dict) -> str:
        """Extraer cuerpo del email como texto plano."""
        body = ""
        html_body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                mime = part.get("mimeType", "")
                if mime == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                elif mime == "text/html":
                    data = part["body"].get("data", "")
                    if data:
                        html_body = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                elif "parts" in part:
                    # Multipart nested (ej: multipart/alternative dentro de multipart/mixed)
                    for subpart in part["parts"]:
                        sub_mime = subpart.get("mimeType", "")
                        data = subpart.get("body", {}).get("data", "")
                        if sub_mime == "text/plain" and data:
                            body = base64.urlsafe_b64decode(data).decode(
                                "utf-8", errors="ignore"
                            )
                        elif sub_mime == "text/html" and data:
                            html_body = base64.urlsafe_b64decode(data).decode(
                                "utf-8", errors="ignore"
                            )
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="ignore"
                )

        # Si no hay texto plano, convertir HTML
        if not body and html_body:
            body = re.sub(r"<br\s*/?>", "\n", html_body)
            body = re.sub(r"<[^>]+>", " ", body)
            body = re.sub(r"\s+", " ", body).strip()

        return body[:2000]

    def _extract_pdf_attachments(self, msg_id: str, payload: Dict) -> List[Dict]:
        """
        Descarga y extrae texto de adjuntos PDF de un email.

        Returns:
            Lista de dicts con: filename, contenido (texto extraído)
        """
        pdfs = []
        parts = payload.get("parts", [])

        for part in parts:
            mime = part.get("mimeType", "")
            filename = part.get("filename", "")

            if mime == "application/pdf" and filename:
                attachment_id = part.get("body", {}).get("attachmentId")
                if not attachment_id:
                    continue

                try:
                    att = self.service.users().messages().attachments().get(
                        userId="me", messageId=msg_id, id=attachment_id
                    ).execute()

                    data = base64.urlsafe_b64decode(att["data"])
                    text = read_pdf_from_bytes(data, max_chars=3000)

                    if text:
                        pdfs.append({
                            "filename": filename,
                            "contenido": text,
                        })
                except Exception as e:
                    print(f"   ⚠️ Error descargando adjunto {filename}: {e}")

            # Buscar en partes anidadas (multipart/mixed)
            if "parts" in part:
                for subpart in part["parts"]:
                    sub_mime = subpart.get("mimeType", "")
                    sub_filename = subpart.get("filename", "")
                    if sub_mime == "application/pdf" and sub_filename:
                        sub_att_id = subpart.get("body", {}).get("attachmentId")
                        if not sub_att_id:
                            continue
                        try:
                            att = self.service.users().messages().attachments().get(
                                userId="me", messageId=msg_id, id=sub_att_id
                            ).execute()
                            data = base64.urlsafe_b64decode(att["data"])
                            text = read_pdf_from_bytes(data, max_chars=3000)
                            if text:
                                pdfs.append({
                                    "filename": sub_filename,
                                    "contenido": text,
                                })
                        except Exception:
                            pass

        return pdfs[:3]  # Máximo 3 PDFs por email
