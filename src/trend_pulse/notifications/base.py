"""Notification base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationPayload:
    """Structured notification message."""
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    level: str = "info"   # info | warning | alert

    def to_text(self) -> str:
        lines = [f"[{self.level.upper()}] {self.title}", self.message]
        if self.data:
            for k, v in list(self.data.items())[:5]:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


class NotificationChannel(ABC):
    """Abstract notification backend."""

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Send a notification. Returns True on success."""

    async def send_text(self, title: str, message: str, **data) -> bool:
        """Convenience: send plain text notification."""
        return await self.send(NotificationPayload(title=title, message=message, data=data))
