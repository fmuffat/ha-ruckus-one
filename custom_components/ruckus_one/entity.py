"""Base entities for RUCKUS One."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REGION, CONF_TENANT_ID, CONF_VENUE_NAME, DOMAIN, MANUFACTURER, REGIONS
from .coordinator import RuckusOneCoordinator


class RuckusOneVenueEntity(CoordinatorEntity[RuckusOneCoordinator]):
    """Entity attached to the venue device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RuckusOneCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        dashboard_host = REGIONS[entry.data[CONF_REGION]][2]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.venue_id)},
            name=entry.data[CONF_VENUE_NAME],
            manufacturer=MANUFACTURER,
            model="RUCKUS One venue",
            configuration_url=f"https://{dashboard_host}/{entry.data[CONF_TENANT_ID]}/t/dashboard",
        )


class RuckusOneApEntity(CoordinatorEntity[RuckusOneCoordinator]):
    """Entity attached to one access point."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RuckusOneCoordinator, serial: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        ap = coordinator.data.aps[serial]
        connections = set()
        if mac := ap.get("macAddress"):
            connections.add((CONNECTION_NETWORK_MAC, mac.lower()))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            connections=connections,
            name=ap.get("name") or serial,
            manufacturer=MANUFACTURER,
            model=ap.get("model"),
            serial_number=serial,
            sw_version=ap.get("firmwareVersion"),
        )

    @property
    def ap(self) -> dict[str, Any] | None:
        """Return the latest data of this AP, or None if it left the venue."""
        return self.coordinator.data.aps.get(self._serial)

    @property
    def available(self) -> bool:
        return super().available and self.ap is not None
