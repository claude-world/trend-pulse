"""trend-pulse plugin system — extensible source architecture."""

from .base import PluginSource
from .registry import PluginRegistry

__all__ = ["PluginSource", "PluginRegistry"]
