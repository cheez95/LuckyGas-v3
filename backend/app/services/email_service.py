"""Email service for sending reports and notifications."""

import os
import smtplib
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import aiosmtplib

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        # In production, these would come from settings
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@luckygas.com.tw")
        self.from_name = os.getenv("FROM_NAME", "LuckyGas 系統")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[tuple[str, bytes]]] = None,
    ):
        """Send an email asynchronously."""
        try:
            # Create message
            message = EmailMessage()
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Set content
            if html_body:
                message.add_alternative(body, subtype="plain")
                message.add_alternative(html_body, subtype="html")
            else:
                message.set_content(body)

            # Add attachments if any
            if attachments:
                for filename, content in attachments:
                    message.add_attachment(
                        content,
                        maintype="application",
                        subtype="octet - stream",
                        filename=filename,
                    )

            # Send email
            if self.smtp_user and self.smtp_password:
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    start_tls=True,
                    username=self.smtp_user,
                    password=self.smtp_password,
                )
                logger.info(f"Email sent successfully to {to_email}")
            else:
                # In development, just log the email
                logger.info(f"Email (dev mode) to {to_email}: {subject}")
                logger.debug(f"Email body: {body}")

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise

    def send_email_sync(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[tuple[str, bytes]]] = None,
    ):
        """Send an email synchronously (for background tasks)."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # Add text and HTML parts
            part1 = MIMEText(body, "plain", "utf - 8")
            msg.attach(part1)

            if html_body:
                part2 = MIMEText(html_body, "html", "utf - 8")
                msg.attach(part2)

            # Add attachments if any
            if attachments:
                for filename, content in attachments:
                    part = MIMEApplication(content)
                    part.add_header(
                        "Content - Disposition", "attachment", filename=filename
                    )
                    msg.attach(part)

            # Send email
            if self.smtp_user and self.smtp_password:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                logger.info(f"Email sent successfully to {to_email}")
            else:
                # In development, just log the email
                logger.info(f"Email (dev mode) to {to_email}: {subject}")
                logger.debug(f"Email body: {body}")

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise
