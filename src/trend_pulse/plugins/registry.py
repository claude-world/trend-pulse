"""PluginRegistry — auto-discovers and loads plugin sources from plugins/sources/.

Usage:
    from trend_pulse.plugins.registry import PluginRegistry

    instances = PluginRegistry.load_all()  # {name: PluginSource instance}
    agg._instances.update(instances)       # merge into aggregator
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from .base import PluginSource

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Auto-discovers plugin source modules and returns instantiated sources.

    Each module in plugins/sources/ that defines a ``register()`` factory
    function is loaded. Modules that raise ImportError (e.g. optional dep
    not installed) are silently skipped with a debug-level log.
    """

    _sources_path = Path(__file__).parent / "sources"

    @classmethod
    def load_all(cls, skip_errors: bool = True) -> dict[str, PluginSource]:
        """Scan plugins/sources/ and return {name: instance} for all plugins.

        Args:
            skip_errors: If True (default), ImportError and other load failures
                         are logged at DEBUG level and skipped. If False, re-raises.
        """
        instances: dict[str, PluginSource] = {}
        pkg_prefix = "trend_pulse.plugins.sources."

        for module_info in pkgutil.iter_modules([str(cls._sources_path)]):
            if module_info.name.startswith("_"):
                continue

            module_name = pkg_prefix + module_info.name
            try:
                module = importlib.import_module(module_name)
            except ImportError as exc:
                if skip_errors:
                    logger.debug("Skipping plugin %s (missing dep): %s", module_info.name, exc)
                    continue
                raise
            except Exception as exc:
                if skip_errors:
                    logger.debug("Skipping plugin %s (load error): %s", module_info.name, exc)
                    continue
                raise

            if not hasattr(module, "register"):
                logger.debug("Plugin %s has no register() factory, skipping", module_info.name)
                continue

            try:
                plugin = module.register()
                if not isinstance(plugin, PluginSource):
                    logger.debug("Plugin %s register() did not return PluginSource, skipping", module_info.name)
                    continue
                instances[plugin.name] = plugin
                logger.debug("Loaded plugin: %s (%s)", plugin.name, type(plugin).__name__)
            except Exception as exc:
                if skip_errors:
                    logger.debug("Plugin %s register() failed: %s", module_info.name, exc)
                    continue
                raise

        return instances

    @classmethod
    def load_one(cls, name: str) -> PluginSource | None:
        """Load a single plugin by module name (not source name).

        Args:
            name: Module filename stem, e.g. "weibo" for weibo.py.

        Returns:
            Instantiated PluginSource, or None if not found / load failed.
        """
        module_name = f"trend_pulse.plugins.sources.{name}"
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "register"):
                return module.register()
        except Exception as exc:
            logger.debug("Failed to load plugin %s: %s", name, exc)
        return None
