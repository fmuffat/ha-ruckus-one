"""Data update coordinator for RUCKUS One."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RuckusOneApi, RuckusOneAuthError, RuckusOneError
from .const import CONF_VENUE_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class RuckusOneData:
    """Snapshot of one venue."""

    aps: dict[str, dict[str, Any]]  # keyed by serial number
    clients: dict[str, dict[str, Any]]  # keyed by lower-case MAC address
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

    async def _async_update_data(self) -> RuckusOneData:
        try:
            aps = await self.api.async_get_aps(self.venue_id)
            clients = await self.api.async_get_clients(self.venue_id)
        except RuckusOneAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except RuckusOneError as err:
            raise UpdateFailed(err) from err
        by_serial = {ap["serialNumber"]: ap for ap in aps if ap.get("serialNumber")}
        by_mac = {c["macAddress"].lower(): c for c in clients if c.get("macAddress")}
        return RuckusOneData(
            aps=by_serial,
            clients=by_mac,
            client_count=len(by_mac),
        )
