from .google_trends import GoogleTrendsSource
from .hackernews import HackerNewsSource
from .mastodon import MastodonSource
from .bluesky import BlueskySource
from .wikipedia import WikipediaSource
from .github_trending import GitHubTrendingSource
from .pypi import PyPISource
from .google_news import GoogleNewsSource
from .lobsters import LobstersSource
from .devto import DevToSource
from .npm import NpmSource
from .reddit import RedditSource
from .coingecko import CoinGeckoSource
from .dockerhub import DockerHubSource
from .stackoverflow import StackOverflowSource
from .producthunt import ProductHuntSource
from .arxiv import ArXivSource
from .lemmy import LemmySource
from .dcard import DcardSource
from .ptt import PTTSource

ALL_SOURCES = [
    GoogleTrendsSource,
    HackerNewsSource,
    MastodonSource,
    BlueskySource,
    WikipediaSource,
    GitHubTrendingSource,
    PyPISource,
    GoogleNewsSource,
    LobstersSource,
    DevToSource,
    NpmSource,
    RedditSource,
    CoinGeckoSource,
    DockerHubSource,
    StackOverflowSource,
    ProductHuntSource,
    ArXivSource,
    LemmySource,
    DcardSource,
    PTTSource,
]

__all__ = [
    "GoogleTrendsSource",
    "HackerNewsSource",
    "MastodonSource",
    "BlueskySource",
    "WikipediaSource",
    "GitHubTrendingSource",
    "PyPISource",
    "GoogleNewsSource",
    "LobstersSource",
    "DevToSource",
    "NpmSource",
    "RedditSource",
    "CoinGeckoSource",
    "DockerHubSource",
    "StackOverflowSource",
    "ProductHuntSource",
    "ArXivSource",
    "LemmySource",
    "DcardSource",
    "PTTSource",
    "ALL_SOURCES",
]
