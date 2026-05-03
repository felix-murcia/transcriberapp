"""
Email adapter for email services.
Implements EmailServicePort using SMTP or external email service.
"""

import os
import logging
from typing import Optional, Dict, Any

from domain.ports import EmailServicePort
from domain.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class SMTPEmailAdapter(EmailServicePort):
    """Adapter for SMTP email service."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@transcriber.app")

        # Import here to avoid hard dependency
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            self.smtplib = smtplib
            self.MIMEText = MIMEText
            self.MIMEMultipart = MIMEMultipart
        except ImportError:
            raise ImportError("Required email packages not installed")

    def send_transcription_result(
        self,
        email: str,
        job_id: str,
        filename: str,
        summary: str,
        transcription_url: Optional[str] = None
    ) -> bool:
        """Send transcription result via email."""
        logger.info(f"Sending transcription email to {email} for job {job_id}")

        try:
            # Create message
            msg = self.MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = f"Transcripción completada: {filename}"

            # Email body
            body = f"""
Hola,

Tu transcripción para el archivo "{filename}" ha sido completada.

Resumen:
{summary}

Job ID: {job_id}
"""

            if transcription_url:
                body += f"""
Enlace a la transcripción completa: {transcription_url}
"""

            body += "\n¡Gracias por usar TranscriberApp!"

            msg.attach(self.MIMEText(body, 'plain'))

            # Send email
            server = self.smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            text = msg.as_string()
            server.sendmail(self.from_email, email, text)
            server.quit()

            logger.info(f"Transcription email sent successfully to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send transcription email to {email}: {e}")
            raise ExternalServiceError("email", f"Failed to send email: {e}") from e


class MockEmailAdapter(EmailServicePort):
    """Mock adapter for testing - just logs emails instead of sending."""

    def send_transcription_result(
        self,
        email: str,
        job_id: str,
        filename: str,
        summary: str,
        transcription_url: Optional[str] = None
    ) -> bool:
        """Mock email sending - just log the email content."""
        logger.info(f"MOCK EMAIL to {email}:")
        logger.info(f"Subject: Transcripción completada: {filename}")
        logger.info(f"Job ID: {job_id}")
        logger.info(f"Summary: {summary[:100]}...")
        if transcription_url:
            logger.info(f"Transcription URL: {transcription_url}")

        return True