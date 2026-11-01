"""Minimal async client for the RUCKUS One REST API."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

from .const import REGIONS

PAGE_SIZE = 100
TIMEOUT = aiohttp.ClientTimeout(total=30)


class RuckusOneError(Exception):
    """Generic API error."""


class RuckusOneAuthError(RuckusOneError):
    """Invalid credentials."""


class RuckusOneApi:
    """RUCKUS One client using an Application Token (OAuth2 client credentials)."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        region: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._session = session
        self._oauth_host, self._api_host, _ = REGIONS[region]
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry = 0.0
        self._lock = asyncio.Lock()

    async def _ensure_token(self) -> str:
        async with self._lock:
            if self._token and time.monotonic() < self._token_expiry - 120:
                return self._token
            url = f"https://{self._oauth_host}/oauth2/token/{self._tenant_id}"
            data = {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }
            try:
                async with self._session.post(url, data=data, timeout=TIMEOUT) as resp:
                    if resp.status in (400, 401, 403, 404):
                        raise RuckusOneAuthError(f"token request refused ({resp.status})")
                    resp.raise_for_status()
                    body = await resp.json()
            except aiohttp.ClientError as err:
                raise RuckusOneError(err) from err
            self._token = body["access_token"]
            self._token_expiry = time.monotonic() + int(body.get("expires_in", 3600))
            return self._token

    async def _request(self, method: str, path: str, json: Any = None) -> Any:
        for attempt in range(2):
            token = await self._ensure_token()
            try:
                async with self._session.request(
                    method,
                    f"https://{self._api_host}{path}",
                    json=json,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        # Token revoked or expired early: get a new one and retry once.
                        self._token = None
                        continue
                    if resp.status in (401, 403):
                        raise RuckusOneAuthError(f"{path} refused ({resp.status})")
                    resp.raise_for_status()
                    return await resp.json()
            except aiohttp.ClientError as err:
                raise RuckusOneError(err) from err
        raise RuckusOneAuthError(f"{path} refused after token refresh")

    async def _query_all(self, path: str, venue_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            body = await self._request(
                "POST",
                path,
                {"filters": {"venueId": [venue_id]}, "page": page, "pageSize": PAGE_SIZE},
            )
            data = body.get("data") or []
            items.extend(data)
            if not data or len(items) >= body.get("totalCount", 0):
                return items
            page += 1

    async def async_get_venues(self) -> list[dict[str, Any]]:
        """Return all venues of the tenant."""
        return await self._request("GET", "/venues")

    async def async_get_aps(self, venue_id: str) -> list[dict[str, Any]]:
        """Return the access points of one venue."""
        return await self._query_all("/venues/aps/query", venue_id)

    async def async_get_clients(self, venue_id: str) -> list[dict[str, Any]]:
        """Return the Wi-Fi clients connected in one venue."""
        return await self._query_all("/venues/aps/clients/query", venue_id)
