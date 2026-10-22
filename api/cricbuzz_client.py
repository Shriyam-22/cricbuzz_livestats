"""Client for the Cricbuzz Cricket API (hosted on RapidAPI).

One class owns every HTTP call, so headers, timeouts, retries and error
messages are handled in a single place.
"""
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)

# Endpoint paths in one place. If RapidAPI changes a path, fix it here only.
ENDPOINTS = {
    "live": "/matches/v1/live",
    "recent": "/matches/v1/recent",
    "upcoming": "/matches/v1/upcoming",
    "scorecard": "/mcenter/v1/{match_id}/scard",
    "match_info": "/mcenter/v1/{match_id}",
    "top_stats_types": "/stats/v1/topstats",
    "top_stats": "/stats/v1/topstats/0",
    "player_search": "/stats/v1/player/search",
    "player_info": "/stats/v1/player/{player_id}",
    "player_batting": "/stats/v1/player/{player_id}/batting",
    "player_bowling": "/stats/v1/player/{player_id}/bowling",
    "series_international": "/series/v1/international",
    "venue_info": "/venues/v1/{venue_id}",
}


class CricbuzzAPIError(Exception):
    """Raised for any API problem, with a message that is safe to show users."""


class CricbuzzClient:
    """Small wrapper around requests with retries and friendly errors."""

    def __init__(self, api_key=None, host=None, timeout=None):
        self.api_key = api_key if api_key is not None else config.RAPIDAPI_KEY
        self.host = host or config.RAPIDAPI_HOST
        self.base_url = f"https://{self.host}"
        self.timeout = timeout or config.API_TIMEOUT_SECONDS
        self.session = requests.Session()
        # Retry temporary failures (server errors) with growing waits: 1s, 2s, 4s.
        # 429 (rate limit) is NOT retried, so we don't burn the free quota.
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504],
                      allowed_methods=["GET"])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    @property
    def is_configured(self):
        return bool(self.api_key) and not self.api_key.startswith("your_")

    def get(self, endpoint_name, params=None, **path_values):
        """Call an endpoint by name, e.g. get("scorecard", match_id=123)."""
        if not self.is_configured:
            raise CricbuzzAPIError("API key missing. Add RAPIDAPI_KEY to your .env file.")
        path = ENDPOINTS[endpoint_name].format(**path_values)
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.host}
        try:
            response = self.session.get(self.base_url + path, headers=headers,
                                        params=params, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise CricbuzzAPIError("The Cricbuzz API took too long to respond. Try again.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise CricbuzzAPIError("Could not reach the Cricbuzz API. Check your internet.") from exc
        except requests.exceptions.RequestException as exc:
            raise CricbuzzAPIError(f"API request failed: {exc}") from exc

        if response.status_code in (401, 403):
            raise CricbuzzAPIError("API key rejected (401/403). Check RAPIDAPI_KEY and that you "
                                   "are subscribed to the Cricbuzz Cricket API on RapidAPI.")
        if response.status_code == 429:
            raise CricbuzzAPIError("API rate limit reached (429). Your free quota may be used "
                                   "up; the app will show data from the database instead.")
        if response.status_code == 204 or not response.content:
            return {}
        if not response.ok:
            raise CricbuzzAPIError(f"API returned error {response.status_code} for {path}.")
        try:
            return response.json()
        except ValueError as exc:
            raise CricbuzzAPIError("API returned data that is not valid JSON.") from exc

    # Convenience methods ---------------------------------------------------
    def live_matches(self):
        return self.get("live")

    def recent_matches(self):
        return self.get("recent")

    def upcoming_matches(self):
        return self.get("upcoming")

    def scorecard(self, match_id):
        return self.get("scorecard", match_id=match_id)

    def top_stats(self, stats_type="mostRuns", match_type=None):
        params = {"statsType": stats_type}
        if match_type:
            params["matchType"] = match_type
        return self.get("top_stats", params=params)
