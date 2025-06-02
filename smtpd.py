#!/usr/bin/env python3

import asyncio
import json
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from email import message_from_string
from email.header import decode_header
from email.message import Message as EmailMessage
from logging import INFO, Formatter, Logger, StreamHandler, getLogger
from os import environ as env
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Envelope, Session

logger: Logger = getLogger("smtpd")
logger.setLevel(INFO)

handler: StreamHandler = StreamHandler()  # type: ignore
handler.setFormatter(Formatter("[%(name)s] %(message)s"))
logger.addHandler(handler)  # type: ignore


@dataclass
class DiscordToken:
    chid: str
    token: str


def tostr(s: bytes | str | Any) -> str:
    if isinstance(s, bytes):
        return s.decode()
    elif isinstance(s, str):
        return s
    else:
        raise TypeError(f"Expected bytes or str, got {type(s)}")


def parse_smtp_content(content: str) -> tuple[str, Optional[str]]:
    """Parse SMTP mail content and extract message.

    Args:
        content (str): Raw SMTP mail content string

    Returns:
        tuple[str, Optional[str]]: Tuple of message body and subject
    """
    email_message: EmailMessage = message_from_string(content)
    body: str = ""

    if email_message.is_multipart():
        parts: List[EmailMessage] = list(email_message.walk())
        body = "\n".join(
            tostr(part.get_payload(decode=True)) for part in parts if part.get_content_type() == "text/plain"
        )

    else:
        body = tostr(email_message.get_payload(decode=True))

    subject: Optional[str] = email_message.get("Subject")
    if subject and "=?utf-8?" in subject.lower():
        # Decode MIME encoded subject
        subject = tostr(decode_header(subject)[0][0])

    return body.strip(), subject


class CustomHandler:
    """see: https://aiosmtpd.aio-libs.org/en/latest/handlers.html#handler-hooks"""

    async def handle_AUTH(self, server: SMTP, session: Session, envelope: Envelope, auth_data: str) -> str:
        return "235 2.7.0 Authentication Succeeded"

    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope) -> str:
        """Handle DATA command

        see: https://aiosmtpd.aio-libs.org/en/latest/handlers.html#handle_DATA

        """
        _ = server
        _ = session

        if envelope.content is None:
            logger.warning("No content in message")
            return "250 Empty message accepted"

        content: str = tostr(envelope.content)
        body, subject = parse_smtp_content(content)

        logger.info(f"   FROM: {envelope.mail_from}")
        logger.info(f"     TO: {envelope.rcpt_tos}")
        logger.info(f"Subject: {subject}")
        logger.info(f" Length: {len(content)}")
        logger.info(" Content:")
        for line in body.splitlines():
            logger.info(f"> {line}")

        tokens: Dict[str, DiscordToken] = {
            k: DiscordToken(**v) for k, v in json.loads(Path("discord.json").read_text()).items()  # type: ignore
        }  # type: ignore

        name: str
        domain: str
        name, domain = envelope.rcpt_tos[0].split("@", 1)
        if domain == "discord.localdomain":
            t: DiscordToken = tokens[name]

            url: str = f"https://discord.com/api/channels/{t.chid}/messages"
            headers: Dict[str, str] = {
                "User-Agent": "Discord SMTP Bot",
                "Content-Type": "application/json",
                "Authorization": f"Bot {t.token}",
            }
            data = json.dumps({"content": f"**{subject}**\n```{body}```"}).encode("utf-8")

            req: Request = Request(url, data=data, headers=headers, method="POST")
            urlopen(req)

        return "250 Message accepted for delivery"


async def main() -> None:
    Controller(CustomHandler(), hostname="", port=int(env["SMTP_PORT"]), auth_require_tls=False).start()


if __name__ == "__main__":
    loop: AbstractEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        loop.close()
        logger.info("SMTP server stopped")
