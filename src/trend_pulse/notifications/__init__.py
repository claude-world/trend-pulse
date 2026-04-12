"""Notification system — multi-channel alerting for trend events."""

from .base import NotificationChannel, NotificationPayload
from .channels import DiscordWebhook, TelegramBot, GenericWebhook, LineNotify, EmailSMTP

__all__ = [
    "NotificationChannel",
    "NotificationPayload",
    "DiscordWebhook",
    "TelegramBot",
    "LineNotify",
    "EmailSMTP",
    "GenericWebhook",
]
