"""
Email channel adapter.

Modes (EMAIL_PROVIDER env var):
  mock  — prints to stdout, no network (default)
  smtp  — sends via SMTP using SMTP_HOST/PORT/USERNAME/PASSWORD/FROM
  webhook — accepts parsed payloads from an inbound email webhook

Signature verification uses EMAIL_WEBHOOK_SECRET (HMAC-SHA256).
Never hard-code credentials — use env vars only.
"""

import hashlib
import hmac
import json
import os

from src.channels.base import (
    BaseChannelAdapter,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
    NormalizedChannelMessage,
)


class EmailAdapter(BaseChannelAdapter):
    channel_name = "email"

    def __init__(self) -> None:
        self.provider = os.getenv("EMAIL_PROVIDER", "mock")
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "")
        self._webhook_secret = os.getenv("EMAIL_WEBHOOK_SECRET", "")

    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        sender = payload.get("from") or payload.get("sender", "unknown@example.com")
        subject = payload.get("subject", "")
        text = payload.get("text") or payload.get("body", "")
        html = payload.get("html", "")
        thread_id = payload.get("message_id") or payload.get("thread_id")

        raw_key = f"email:{sender}:{subject}:{text[:64]}"
        idempotency_key = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        return NormalizedChannelMessage(
            channel="email",
            external_user_id=sender,
            external_thread_id=thread_id,
            text=text or subject or None,
            intent=self._detect_email_intent(subject, text),
            attachments=payload.get("attachments", []),
            raw=payload,
            idempotency_key=idempotency_key,
        )

    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        if self.provider == "mock":
            subj = message.subject or "(no subject)"
            print(f"[Email MOCK → {message.to_external_user_id}] {subj}\n{message.text}")
            return ChannelDeliveryReceipt(
                channel="email",
                external_user_id=message.to_external_user_id,
                message_id=f"email_mock_{abs(hash(message.text)):x}",
                status="mocked",
                provider_response={"mock": True},
            )
        if self.provider == "smtp":
            return self._send_smtp(message)
        raise ValueError(f"Unsupported EMAIL_PROVIDER: {self.provider!r}")

    def verify_signature(self, headers: dict, payload: bytes | dict) -> bool:
        if not self._webhook_secret:
            return True
        sig = (
            headers.get("X-Email-Signature")
            or headers.get("x-email-signature")
            or ""
        )
        if not sig:
            return False
        if isinstance(payload, dict):
            payload = json.dumps(payload, separators=(",", ":")).encode()
        expected = hmac.new(
            self._webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, sig)

    def _send_smtp(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        if not self.smtp_host or not self.smtp_username or not self.smtp_password:
            raise RuntimeError(
                "SMTP not configured — set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD"
            )
        msg = MIMEMultipart("alternative")
        msg["From"] = self.smtp_from or self.smtp_username
        msg["To"] = message.to_external_user_id
        msg["Subject"] = message.subject or "(no subject)"
        msg.attach(MIMEText(message.text, "plain"))
        if message.html:
            msg.attach(MIMEText(message.html, "html"))
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
            s.starttls()
            s.login(self.smtp_username, self.smtp_password)
            s.sendmail(msg["From"], msg["To"], msg.as_string())
        return ChannelDeliveryReceipt(
            channel="email",
            external_user_id=message.to_external_user_id,
            status="sent",
            provider_response={"smtp": "ok"},
        )

    def _detect_email_intent(self, subject: str, text: str) -> str | None:
        combined = (subject + " " + text).lower()
        if any(w in combined for w in ["inquiry", "purchase", "buy", "need", "sourcing", "rfq"]):
            return "buy"
        if any(w in combined for w in ["quote", "capacity", "supply", "can make", "lead time", "moq"]):
            return "supply"
        if any(w in combined for w in ["shipment", "logistics", "tracking", "carrier", "shipping"]):
            return "logistics"
        return None
