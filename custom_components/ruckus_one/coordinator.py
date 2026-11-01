"""Data update coordinator for RUCKUS One."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import RuckusOneApi, RuckusOneAuthError, RuckusOneError
from .const import CONF_VENUE_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

ALIAS_REFRESH = timedelta(minutes=10)


@dataclass
class RuckusOneData:
    """Snapshot of one venue."""

    aps: dict[str, dict[str, Any]]  # keyed by serial number
    clients: dict[str, dict[str, Any]]  # keyed by lower-case MAC address
    aliases: dict[str, str]  # client aliases set in RUCKUS One, keyed by MAC
    client_count: int


type RuckusOneConfigEntry = ConfigEntry[RuckusOneCoordinator]


class RuckusOneCoordinator(DataUpdateCoordinator[RuckusOneData]):
    """Poll the access points of the configured venue."""

    config_entry: RuckusOneConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: RuckusOneConfigEntry, api: RuckusOneApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self.venue_id: str = entry.data[CONF_VENUE_ID]
        self._aliases: dict[str, str] = {}
        self._aliases_updated = None

    async def _async_update_data(self) -> RuckusOneData:
        try:
            aps = await self.api.async_get_aps(self.venue_id)
            clients = await self.api.async_get_clients(self.venue_id)
            now = dt_util.utcnow()
            if self._aliases_updated is None or now - self._aliases_updated > ALIAS_REFRESH:
                try:
                    self._aliases = await self.api.async_get_aliases()
                    self._aliases_updated = now
                except RuckusOneAuthError:
                    raise
                except RuckusOneError as err:
                    # Aliases are cosmetic: keep the previous ones on failure.
                    _LOGGER.debug("Could not refresh client aliases: %s", err)
        except RuckusOneAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except RuckusOneError as err:
            raise UpdateFailed(err) from err
        by_serial = {ap["serialNumber"]: ap for ap in aps if ap.get("serialNumber")}
        by_mac = {
            c["macAddress"].lower(): c
            for c in clients
            if c.get("macAddress") and self._in_venue(c, by_serial)
        }
        return RuckusOneData(
            aps=by_serial,
            clients=by_mac,
            aliases=self._aliases,
            client_count=len(by_mac),
        )

    def _in_venue(self, client: dict[str, Any], aps: dict[str, dict[str, Any]]) -> bool:
        """Keep only clients of this venue (the API filter is not always strict)."""
        if venue := (client.get("venueInformation") or {}).get("id"):
            return venue == self.venue_id
        return (client.get("apInformation") or {}).get("serialNumber") in aps
