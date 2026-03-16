"""Unit tests for all 20 trend sources using mocked HTTP responses."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from trend_pulse.sources.base import TrendItem, TrendSource


# ── Helper ──


def _run(coro):
    return asyncio.run(coro)


def _mock_client(responses: list[MagicMock]) -> MagicMock:
    """Create a mock httpx.AsyncClient that returns responses in order."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=responses)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    # Also allow setting cookies
    client.cookies = MagicMock()
    return client


def _json_resp(data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.text = json.dumps(data)
    return resp


def _text_resp(text, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


# ═══════════════════════════════════════════════════════
# 1. Google Trends
# ═══════════════════════════════════════════════════════


class TestGoogleTrendsSource:
    def test_parse_traffic_k(self):
        from trend_pulse.sources.google_trends import GoogleTrendsSource
        assert GoogleTrendsSource._parse_traffic("200K+") == 40.0

    def test_parse_traffic_m(self):
        from trend_pulse.sources.google_trends import GoogleTrendsSource
        assert GoogleTrendsSource._parse_traffic("2M+") == 100.0

    def test_parse_traffic_numeric(self):
        from trend_pulse.sources.google_trends import GoogleTrendsSource
        assert GoogleTrendsSource._parse_traffic("500") == 10.0

    def test_parse_traffic_empty(self):
        from trend_pulse.sources.google_trends import GoogleTrendsSource
        assert GoogleTrendsSource._parse_traffic("") == 0

    def test_fetch_trending(self):
        from trend_pulse.sources.google_trends import GoogleTrendsSource
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss xmlns:ht="https://trends.google.com/trending/trendsapi/ht">
          <channel>
            <item>
              <title>AI Tools</title>
              <ht:approx_traffic>100K+</ht:approx_traffic>
              <pubDate>Mon, 10 Mar 2026</pubDate>
              <ht:news_item>
                <ht:news_item_title>Breaking AI News</ht:news_item_title>
                <ht:news_item_url>https://example.com/ai</ht:news_item_url>
                <ht:news_item_source>Example</ht:news_item_source>
              </ht:news_item>
            </item>
          </channel>
        </rss>"""
        resp = _text_resp(xml)
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            src = GoogleTrendsSource()
            items = _run(src.fetch_trending(geo="US", count=5))
        assert len(items) == 1
        assert items[0].keyword == "AI Tools"
        assert items[0].source == "google_trends"
        assert items[0].metadata["news"][0]["title"] == "Breaking AI News"

    def test_info(self):
        from trend_pulse.sources.google_trends import GoogleTrendsSource
        info = GoogleTrendsSource.info()
        assert info["name"] == "google_trends"
        assert info["requires_auth"] is False


# ═══════════════════════════════════════════════════════
# 2. Hacker News
# ═══════════════════════════════════════════════════════


class TestHackerNewsSource:
    def test_fetch_trending(self):
        from trend_pulse.sources.hackernews import HackerNewsSource
        resp_ids = _json_resp([1001, 1002])
        resp_s1 = _json_resp({"type": "story", "title": "Story 1", "score": 250, "by": "user1", "descendants": 50, "url": "https://a.com"})
        resp_s2 = _json_resp({"type": "story", "title": "Story 2", "score": 100, "by": "user2", "descendants": 10})
        client = _mock_client([resp_ids, resp_s1, resp_s2])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(HackerNewsSource().fetch_trending(count=5))
        assert len(items) == 2
        assert items[0].keyword == "Story 1"
        assert items[0].score == 50.0  # 250/5
        assert items[0].metadata["comments"] == 50

    def test_search(self):
        from trend_pulse.sources.hackernews import HackerNewsSource
        resp = _json_resp({"hits": [
            {"title": "AI Result", "points": 100, "url": "https://x.com", "objectID": "1", "author": "a", "num_comments": 5, "created_at": "2026-03-10"},
        ]})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(HackerNewsSource().search("AI"))
        assert len(items) == 1
        assert items[0].keyword == "AI Result"


# ═══════════════════════════════════════════════════════
# 3. Mastodon
# ═══════════════════════════════════════════════════════


class TestMastodonSource:
    def test_fetch_trending(self):
        from trend_pulse.sources.mastodon import MastodonSource
        tags_resp = _json_resp([
            {"name": "python", "history": [{"uses": "50", "accounts": "20"}]},
        ])
        links_resp = _json_resp([
            {"title": "Cool Article", "url": "https://a.com", "history": [{"uses": "30"}], "provider_name": "Blog", "description": "desc"},
        ])
        client = _mock_client([tags_resp, links_resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(MastodonSource().fetch_trending(count=10))
        assert len(items) == 2
        assert items[0].keyword == "#python"
        assert items[1].keyword == "Cool Article"

    def test_custom_instance(self):
        from trend_pulse.sources.mastodon import MastodonSource
        src = MastodonSource(instance="https://fosstodon.org")
        assert src.instance == "https://fosstodon.org"


# ═══════════════════════════════════════════════════════
# 4. Bluesky
# ═══════════════════════════════════════════════════════


class TestBlueskySource:
    def test_fetch_trending(self):
        from trend_pulse.sources.bluesky import BlueskySource
        topics_resp = _json_resp({"topics": [
            {"topic": "AI Safety", "displayName": "AI Safety", "link": ""},
        ]})
        feeds_resp = _json_resp({"feeds": [
            {"displayName": "Tech Feed", "likeCount": 500, "uri": "at://feed/1", "creator": {"handle": "user.bsky"}, "description": "Tech stuff"},
        ]})
        client = _mock_client([topics_resp, feeds_resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(BlueskySource().fetch_trending(count=10))
        assert len(items) == 2
        assert items[0].keyword == "AI Safety"
        assert items[1].keyword == "Tech Feed"

    def test_search(self):
        from trend_pulse.sources.bluesky import BlueskySource
        resp = _json_resp({"posts": [
            {"record": {"text": "Hello world", "createdAt": "2026-03-10"}, "likeCount": 10, "repostCount": 5, "replyCount": 3, "author": {"handle": "user.bsky"}, "uri": "at://did/app.bsky.feed.post/abc"},
        ]})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(BlueskySource().search("hello"))
        assert len(items) == 1


# ═══════════════════════════════════════════════════════
# 5. Wikipedia
# ═══════════════════════════════════════════════════════


class TestWikipediaSource:
    def test_geo_to_project(self):
        from trend_pulse.sources.wikipedia import WikipediaSource
        assert WikipediaSource._geo_to_project("TW") == "zh.wikipedia"
        assert WikipediaSource._geo_to_project("JP") == "ja.wikipedia"
        assert WikipediaSource._geo_to_project("US") == "en.wikipedia"
        assert WikipediaSource._geo_to_project("") == "en.wikipedia"

    def test_fetch_trending(self):
        from trend_pulse.sources.wikipedia import WikipediaSource
        resp = _json_resp({"items": [{"articles": [
            {"article": "Python_(programming_language)", "views": 500000, "rank": 1},
            {"article": "Special:Search", "views": 100000, "rank": 2},
            {"article": "Main_Page", "views": 8000000, "rank": 3},
            {"article": "Claude_(AI)", "views": 200000, "rank": 4},
        ]}]})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(WikipediaSource().fetch_trending(count=10))
        # Special: and Main_Page should be filtered
        assert len(items) == 2
        assert items[0].keyword == "Python (programming language)"
        assert items[1].keyword == "Claude (AI)"


# ═══════════════════════════════════════════════════════
# 6. GitHub Trending
# ═══════════════════════════════════════════════════════


class TestGitHubTrendingSource:
    def test_parse_html(self):
        from trend_pulse.sources.github_trending import GitHubTrendingSource
        html = '''
        <article class="Box-row">
            <h2><a href="/user/cool-repo">user/cool-repo</a></h2>
            <p class="col-9 text-gray my-1 pr-4">A cool project</p>
            <span itemprop="programmingLanguage">Python</span>
            <a href="/user/cool-repo/stargazers">1,234</a>
            <span>42 stars today</span>
        </article>
        <article class="Box-row">
            <h2><a href="/org/another-repo">org/another-repo</a></h2>
            <p class="col-9 text-gray my-1 pr-4">Another project</p>
            <span>10 stars today</span>
        </article>
        '''
        src = GitHubTrendingSource()
        items = src._parse_html(html, 20)
        assert len(items) == 2
        assert items[0].keyword == "user/cool-repo"
        assert items[0].metadata["stars_today"] == 42
        assert items[0].metadata["language"] == "Python"

    def test_normalize_browser_data_dict(self):
        from trend_pulse.sources.github_trending import GitHubTrendingSource
        data = {"repositories": [
            {"name": "user/repo", "stars_today": 50, "total_stars": 1000, "description": "Test", "language": "Rust"},
        ]}
        src = GitHubTrendingSource()
        items = src._normalize_browser_data(data, 10)
        assert len(items) == 1
        assert items[0].keyword == "user/repo"
        assert items[0].metadata["via"] == "cf-browser-rendering"

    def test_normalize_browser_data_list(self):
        from trend_pulse.sources.github_trending import GitHubTrendingSource
        data = [{"name": "a/b", "stars_today": 10, "total_stars": 100}]
        items = GitHubTrendingSource()._normalize_browser_data(data, 10)
        assert len(items) == 1

    def test_language_validation(self):
        from trend_pulse.sources.github_trending import GitHubTrendingSource
        # geo > 2 chars treated as language; injection attempt rejected by regex
        html = '<article class="Box-row"><h2><a href="/a/b">a/b</a></h2><span>1 stars today</span></article>'
        resp = _text_resp(html)
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            src = GitHubTrendingSource()
            _run(src.fetch_trending(geo="python;rm -rf", count=5))
            # Verify the malicious geo was rejected: URL should be the base trending URL, not /trending/python;rm -rf
            call_args = client.get.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "rm" not in url
            assert url == "https://github.com/trending"


# ═══════════════════════════════════════════════════════
# 7. PyPI
# ═══════════════════════════════════════════════════════


class TestPyPISource:
    def test_fetch_trending(self):
        from trend_pulse.sources.pypi import PyPISource
        resp = _json_resp({"data": {"last_day": 50000, "last_week": 280000, "last_month": 1200000}})
        # Return same response for each package call
        client = _mock_client([resp] * 20)
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(PyPISource().fetch_trending(count=3))
        assert len(items) == 3
        assert all(i.source == "pypi" for i in items)
        assert items[0].metadata["last_day"] == 50000


# ═══════════════════════════════════════════════════════
# 8. Google News
# ═══════════════════════════════════════════════════════


class TestGoogleNewsSource:
    def test_fetch_trending(self):
        from trend_pulse.sources.google_news import GoogleNewsSource
        xml = """<?xml version="1.0"?>
        <rss><channel>
            <item><title>Breaking News</title><link>https://news.com/1</link><pubDate>Mon, 10 Mar 2026</pubDate></item>
            <item><title>Tech Update</title><link>https://news.com/2</link><pubDate>Mon, 10 Mar 2026</pubDate></item>
        </channel></rss>"""
        resp = _text_resp(xml)
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(GoogleNewsSource().fetch_trending(geo="TW", count=5))
        assert len(items) == 2
        assert items[0].keyword == "Breaking News"
        assert items[0].score == 100  # First item rank-based
        assert items[1].score == 97   # Second item


# ═══════════════════════════════════════════════════════
# 9. Lobsters
# ═══════════════════════════════════════════════════════


class TestLobstersSource:
    def test_fetch_trending(self):
        from trend_pulse.sources.lobsters import LobstersSource
        resp = _json_resp([
            {"title": "Cool Tech", "score": 60, "url": "https://cool.tech", "comments_url": "https://lobste.rs/s/abc", "created_at": "2026-03-10", "short_id": "abc", "comment_count": 15, "submitter_user": "alice", "tags": ["programming"]},
        ])
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(LobstersSource().fetch_trending(count=5))
        assert len(items) == 1
        assert items[0].keyword == "Cool Tech"
        assert items[0].score == 20.0  # 60/3


# ═══════════════════════════════════════════════════════
# 10. Dev.to
# ═══════════════════════════════════════════════════════


class TestDevToSource:
    def test_parse_articles(self):
        from trend_pulse.sources.devto import DevToSource
        articles = [
            {"title": "Learn Python", "public_reactions_count": 200, "url": "https://dev.to/p", "published_at": "2026-03-10", "id": 1, "comments_count": 10, "user": {"username": "bob"}, "tag_list": ["python"]},
        ]
        items = DevToSource()._parse_articles(articles)
        assert len(items) == 1
        assert items[0].keyword == "Learn Python"
        assert items[0].score == 40.0  # 200/5

    def test_search(self):
        from trend_pulse.sources.devto import DevToSource
        resp = _json_resp([
            {"title": "AI Post", "public_reactions_count": 50, "url": "https://dev.to/ai", "published_at": "2026-03-10", "id": 2, "comments_count": 3, "user": {"username": "a"}, "tag_list": []},
        ])
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(DevToSource().search("AI"))
        assert len(items) == 1


# ═══════════════════════════════════════════════════════
# 11. npm
# ═══════════════════════════════════════════════════════


class TestNpmSource:
    def test_fetch_package(self):
        from trend_pulse.sources.npm import NpmSource
        day_resp = _json_resp({"downloads": 100000})
        week_resp = _json_resp({"downloads": 600000})
        client = _mock_client([])
        client.get = AsyncMock(side_effect=[day_resp, week_resp])
        item = _run(NpmSource()._fetch_package(client, "react"))
        assert item.keyword == "react"
        assert item.metadata["downloads_daily"] == 100000


# ═══════════════════════════════════════════════════════
# 12. Reddit
# ═══════════════════════════════════════════════════════


class TestRedditSource:
    def test_parse_posts(self):
        from trend_pulse.sources.reddit import RedditSource
        children = [
            {"data": {"title": "Cool Post", "score": 5000, "permalink": "/r/test/cool", "created_utc": 1741600000, "subreddit": "test", "author": "u1", "num_comments": 50, "upvote_ratio": 0.95}},
        ]
        items = RedditSource()._parse_posts(children)
        assert len(items) == 1
        assert items[0].keyword == "Cool Post"
        assert items[0].score == 10.0  # 5000/500, capped at 100

    def test_search(self):
        from trend_pulse.sources.reddit import RedditSource
        resp = _json_resp({"data": {"children": [
            {"data": {"title": "Search Result", "score": 100, "permalink": "/r/test/s", "created_utc": 1741600000, "subreddit": "test", "author": "u2", "num_comments": 5, "upvote_ratio": 0.9}},
        ]}})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(RedditSource().search("test"))
        assert len(items) == 1


# ═══════════════════════════════════════════════════════
# 13. CoinGecko
# ═══════════════════════════════════════════════════════


class TestCoinGeckoSource:
    def test_fetch_trending(self):
        from trend_pulse.sources.coingecko import CoinGeckoSource
        resp = _json_resp({
            "coins": [
                {"item": {"name": "Bitcoin", "id": "bitcoin", "symbol": "BTC", "market_cap_rank": 1, "thumb": ""}},
                {"item": {"name": "Ethereum", "id": "ethereum", "symbol": "ETH", "market_cap_rank": 2, "thumb": ""}},
            ],
            "nfts": [
                {"name": "Cool NFT", "id": "cool-nft", "symbol": "CNFT", "thumb": ""},
            ],
        })
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(CoinGeckoSource().fetch_trending(count=10))
        assert len(items) == 3
        assert items[0].keyword == "Bitcoin"
        assert items[0].score == 98  # 100 - 1*2
        assert items[2].category == "crypto-nft"


# ═══════════════════════════════════════════════════════
# 14. Docker Hub
# ═══════════════════════════════════════════════════════


class TestDockerHubSource:
    def test_format_pulls(self):
        from trend_pulse.sources.dockerhub import _format_pulls
        assert _format_pulls(5_000_000_000) == "5.0B pulls"
        assert _format_pulls(50_000_000) == "50M pulls"
        assert _format_pulls(50_000) == "50K pulls"
        assert _format_pulls(500) == "500 pulls"

    def test_fetch_trending(self):
        from trend_pulse.sources.dockerhub import DockerHubSource
        resp = _json_resp({"results": [
            {"name": "nginx", "pull_count": 2_000_000_000, "star_count": 500, "last_updated": "2026-03-10", "description": "Web server"},
        ]})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(DockerHubSource().fetch_trending(count=5))
        assert len(items) == 1
        assert items[0].keyword == "nginx"
        assert items[0].traffic == "2.0B pulls"


# ═══════════════════════════════════════════════════════
# 15. Stack Overflow
# ═══════════════════════════════════════════════════════


class TestStackOverflowSource:
    def test_parse_questions(self):
        from trend_pulse.sources.stackoverflow import StackOverflowSource
        data = {"items": [
            {"title": "How to use &amp; in Python?", "score": 50, "view_count": 1000, "link": "https://so.com/q/1", "creation_date": 1741600000, "tags": ["python"], "answer_count": 3, "is_answered": True, "owner": {"display_name": "user"}},
        ]}
        items = StackOverflowSource()._parse_questions(data)
        assert len(items) == 1
        assert items[0].keyword == "How to use & in Python?"  # HTML unescaped
        assert items[0].score == 10.0

    def test_search(self):
        from trend_pulse.sources.stackoverflow import StackOverflowSource
        resp = _json_resp({"items": [
            {"title": "Python question", "score": 20, "view_count": 500, "link": "https://so.com/q/2", "creation_date": 1741600000, "tags": ["python"], "answer_count": 1, "is_answered": True, "owner": {"display_name": "u"}},
        ]})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(StackOverflowSource().search("Python"))
        assert len(items) == 1


# ═══════════════════════════════════════════════════════
# 16. ArXiv
# ═══════════════════════════════════════════════════════


class TestArXivSource:
    def test_parse_feed(self):
        from trend_pulse.sources.arxiv import ArXivSource
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Multi-line
            Title Here</title>
            <summary>This is an abstract.</summary>
            <published>2026-03-10T00:00:00Z</published>
            <link href="https://arxiv.org/abs/1234" type="text/html"/>
            <category term="cs.AI"/>
            <author><name>Alice</name></author>
            <author><name>Bob</name></author>
          </entry>
        </feed>"""
        items = ArXivSource()._parse_feed(xml)
        assert len(items) == 1
        assert "Multi-line" in items[0].keyword and "Title Here" in items[0].keyword
        assert items[0].url == "https://arxiv.org/abs/1234"
        assert items[0].metadata["authors"] == ["Alice", "Bob"]
        assert items[0].metadata["categories"] == ["cs.AI"]

    def test_search(self):
        from trend_pulse.sources.arxiv import ArXivSource
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>AI Paper</title>
            <summary>Abstract</summary>
            <published>2026-03-10</published>
            <id>http://arxiv.org/abs/5678</id>
            <author><name>Eve</name></author>
          </entry>
        </feed>"""
        resp = _text_resp(xml)
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(ArXivSource().search("AI"))
        assert len(items) == 1
        assert items[0].keyword == "AI Paper"


# ═══════════════════════════════════════════════════════
# 17. Product Hunt
# ═══════════════════════════════════════════════════════


class TestProductHuntSource:
    def test_parse_html(self):
        from trend_pulse.sources.producthunt import ProductHuntSource
        html = '''{"__typename":"Post","someField":"x","name":"Cool App","tagline":"Do things","slug":"cool-app","votesCount":500}'''
        items = ProductHuntSource()._parse_html(html)
        assert len(items) == 1
        assert items[0].keyword == "Cool App"
        assert items[0].score == 50.0  # 500/10
        assert items[0].metadata["tagline"] == "Do things"

    def test_search(self):
        from trend_pulse.sources.producthunt import ProductHuntSource
        html = '''{"__typename":"Post","x":"y","name":"Search Result","tagline":"Found it","slug":"search-result","votesCount":200}'''
        resp = _text_resp(html)
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(ProductHuntSource().search("search"))
        assert len(items) == 1
        assert items[0].keyword == "Search Result"


# ═══════════════════════════════════════════════════════
# 18. Lemmy
# ═══════════════════════════════════════════════════════


class TestLemmySource:
    def test_parse_posts(self):
        from trend_pulse.sources.lemmy import LemmySource
        posts = [
            {"post": {"name": "Cool Post", "id": 1, "ap_id": "https://lemmy.world/post/1", "published": "2026-03-10", "url": "https://example.com"},
             "counts": {"upvotes": 250, "comments": 30},
             "community": {"name": "tech"},
             "creator": {"name": "alice"}},
        ]
        items = LemmySource()._parse_posts(posts)
        assert len(items) == 1
        assert items[0].keyword == "Cool Post"
        assert items[0].score == 5.0  # 250/50
        assert items[0].metadata["external_url"] == "https://example.com"

    def test_search(self):
        from trend_pulse.sources.lemmy import LemmySource
        resp = _json_resp({"posts": [
            {"post": {"name": "Found Post", "id": 2, "ap_id": "https://lemmy.world/post/2", "published": "2026-03-10"},
             "counts": {"upvotes": 100, "comments": 5},
             "community": {"name": "linux"},
             "creator": {"name": "bob"}},
        ]})
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(LemmySource().search("linux"))
        assert len(items) == 1


# ═══════════════════════════════════════════════════════
# 19. Dcard
# ═══════════════════════════════════════════════════════


class TestDcardSource:
    def test_parse_posts(self):
        from trend_pulse.sources.dcard import DcardSource
        posts = [
            {"title": "好文", "likeCount": 500, "commentCount": 100, "id": 1, "forumAlias": "talk", "forumName": "閒聊", "createdAt": "2026-03-10", "gender": "F", "school": "NTU", "excerpt": "內文"},
        ]
        items = DcardSource()._parse_posts(posts)
        assert len(items) == 1
        assert items[0].keyword == "好文"
        assert items[0].score == 3.5  # (500 + 100*2) / 200
        assert items[0].metadata["forum"] == "talk"

    def test_fetch_trending(self):
        from trend_pulse.sources.dcard import DcardSource
        resp = _json_resp([
            {"title": "Post 1", "likeCount": 200, "commentCount": 50, "id": 1, "forumAlias": "funny", "forumName": "有趣", "createdAt": "2026-03-10", "gender": "", "school": "", "excerpt": ""},
        ])
        client = _mock_client([resp])
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(DcardSource().fetch_trending(count=5))
        assert len(items) == 1
        assert items[0].source == "dcard"


# ═══════════════════════════════════════════════════════
# 20. PTT
# ═══════════════════════════════════════════════════════


class TestPTTSource:
    def test_parse_articles_normal(self):
        from trend_pulse.sources.ptt import PTTSource
        html = '''
        <div class="r-ent">
            <div class="nrec"><span class="hl f3">42</span></div>
            <div class="title"><a href="/bbs/Gossiping/M.123.A.456.html">好文章標題</a></div>
            <div class="author">testuser</div>
        </div>'''
        items = PTTSource()._parse_articles(html, "Gossiping")
        assert len(items) == 1
        assert items[0].keyword == "好文章標題"
        assert items[0].metadata["pushes"] == 42

    def test_parse_articles_bao(self):
        from trend_pulse.sources.ptt import PTTSource
        html = '''
        <div class="r-ent">
            <div class="nrec"><span class="hl f9">爆</span></div>
            <div class="title"><a href="/bbs/Gossiping/M.456.A.789.html">爆文標題</a></div>
            <div class="author">hotuser</div>
        </div>'''
        items = PTTSource()._parse_articles(html, "Gossiping")
        assert len(items) == 1
        assert items[0].metadata["pushes"] == 100
        assert items[0].score == 100.0

    def test_parse_articles_negative(self):
        from trend_pulse.sources.ptt import PTTSource
        html = '''
        <div class="r-ent">
            <div class="nrec"><span class="hl f1">X1</span></div>
            <div class="title"><a href="/bbs/Gossiping/M.111.A.222.html">噓文標題</a></div>
            <div class="author">baduser</div>
        </div>'''
        items = PTTSource()._parse_articles(html, "Gossiping")
        assert len(items) == 1
        assert items[0].metadata["pushes"] == -10
        assert items[0].score == 0  # max(-10, 0)

    def test_parse_articles_skip_deleted(self):
        from trend_pulse.sources.ptt import PTTSource
        html = '''
        <div class="r-ent">
            <div class="nrec"><span class="hl f3">10</span></div>
            <div class="title"><a href="/bbs/Gossiping/M.999.A.000.html">(本文已被刪除) [author]</a></div>
            <div class="author">del</div>
        </div>'''
        items = PTTSource()._parse_articles(html, "Gossiping")
        assert len(items) == 0

    def test_fetch_trending_multiple_boards(self):
        from trend_pulse.sources.ptt import PTTSource
        html = '''
        <div class="r-ent">
            <div class="nrec"><span class="hl f3">50</span></div>
            <div class="title"><a href="/bbs/Board/M.1.A.2.html">文章</a></div>
            <div class="author">user</div>
        </div>'''
        resp = _text_resp(html)
        # 5 boards × 1 response each
        client = _mock_client([resp] * 5)
        with patch("httpx.AsyncClient", return_value=client):
            items = _run(PTTSource().fetch_trending(count=3))
        # Each board returns 1 article, total 5, but limited to 3
        assert len(items) == 3


# ═══════════════════════════════════════════════════════
# Cross-cutting: Base class and source registry
# ═══════════════════════════════════════════════════════


class TestSourceRegistry:
    def test_all_sources_count(self):
        from trend_pulse.sources import ALL_SOURCES
        assert len(ALL_SOURCES) == 20

    def test_all_sources_are_trend_source(self):
        from trend_pulse.sources import ALL_SOURCES
        for cls in ALL_SOURCES:
            assert issubclass(cls, TrendSource)

    def test_all_sources_have_unique_names(self):
        from trend_pulse.sources import ALL_SOURCES
        names = [cls.name for cls in ALL_SOURCES]
        assert len(names) == len(set(names))

    def test_all_sources_have_description(self):
        from trend_pulse.sources import ALL_SOURCES
        for cls in ALL_SOURCES:
            assert cls.description, f"{cls.name} missing description"

    def test_all_sources_require_no_auth(self):
        from trend_pulse.sources import ALL_SOURCES
        for cls in ALL_SOURCES:
            assert cls.requires_auth is False, f"{cls.name} requires auth"

    def test_base_search_returns_empty(self):
        """Default search() should return empty list."""
        class DummySource(TrendSource):
            name = "dummy"
            async def fetch_trending(self, geo="", count=20):
                return []
        items = _run(DummySource().search("test"))
        assert items == []

    def test_trend_item_to_dict(self):
        item = TrendItem(
            keyword="test", score=50.0, source="test_source",
            url="https://example.com", traffic="100", category="tech",
            published="2026-03-10", metadata={"key": "val"},
            direction="rising", velocity=5.0, previous_score=30.0,
        )
        d = item.to_dict()
        assert d["keyword"] == "test"
        assert d["score"] == 50.0
        assert d["direction"] == "rising"
        assert d["velocity"] == 5.0
        assert d["metadata"] == {"key": "val"}


# ═══════════════════════════════════════════════════════
# Aggregator integration
# ═══════════════════════════════════════════════════════


class TestAggregator:
    def test_list_sources_returns_20(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        sources = agg.list_sources()
        assert len(sources) == 20

    def test_select_subset(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        selected = agg._select(["hackernews", "reddit"])
        assert set(selected.keys()) == {"hackernews", "reddit"}

    def test_select_none_returns_all(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        selected = agg._select(None)
        assert len(selected) == 20

    def test_available_sources(self):
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        assert "hackernews" in agg.available_sources
        assert "dcard" in agg.available_sources
        assert len(agg.available_sources) == 20


# ═══════════════════════════════════════════════════════
# Velocity enrichment
# ═══════════════════════════════════════════════════════


class TestVelocityEnrichment:
    def test_new_item_direction(self):
        """Items with no history should be marked as 'new'."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB

        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={})

        items = [TrendItem(keyword="test", score=50.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        assert result[0].direction == "new"
        assert result[0].velocity == 0.0
        assert result[0].previous_score == 0.0

    def test_rising_direction(self):
        """Items with large score increase should be 'rising'."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB
        from datetime import datetime, timezone, timedelta

        prev_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={
            "test::hackernews": {"score": 20.0, "timestamp": prev_time, "source": "hackernews"},
        })

        items = [TrendItem(keyword="test", score=80.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        assert result[0].direction == "rising"
        assert result[0].velocity > 10.0
        assert result[0].previous_score == 20.0

    def test_declining_direction(self):
        """Items with large score decrease should be 'declining'."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB
        from datetime import datetime, timezone, timedelta

        prev_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={
            "test::hackernews": {"score": 80.0, "timestamp": prev_time, "source": "hackernews"},
        })

        items = [TrendItem(keyword="test", score=20.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        assert result[0].direction == "declining"
        assert result[0].velocity < -10.0

    def test_stable_direction(self):
        """Items with small score change should be 'stable'."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB
        from datetime import datetime, timezone, timedelta

        prev_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={
            "test::hackernews": {"score": 50.0, "timestamp": prev_time, "source": "hackernews"},
        })

        items = [TrendItem(keyword="test", score=52.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        assert result[0].direction == "stable"

    def test_invalid_timestamp_fallback(self):
        """Invalid timestamp should be treated as no history (direction='new')."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB

        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={
            "test::hackernews": {"score": 50.0, "timestamp": "not-a-date", "source": "hackernews"},
        })

        items = [TrendItem(keyword="test", score=60.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        assert result[0].direction == "new"
        assert result[0].velocity == 0.0
        assert result[0].previous_score == 50.0

    def test_z_suffix_timestamp_parsed(self):
        """Z-suffix ISO 8601 timestamps should parse correctly on all Python versions."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB
        from datetime import datetime, timezone, timedelta

        prev_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={
            "test::hackernews": {"score": 50.0, "timestamp": prev_time, "source": "hackernews"},
        })

        items = [TrendItem(keyword="test", score=55.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        # Should parse correctly, not fall back to "new"
        assert result[0].direction in ("rising", "stable", "declining")
        assert result[0].previous_score == 50.0

    def test_aware_timestamp_preserved(self):
        """Timezone-aware timestamps should not be overwritten."""
        from trend_pulse.velocity import enrich_with_velocity
        from trend_pulse.history import TrendDB

        db = AsyncMock(spec=TrendDB)
        db.get_latest_scores = AsyncMock(return_value={
            "test::hackernews": {"score": 50.0, "timestamp": "2026-03-10T12:00:00+00:00", "source": "hackernews"},
        })

        items = [TrendItem(keyword="test", score=55.0, source="hackernews")]
        result = _run(enrich_with_velocity(items, db))
        # Should not error — aware timestamp handled correctly
        assert result[0].direction in ("rising", "stable", "declining", "new")
