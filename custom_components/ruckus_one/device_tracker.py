"""Wi-Fi client presence for RUCKUS One (limited to the configured venue)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import RuckusOneConfigEntry, RuckusOneCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RuckusOneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one tracker per Wi-Fi client seen in the venue."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    # Recreate trackers of clients seen before, so they show "away" after a restart.
    registry = er.async_get(hass)
    restored = {
        reg.unique_id: reg.original_name
        for reg in er.async_entries_for_config_entry(registry, entry.entry_id)
        if reg.domain == "device_tracker"
    }

    @callback
    def add_new_clients(macs: set[str] | None = None) -> None:
        new = (macs or set(coordinator.data.clients)) - known
        if not new:
            return
        known.update(new)
        async_add_entities(
            RuckusOneClientTracker(coordinator, mac, restored.get(mac)) for mac in new
        )

    add_new_clients(set(restored) | set(coordinator.data.clients))
    entry.async_on_unload(coordinator.async_add_listener(add_new_clients))


class RuckusOneClientTracker(CoordinatorEntity[RuckusOneCoordinator], ScannerEntity):
    """Presence of one Wi-Fi client."""

    _unrecorded_attributes = frozenset({"rssi", "snr", "channel", "connected_since"})

    def __init__(
        self, coordinator: RuckusOneCoordinator, mac: str, known_name: str | None = None
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = mac
        client = coordinator.data.clients.get(mac) or {}
        self._attr_name = client.get("hostname") or known_name or mac

    @property
    def _client(self) -> dict[str, Any] | None:
        return self.coordinator.data.clients.get(self._mac)

    @property
    def entity_registry_enabled_default(self) -> bool:
        # ScannerEntity disables unknown MACs by default; show every venue client.
        return True

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def ip_address(self) -> str | None:
        return self._client.get("ipAddress") if self._client else None

    @property
    def hostname(self) -> str | None:
        return self._client.get("hostname") if self._client else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not (client := self._client):
            return None
        ap = client.get("apInformation") or {}
        network = client.get("networkInformation") or {}
        signal = client.get("signalStatus") or {}
        radio = client.get("radioStatus") or {}
        return {
            "access_point": ap.get("name"),
            "ssid": network.get("ssid"),
            "vlan": network.get("vlan"),
            "band": client.get("band"),
            "channel": radio.get("channel"),
            "rssi": signal.get("rssi"),
            "snr": signal.get("snr"),
            "signal_health": signal.get("health"),
            "device_type": client.get("deviceType"),
            "os_type": client.get("osType"),
            "connected_since": client.get("connectedTime"),
        }
