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


def _mock_http(responses):
    """Mock httpx.AsyncClient whose get() returns the given responses in order."""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.get = AsyncMock(side_effect=responses)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _http_resp(text="", status=200, data=None, url="https://example.com/"):
    import json as _json
    from unittest.mock import MagicMock

    import httpx

    resp = MagicMock()
    resp.status_code = status
    resp.text = _json.dumps(data) if data is not None else text
    resp.content = resp.text.encode()
    resp.json.return_value = data
    resp.url = httpx.URL(url)
    resp.raise_for_status = MagicMock()
    return resp


def _fetch(source_name, responses, count=20):
    import asyncio
    from unittest.mock import patch

    client = _mock_http(responses)
    with patch("httpx.AsyncClient", return_value=client):
        items = asyncio.run(PluginRegistry.load_one(source_name).fetch_trending(count=count))
    return items, client


def test_weibo_visitor_gate_returns_empty():
    gate = _http_resp(
        "<html><title>Sina Visitor System</title></html>",
        url="https://passport.weibo.com/visitor/visitor?entry=miniblog&a=enter",
    )
    items, _ = _fetch("weibo", [gate])
    assert items == []


def test_weibo_parses_hot_search_table():
    page = (
        '<table><tr class="thead"><th>rank</th></tr>'
        '<tr><td class="td-01">1</td><td class="td-02">'
        '<a href="/weibo?q=%23topic%23" target="_blank">熱門話題 &amp; 測試</a>'
        '<span>1234567</span></td><td class="td-03"><i class="icon-txt">熱</i></td></tr>'
        "</table>"
    )
    items, _ = _fetch("weibo", [_http_resp(page, url="https://s.weibo.com/top/summary?cate=realtimehot")])
    assert len(items) == 1
    assert items[0].keyword == "熱門話題 & 測試"
    assert items[0].url == "https://s.weibo.com/weibo?q=%23topic%23"


def test_xiaohongshu_block_page_yields_no_items():
    inst = PluginRegistry.load_one("xiaohongshu")
    page = "<html><head><title>小红书 - 你的生活指南</title></head><body>登录</body></html>"
    assert inst._parse_html(page, 10) == []


_BAHAMUT_FORUM_HTML = """
<div><a href="https://forum.gamer.com.tw/B.php?bsn=7650" tabindex="0"><h3 class="x">新楓之谷 </h3></a></div>
<span><svg></svg><data value="200000">20萬</data><data value="200000">200,000</data></span>
<span><svg></svg><data value="103">103</data></span><span>板主：someone</span>
<a href="https://forum.gamer.com.tw/C.php?bsn=7650&amp;snA=1038568" tabindex="0"><h5 class="y">【情報】改版 &amp; 活動</h5></a>
<div><a href="https://forum.gamer.com.tw/B.php?bsn=36730" tabindex="0"><h3 class="x">原神</h3></a></div>
<span><svg></svg><data value="50000">5萬</data></span>
<a href="https://forum.gamer.com.tw/C.php?bsn=36730&amp;snA=46853" tabindex="0"><h5 class="y">【心得】新角色</h5></a>
"""

_BAHAMUT_GNN_RSS = """<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0"><channel><title>巴哈姆特 GNN 新聞網</title>
<item><title><![CDATA[《新作》公布上市日期]]></title>
<link><![CDATA[https://gnn.gamer.com.tw/detail.php?sn=1]]></link>
<pubDate>Tue, 20 Oct 2026 23:33:57 +0800</pubDate></item>
</channel></rss>"""


def test_bahamut_parses_hot_boards():
    items, _ = _fetch("bahamut", [_http_resp(_BAHAMUT_FORUM_HTML)])
    assert [it.keyword for it in items] == ["新楓之谷", "原神"]
    assert items[0].score == 100.0
    assert items[1].score == 25.0
    assert items[0].url == "https://forum.gamer.com.tw/B.php?bsn=7650"
    assert items[0].metadata["popularity"] == 200000
    assert items[0].metadata["hot_thread"] == "【情報】改版 & 活動"
    assert items[0].metadata["hot_thread_url"] == "https://forum.gamer.com.tw/C.php?bsn=7650&snA=1038568"


def test_bahamut_falls_back_to_gnn_rss():
    items, client = _fetch("bahamut", [_http_resp("<html>layout changed</html>"), _http_resp(_BAHAMUT_GNN_RSS)])
    assert client.get.call_count == 2
    assert len(items) == 1
    assert items[0].keyword == "《新作》公布上市日期"
    assert items[0].url == "https://gnn.gamer.com.tw/detail.php?sn=1"
    assert items[0].metadata["feed"] == "gnn"


