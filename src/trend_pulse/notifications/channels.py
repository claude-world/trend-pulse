"""Notification channel implementations: Discord, Telegram, LINE Notify, Email SMTP, Generic webhook."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

from .base import NotificationChannel, NotificationPayload


class DiscordWebhook(NotificationChannel):
    """Send notifications to a Discord channel via webhook URL.

    Setup:
        channel = DiscordWebhook(webhook_url="https://discord.com/api/webhooks/...")
        # Or set DISCORD_WEBHOOK_URL environment variable.
    """

    def __init__(self, webhook_url: str = "") -> None:
        self._url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")

    async def send(self, payload: NotificationPayload) -> bool:
        if not self._url:
            return False
        color_map = {"info": 0x3498DB, "warning": 0xF1C40F, "alert": 0xE74C3C}
        body = {
            "embeds": [{
                "title": payload.title,
                "description": payload.message,
                "color": color_map.get(payload.level, 0x3498DB),
                "fields": [
                    {"name": str(k), "value": str(v), "inline": True}
                    for k, v in list(payload.data.items())[:5]
                ],
            }]
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=body)
                return resp.status_code in (200, 204)
        except Exception:
            return False


class TelegramBot(NotificationChannel):
    """Send notifications via Telegram Bot API.

    Setup:
        bot = TelegramBot(token="...", chat_id="...")
        # Or set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
    """

    def __init__(self, token: str = "", chat_id: str = "") -> None:
        self._token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    async def send(self, payload: NotificationPayload) -> bool:
        if not self._token or not self._chat_id:
            return False
        text = payload.to_text()
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json={
                    "chat_id": self._chat_id,
                    "text": text,
                    # No parse_mode: avoid Markdown parsing failures on trend keyword data
                })
                return resp.status_code == 200
        except Exception:
            return False


class GenericWebhook(NotificationChannel):
    """POST a JSON payload to any webhook URL.

    Useful for custom integrations (Slack incoming webhooks, n8n, Zapier, etc.)

    Setup:
        hook = GenericWebhook(url="https://hooks.slack.com/services/...")
        # Or set GENERIC_WEBHOOK_URL environment variable.
    """

    def __init__(self, url: str = "") -> None:
        self._url = url or os.environ.get("GENERIC_WEBHOOK_URL", "")

    async def send(self, payload: NotificationPayload) -> bool:
        if not self._url:
            return False
        body = {
            "title": payload.title,
            "message": payload.message,
            "level": payload.level,
            "data": payload.data,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=body)
                return resp.status_code < 400
        except Exception:
            return False


class LineNotify(NotificationChannel):
    """Send notifications via LINE Notify API.

    Setup:
        notifier = LineNotify(token="...")
        # Or set LINE_NOTIFY_TOKEN environment variable.
        # Get token from: https://notify-bot.line.me/
    """

    _API_URL = "https://notify-api.line.me/api/notify"

    def __init__(self, token: str = "") -> None:
        self._token = token or os.environ.get("LINE_NOTIFY_TOKEN", "")

    async def send(self, payload: NotificationPayload) -> bool:
        if not self._token:
            return False
        text = f"[{payload.level.upper()}] {payload.title}\n{payload.message}"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._API_URL,
                    headers=headers,
                    data={"message": text},
                )
                return resp.status_code == 200
        except Exception:
            return False


class EmailSMTP(NotificationChannel):
    """Send notifications via SMTP email.

    Setup (environment variables):
        SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_TO

    Or pass directly:
        EmailSMTP(host="smtp.gmail.com", port=587,
                  user="me@gmail.com", password="...",
                  from_addr="me@gmail.com", to_addr="you@example.com")
    """

    def __init__(
        self,
        host: str = "",
        port: int = 0,
        user: str = "",
        password: str = "",
        from_addr: str = "",
        to_addr: str = "",
    ) -> None:
        self._host = host or os.environ.get("SMTP_HOST", "")
        self._port = port or int(os.environ.get("SMTP_PORT", "587"))
        self._user = user or os.environ.get("SMTP_USER", "")
        self._password = password or os.environ.get("SMTP_PASS", "")
        self._from = from_addr or os.environ.get("SMTP_FROM", self._user)
        self._to = to_addr or os.environ.get("SMTP_TO", "")

    async def send(self, payload: NotificationPayload) -> bool:
        if not (self._host and self._user and self._to):
            return False
        import asyncio
        import smtplib
        from email.mime.text import MIMEText

        def _send_sync() -> bool:
            msg = MIMEText(payload.to_text(), _charset="utf-8")
            msg["Subject"] = f"[TrendPulse] {payload.title}"
            msg["From"] = self._from
            msg["To"] = self._to
            try:
                with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
                    smtp.starttls()
                    smtp.login(self._user, self._password)
                    smtp.sendmail(self._from, [self._to], msg.as_string())
                return True
            except Exception as exc:
                logger.warning("EmailSMTP send failed: %s", exc)
                return False

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _send_sync)
