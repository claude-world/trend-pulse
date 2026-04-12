"""Tests for the v2.0 plugin system and new plugin sources."""

from __future__ import annotations

import pytest

from trend_pulse.plugins.base import PluginSource
from trend_pulse.plugins.registry import PluginRegistry
from trend_pulse.sources.base import TrendItem, TrendSource


# ── Plugin Base Class ──────────────────────────────────────────────────────────

class ConcretePlugin(PluginSource):
    name = "test_plugin"
    description = "Test plugin for unit tests"
    requires_auth = False
    rate_limit = "unlimited"
    category = "global"
    frequency = "realtime"
    plugin_version = "1.0"

    async def fetch_trending(self, geo: str = "", count: int = 20) -> list[TrendItem]:
        return [TrendItem(keyword="test", score=50.0, source=self.name)]


def test_plugin_source_inherits_trend_source():
    assert issubclass(PluginSource, TrendSource)


def test_plugin_source_info_includes_base_keys():
    info = ConcretePlugin.info()
    # Must preserve original keys from TrendSource.info()
    assert "name" in info
    assert "description" in info
    assert "requires_auth" in info
    assert "rate_limit" in info


def test_plugin_source_info_includes_extended_keys():
    info = ConcretePlugin.info()
    assert info["category"] == "global"
    assert info["frequency"] == "realtime"
    assert info["plugin_version"] == "1.0"


def test_plugin_source_name():
    assert ConcretePlugin.name == "test_plugin"


# ── Plugin Registry ────────────────────────────────────────────────────────────

def test_registry_load_all_returns_dict():
    instances = PluginRegistry.load_all(skip_errors=True)
    assert isinstance(instances, dict)


def test_registry_all_instances_are_plugin_sources():
    instances = PluginRegistry.load_all(skip_errors=True)
    for name, inst in instances.items():
        assert isinstance(inst, PluginSource), f"{name} is not a PluginSource"


def test_registry_instance_names_match_class_names():
    instances = PluginRegistry.load_all(skip_errors=True)
    for name, inst in instances.items():
        assert name == inst.name, f"Key {name!r} != inst.name {inst.name!r}"


def test_registry_load_one_known():
    inst = PluginRegistry.load_one("weibo")
    if inst is None:
        pytest.skip("weibo plugin not available")
    assert isinstance(inst, PluginSource)
    assert inst.name == "weibo"


def test_registry_load_one_unknown():
    inst = PluginRegistry.load_one("nonexistent_plugin_xyz")
    assert inst is None


# ── Aggregator Integration ─────────────────────────────────────────────────────

def test_aggregator_loads_plugins():
    from trend_pulse.aggregator import TrendAggregator
    agg = TrendAggregator(include_plugins=True)
    # Should have at least the 20 built-in sources
    assert len(agg.available_sources) >= 20


def test_aggregator_no_plugins():
    from trend_pulse.aggregator import TrendAggregator
    agg = TrendAggregator(include_plugins=False)
    assert len(agg.available_sources) == 20  # Exactly the 20 built-ins


def test_aggregator_list_sources_includes_plugins():
    from trend_pulse.aggregator import TrendAggregator
    agg = TrendAggregator(include_plugins=True)
    source_list = agg.list_sources()
    assert isinstance(source_list, list)
    # All entries must have required keys
    for entry in source_list:
        assert "name" in entry
        assert "description" in entry
        assert "requires_auth" in entry
        assert "rate_limit" in entry


def test_aggregator_plugin_sources_have_category():
    from trend_pulse.aggregator import TrendAggregator
    agg = TrendAggregator(include_plugins=True)
    source_list = agg.list_sources()
    plugin_sources = [s for s in source_list if "category" in s]
    # At least some plugin sources should have category
    # (built-ins don't have it unless they extend PluginSource)
    assert len(plugin_sources) >= 1  # At least one plugin source should carry category metadata


# ── Individual Plugin Sources (smoke tests) ────────────────────────────────────

def test_weibo_plugin_structure():
    inst = PluginRegistry.load_one("weibo")
    if inst is None:
        pytest.skip("weibo plugin not available")
    assert inst.name == "weibo"
    assert inst.category == "tw"
    assert not inst.requires_auth


def test_coinmarketcap_plugin_structure():
    inst = PluginRegistry.load_one("coinmarketcap")
    if inst is None:
        pytest.skip("coinmarketcap plugin not available")
    assert inst.name == "coinmarketcap"
    assert inst.category == "crypto"
    assert not inst.requires_auth


def test_dexscreener_plugin_structure():
    inst = PluginRegistry.load_one("dexscreener")
    if inst is None:
        pytest.skip("dexscreener plugin not available")
    assert inst.name == "dexscreener"
    assert inst.category == "crypto"
    assert not inst.requires_auth


def test_youtube_trending_plugin_structure():
    inst = PluginRegistry.load_one("youtube_trending")
    if inst is None:
        pytest.skip("youtube_trending plugin not available")
    assert inst.name == "youtube_trending"
    assert inst.category == "global"


def test_indie_hackers_plugin_structure():
    inst = PluginRegistry.load_one("indie_hackers")
    if inst is None:
        pytest.skip("indie_hackers plugin not available")
    assert inst.name == "indie_hackers"
    assert inst.category == "dev"


def test_all_plugins_have_register_function():
    """Verify every plugin module has a register() function."""
    import importlib
    import pkgutil
    from pathlib import Path

    sources_path = Path(__file__).parent.parent / "src" / "trend_pulse" / "plugins" / "sources"
    for module_info in pkgutil.iter_modules([str(sources_path)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"trend_pulse.plugins.sources.{module_info.name}")
        assert hasattr(module, "register"), (
            f"Plugin module {module_info.name} is missing register() function"
        )


def test_all_plugin_trend_items_have_required_fields():
    """register() should return instances with required class vars set."""
    instances = PluginRegistry.load_all(skip_errors=True)
    for name, inst in instances.items():
        assert inst.name, f"Plugin {name} has empty name"
        assert inst.description, f"Plugin {name} has empty description"
