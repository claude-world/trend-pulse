from .google_trends import GoogleTrendsSource
from .hackernews import HackerNewsSource
from .mastodon import MastodonSource
from .bluesky import BlueskySource
from .wikipedia import WikipediaSource
from .github_trending import GitHubTrendingSource
from .pypi import PyPISource

ALL_SOURCES = [
    GoogleTrendsSource,
    HackerNewsSource,
    MastodonSource,
    BlueskySource,
    WikipediaSource,
    GitHubTrendingSource,
    PyPISource,
]

__all__ = [
    "GoogleTrendsSource",
    "HackerNewsSource",
    "MastodonSource",
    "BlueskySource",
    "WikipediaSource",
    "GitHubTrendingSource",
    "PyPISource",
    "ALL_SOURCES",
]