def test_line_today_parses_most_viewed():
    data = {"id": "module:x", "items": [
        {"title": "颱風最新路徑", "publisher": "三立新聞網", "viewCount": 150000,
         "categoryName": "生活", "publishTimeUnix": 1792536300000,
         "url": {"hash": "j7pJrEx", "url": "https://today.line.me/tw/v3/article/j7pJrEx"}},
        {"title": "股市收盤", "publisher": "自由電子報", "viewCount": 75000,
         "categoryName": "理財", "url": {"hash": "nXpmm7g"}},
        {"title": "", "viewCount": 999999},
    ]}
    items, client = _fetch("line_today", [_http_resp(data=data)], count=10)
    assert [it.keyword for it in items] == ["颱風最新路徑", "股市收盤"]
    assert items[0].score == 100.0
    assert items[1].score == 50.0
    assert items[1].url == "https://today.line.me/tw/v3/article/nXpmm7g"
    assert items[0].metadata["publisher"] == "三立新聞網"
    assert items[0].published.startswith("2026-10-")
    assert client.get.call_args.kwargs["params"]["categories"] == "100259:10"


def test_line_today_falls_back_to_page_listing():
    import json as _json

    next_data = {"props": {"pageProps": {"fallback": {
        "getTabsData": {"modules": []},
        '5e4b9e403429e7a65895ac63_{"offset":0,"length":10}': [
            {"title": "頭條新聞", "publisher": "華視新聞", "url": {"hash": "Nv5oP08"}},
        ],
    }}}}
    page = f'<script id="__NEXT_DATA__" type="application/json">{_json.dumps(next_data)}</script>'
    items, _ = _fetch("line_today", [_http_resp(status=404, data={"status": 404}), _http_resp(page)])
    assert len(items) == 1
    assert items[0].keyword == "頭條新聞"
    assert items[0].url == "https://today.line.me/tw/v3/article/Nv5oP08"
    assert items[0].score == 99


def test_coinmarketcap_plugin_structure():
    inst = PluginRegistry.load_one("coinmarketcap")
    if inst is None:
        pytest.skip("coinmarketcap plugin not available")
    assert inst.name == "coinmarketcap"
    assert inst.category == "crypto"
    assert not inst.requires_auth


_DEX_BOOSTS = [
    {"url": "https://dexscreener.com/solana/aaa", "chainId": "solana",
     "tokenAddress": "AAAtoken111", "totalAmount": 700},
    {"url": "https://dexscreener.com/ethereum/0xbbb", "chainId": "ethereum",
     "tokenAddress": "0xBBBtoken222", "totalAmount": 350},
]


def test_dexscreener_resolves_token_names():
    solana_pairs = [{"baseToken": {"address": "AAAtoken111", "name": "Kimchi Coin", "symbol": "KIMCHI"},
                     "quoteToken": {"address": "So111", "name": "Wrapped SOL", "symbol": "SOL"}}]
    eth_pairs = [{"baseToken": {"address": "0xbbbtoken222", "name": "Money Business", "symbol": "MONEYBIZ"},
                  "quoteToken": {"address": "0xweth", "name": "Wrapped Ether", "symbol": "WETH"}}]
    items, client = _fetch("dexscreener", [
        _http_resp(data=_DEX_BOOSTS), _http_resp(data=solana_pairs), _http_resp(data=eth_pairs),
    ])
    assert [it.keyword for it in items] == ["Kimchi Coin (KIMCHI)", "Money Business (MONEYBIZ)"]
    assert [it.score for it in items] == [100.0, 50.0]
    assert items[0].traffic == "boost: 700"
    lookups = [call.args[0] for call in client.get.call_args_list[1:]]
    assert "https://api.dexscreener.com/tokens/v1/solana/AAAtoken111" in lookups
    assert "https://api.dexscreener.com/tokens/v1/ethereum/0xBBBtoken222" in lookups


def test_dexscreener_keeps_address_when_names_unavailable():
    items, _ = _fetch("dexscreener", [
        _http_resp(data=_DEX_BOOSTS), _http_resp(status=429, data={}), _http_resp(status=429, data={}),
    ])
    assert [it.keyword for it in items] == ["AAAtoken", "0xBBBtok"]


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


