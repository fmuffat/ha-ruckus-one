"""Sensors for RUCKUS One."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import STATUS_OPERATIONAL_PREFIX
from .coordinator import RuckusOneConfigEntry, RuckusOneCoordinator
from .entity import RuckusOneApEntity, RuckusOneVenueEntity

BANDS = ("2.4G", "5G", "6G")


def _radio(ap: dict[str, Any], band: str) -> dict[str, Any] | None:
    for radio in ap.get("radioStatuses") or []:
        if radio.get("band") == band:
            return radio
    return None


def _channel(band: str) -> Callable[[dict[str, Any]], int | None]:
    def value(ap: dict[str, Any]) -> int | None:
        radio = _radio(ap, band)
        return radio.get("channel") if radio else None

    return value


def _boot_time(ap: dict[str, Any]) -> datetime | None:
    if (uptime := ap.get("uptime")) is None or not ap.get("status", "").startswith(
        STATUS_OPERATIONAL_PREFIX
    ):
        return None
    # Round to the minute so the state does not change on every poll.
    boot = dt_util.utcnow() - timedelta(seconds=int(uptime))
    return boot.replace(second=0, microsecond=0)


def _status(ap: dict[str, Any]) -> str | None:
    # "2_00_Operational" -> "Operational", "3_04_DisconnectedFromCloud" -> "DisconnectedFromCloud"
    status = ap.get("status")
    return status.split("_", 2)[-1] if status else None


@dataclass(frozen=True, kw_only=True)
class RuckusOneApSensorDescription(SensorEntityDescription):
    """Describe an AP sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


AP_SENSORS: tuple[RuckusOneApSensorDescription, ...] = (
    RuckusOneApSensorDescription(
        key="clients",
        translation_key="clients",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda ap: ap.get("clientCount") or 0,
    ),
    RuckusOneApSensorDescription(
        key="status",
        translation_key="status",
        value_fn=_status,
        attrs_fn=lambda ap: {
            "severity": ap.get("statusSeverity"),
            "health": ap.get("healthStatus"),
            "last_seen": ap.get("lastSeenTime"),
        },
    ),
    RuckusOneApSensorDescription(
        key="boot_time",
        translation_key="boot_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_boot_time,
    ),
    RuckusOneApSensorDescription(
        key="ip_address",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ap: (ap.get("networkStatus") or {}).get("ipAddress"),
    ),
    RuckusOneApSensorDescription(
        key="uplink",
        translation_key="uplink",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ap: (ap.get("poePortStatus") or "").strip() or None,
        attrs_fn=lambda ap: {"poe_mode": ap.get("poeMode")},
    ),
    *(
        RuckusOneApSensorDescription(
            key=f"channel_{band.lower().replace('.', '_')}",
            translation_key=f"channel_{band.lower().replace('.', '_')}",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=_channel(band),
            attrs_fn=lambda ap, band=band: {
                "bandwidth_mhz": (_radio(ap, band) or {}).get("channelBandwidth"),
                "tx_power_dbm": (_radio(ap, band) or {}).get("actualTxPower"),
            },
        )
        for band in BANDS
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RuckusOneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    async_add_entities([RuckusOneClientsTotal(coordinator), RuckusOneApsOnline(coordinator)])
    known: set[str] = set()

    @callback
    def add_new_aps() -> None:
        new = set(coordinator.data.aps) - known
        if not new:
            return
        known.update(new)
        entities = []
        for serial in new:
            ap = coordinator.data.aps[serial]
            for description in AP_SENSORS:
                if description.key.startswith("channel_") and description.value_fn(ap) is None:
                    continue  # band not present on this model
                entities.append(RuckusOneApSensor(coordinator, serial, description))
        async_add_entities(entities)

    add_new_aps()
    entry.async_on_unload(coordinator.async_add_listener(add_new_aps))


class RuckusOneApSensor(RuckusOneApEntity, SensorEntity):
    """Sensor of one access point."""

    entity_description: RuckusOneApSensorDescription

    def __init__(
        self,
        coordinator: RuckusOneCoordinator,
        serial: str,
        description: RuckusOneApSensorDescription,
    ) -> None:
        super().__init__(coordinator, serial)
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.ap) if self.ap else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.ap and self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.ap)
        return None


class RuckusOneClientsTotal(RuckusOneVenueEntity, SensorEntity):
    """Wi-Fi clients connected in the venue."""

    _attr_translation_key = "clients_total"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RuckusOneCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.venue_id}_clients"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.client_count


class RuckusOneApsOnline(RuckusOneVenueEntity, SensorEntity):
    """Number of operational access points in the venue."""

    _attr_translation_key = "aps_online"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RuckusOneCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.venue_id}_aps_online"

    @property
    def native_value(self) -> int:
        return sum(
            ap.get("status", "").startswith(STATUS_OPERATIONAL_PREFIX)
            for ap in self.coordinator.data.aps.values()
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"total": len(self.coordinator.data.aps)}
