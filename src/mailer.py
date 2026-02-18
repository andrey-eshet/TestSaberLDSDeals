from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path

from src.config import Settings


def send_email(
    settings: Settings,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[Path] | None = None,
    inline_images: list[tuple[str, Path]] | None = None,
) -> None:
    if not settings.smtp_ready():
        raise ValueError("SMTP configuration is incomplete")

    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = ", ".join(settings.mail_to)
    if settings.mail_cc:
        msg["Cc"] = ", ".join(settings.mail_cc)
    msg["Subject"] = subject
    msg.set_content(body_text)

    if body_html:
        msg.add_alternative(body_html, subtype="html")
        html_part = msg.get_payload()[-1]
        for cid, image_path in inline_images or []:
            if not image_path.exists() or not image_path.is_file():
                continue
            ctype, _ = mimetypes.guess_type(str(image_path))
            maintype = "image"
            subtype = "png"
            if ctype and "/" in ctype:
                guessed_main, guessed_sub = ctype.split("/", 1)
                maintype = guessed_main or "image"
                subtype = guessed_sub or "png"
            with image_path.open("rb") as f:
                html_part.add_related(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    cid=f"<{cid}>",
                    filename=image_path.name,
                    disposition="inline",
                )

    for attachment in attachments or []:
        if not attachment.exists() or not attachment.is_file():
            continue

        ctype, _ = mimetypes.guess_type(str(attachment))
        if ctype is None:
            maintype, subtype = "application", "octet-stream"
        else:
            maintype, subtype = ctype.split("/", 1)

        with attachment.open("rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment.name,
            )

    recipients = settings.mail_to + settings.mail_cc

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=60) as server:
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg, to_addrs=recipients)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=60) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(msg, to_addrs=recipients)