def _fake_async_client(*responses):
    """Stand-in for httpx.AsyncClient whose get() returns the given responses in order."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.get = AsyncMock(side_effect=list(responses))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _http_response(status: int, url: str, **kwargs):
    """Real httpx.Response bound to `url` (resp.url is the final, post-redirect URL)."""
    import httpx

    return httpx.Response(status, request=httpx.Request("GET", url), **kwargs)


def test_youtube_trending_without_api_key_makes_no_request(monkeypatch):
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.youtube_trending import YouTubeTrendingSource

    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with patch("trend_pulse.plugins.sources.youtube_trending.httpx.AsyncClient") as client_cls:
        items = asyncio.run(YouTubeTrendingSource().fetch_trending(count=5))
    assert items == []
    client_cls.assert_not_called()


def test_youtube_trending_parses_data_api_most_popular(monkeypatch):
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.youtube_trending import YouTubeTrendingSource

    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    payload = {"items": [
        {
            "id": "abc123",
            "snippet": {"title": "Big Video", "channelTitle": "Chan",
                        "publishedAt": "2026-10-20T10:00:00Z", "categoryId": "10"},
            "statistics": {"viewCount": "25000000", "likeCount": "1000", "commentCount": "50"},
        },
        {"id": "", "snippet": {"title": "No id"}, "statistics": {}},
    ]}
    client = _fake_async_client(_http_response(200, YouTubeTrendingSource.API_URL, json=payload))
    with patch("trend_pulse.plugins.sources.youtube_trending.httpx.AsyncClient", return_value=client):
        items = asyncio.run(YouTubeTrendingSource().fetch_trending(geo="tw", count=5))

    assert len(items) == 1
    assert items[0].keyword == "Big Video"
    assert items[0].url == "https://www.youtube.com/watch?v=abc123"
    assert items[0].score == 25.0
    assert items[0].metadata["views"] == 25_000_000
    assert items[0].metadata["region"] == "TW"
    kwargs = client.get.call_args.kwargs
    assert kwargs["params"]["chart"] == "mostPopular"
    assert kwargs["params"]["regionCode"] == "TW"
    assert "key" not in kwargs["params"]  # key travels in a header, never in the logged URL
    assert kwargs["headers"]["X-Goog-Api-Key"] == "test-key"


def test_indie_hackers_plugin_structure():
    inst = PluginRegistry.load_one("indie_hackers")
    if inst is None:
        pytest.skip("indie_hackers plugin not available")
    assert inst.name == "indie_hackers"
    assert inst.category == "dev"


_IH_HOME = """
<div class="organic" style="grid-area: organic;">
<div class="story homepage-post normal story--no-image">
<a class="story__text-link story__link-element" href="/post/first-post-abc">
<h3 class="story__title">Don&#x27;t build &amp; pray</h3>
</a>
<div class="story__counts"><a class="story__count story__count--likes" href="/sign-up"><svg></svg><span class="story__count-number">40</span><span class="story__count-text">upvotes</span></a><a class="story__count story__count--comments" href="/post/first-post-abc"><svg></svg><span class="story__count-number">1,204</span><span class="story__count-text">comments</span></a></div>
</div><div class="story homepage-post normal">
<a class="story__text-link story__link-element" href="/post/second-post-def">
<h3 class="story__title">Second post</h3>
</a>
</div>
</div>
<div class="featured" style="grid-area: featured;">
<div class="story homepage-post featured">
<a class="story__text-link story__link-element" href="/post/featured-ghi">
<h3 class="story__title">Featured subscriber story</h3>
</a>
</div>
</div>
"""


def test_indie_hackers_parses_homepage_feed():
    from trend_pulse.plugins.sources.indie_hackers import IndieHackersSource

    items = IndieHackersSource()._parse_home(_IH_HOME, 20)
    assert [it.keyword for it in items] == ["Don't build & pray", "Second post"]  # featured skipped
    assert items[0].url == "https://www.indiehackers.com/post/first-post-abc"
    assert items[0].metadata["votes"] == 40
    assert items[0].metadata["comments"] == 1204
    assert items[0].score == 20.0
    assert items[1].score == 0.0


def test_indie_hackers_without_feed_returns_empty():
    from trend_pulse.plugins.sources.indie_hackers import IndieHackersSource

    assert IndieHackersSource()._parse_home("<html><body>maintenance</body></html>", 20) == []


def test_pinterest_parses_trends_and_falls_back_to_us():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.pinterest import PinterestSource

    url = PinterestSource.TRENDS_URL
    payload = {"values": [
        {"term": "second term", "reverseRank": 19, "searchCount": 17,
         "mom_change": {"value": 0.9}, "wow_change": {"value": -0.2}},
        {"term": "top term", "reverseRank": 20, "searchCount": 38, "mom_change": {"value": 100.01}},
        {"term": "", "reverseRank": 18},
    ]}
    client = _fake_async_client(_http_response(400, url, json={}), _http_response(200, url, json=payload))
    with patch("trend_pulse.plugins.sources.pinterest.httpx.AsyncClient", return_value=client):
        items = asyncio.run(PinterestSource().fetch_trending(geo="TW", count=5))

    assert [it.keyword for it in items] == ["top term", "second term"]
    assert items[0].traffic == "10,000%+ MoM"
    assert items[1].traffic == "+90% MoM"
    assert items[0].score > items[1].score
    assert items[0].metadata["country"] == "US"
    assert [c.kwargs["params"]["country"] for c in client.get.call_args_list] == ["TW", "US"]


def test_pinterest_http_error_returns_empty():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.pinterest import PinterestSource

    client = _fake_async_client(_http_response(503, PinterestSource.TRENDS_URL, text="down"))
    with patch("trend_pulse.plugins.sources.pinterest.httpx.AsyncClient", return_value=client):
        assert asyncio.run(PinterestSource().fetch_trending(count=5)) == []


def test_threads_login_wall_returns_empty_not_entities():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.threads import ThreadsSource

    login_page = '<html><body style="color:#fff">Log in &#x2022; Threads &#x767b;</body></html>'
    client = _fake_async_client(_http_response(
        200, "https://www.threads.com/login/?next=https%3A%2F%2Fwww.threads.com%2Fexplore%2F", text=login_page,
    ))
    with patch("trend_pulse.plugins.sources.threads.httpx.AsyncClient", return_value=client):
        assert asyncio.run(ThreadsSource().fetch_trending(count=5)) == []


def test_linkedin_trending_marketing_redirect_returns_empty():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.linkedin_trending import LinkedInTrendingSource

    marketing = "<h2>Top products for hiring</h2><h3>Why post a job on LinkedIn?</h3>"
    client = _fake_async_client(_http_response(
        200, "https://business.linkedin.com/talent-solutions/cx/20/12/jobs-single-cta", text=marketing,
    ))
    with patch("trend_pulse.plugins.sources.linkedin_trending.httpx.AsyncClient", return_value=client):
        assert asyncio.run(LinkedInTrendingSource().fetch_trending(count=5)) == []


def test_linkedin_trending_parses_public_news_page():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.linkedin_trending import LinkedInTrendingSource

    page = "<h2>Chipmakers ramp up hiring</h2><h3>Remote work rules tighten</h3>"
    client = _fake_async_client(_http_response(200, LinkedInTrendingSource.NEWS_URL, text=page))
    with patch("trend_pulse.plugins.sources.linkedin_trending.httpx.AsyncClient", return_value=client):
        items = asyncio.run(LinkedInTrendingSource().fetch_trending(count=5))
    assert [it.keyword for it in items] == ["Chipmakers ramp up hiring", "Remote work rules tighten"]


def test_tiktok_api_permission_error_returns_empty():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.tiktok_trending import TikTokTrendingSource

    client = _fake_async_client(
        _http_response(200, TikTokTrendingSource.API_URL, json={"code": 40101, "msg": "no permission"}),
        _http_response(200, TikTokTrendingSource.CC_URL, text="<html><div id='root'></div></html>"),
    )
    with patch("trend_pulse.plugins.sources.tiktok_trending.httpx.AsyncClient", return_value=client):
        items = asyncio.run(TikTokTrendingSource().fetch_trending(count=5))
    assert items == []
    assert client.get.await_count == 2  # API refusal falls through to the static page


def test_tiktok_parses_api_hashtags():
    import asyncio
    from unittest.mock import patch

    from trend_pulse.plugins.sources.tiktok_trending import TikTokTrendingSource

    payload = {"code": 0, "data": {"list": [{"hashtag_name": "fyp", "video_views": 50_000_000, "post_num": 900}]}}
    client = _fake_async_client(_http_response(200, TikTokTrendingSource.API_URL, json=payload))
    with patch("trend_pulse.plugins.sources.tiktok_trending.httpx.AsyncClient", return_value=client):
        items = asyncio.run(TikTokTrendingSource().fetch_trending(count=5))
    assert [it.keyword for it in items] == ["#fyp"]
    assert items[0].score == 5.0


def test_x_trending_awaits_twikit_get_trends():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    import trend_pulse.plugins.sources.x_trending as xt

    twikit_client = MagicMock()
    twikit_client.get_trends = AsyncMock(return_value=[SimpleNamespace(name="#AI", tweets_count="12.3K posts")])
    with patch.object(xt, "_TWIKIT_AVAILABLE", True), \
            patch.object(xt, "TwikitClient", return_value=twikit_client, create=True):
        items = asyncio.run(xt.XTrendingSource().fetch_trending(count=5))

    twikit_client.get_trends.assert_awaited_once_with("trending", count=5, retry=False)
    assert [it.keyword for it in items] == ["#AI"]
    assert items[0].traffic == "12.3K posts"
    assert "%23AI" in items[0].url


def test_x_trending_twikit_failure_without_token_returns_empty():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    import trend_pulse.plugins.sources.x_trending as xt

    twikit_client = MagicMock()
    twikit_client.get_trends = AsyncMock(side_effect=Exception("Couldn't get KEY_BYTE indices"))
    with patch.object(xt, "_TWIKIT_AVAILABLE", True), \
            patch.object(xt, "TwikitClient", return_value=twikit_client, create=True), \
            patch.object(xt.XTrendingSource, "_BEARER", ""):
        assert asyncio.run(xt.XTrendingSource().fetch_trending(count=5)) == []


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
