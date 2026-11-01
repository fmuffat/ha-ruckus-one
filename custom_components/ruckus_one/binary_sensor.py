"""Binary sensors for RUCKUS One."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATUS_OPERATIONAL_PREFIX
from .coordinator import RuckusOneConfigEntry, RuckusOneCoordinator
from .entity import RuckusOneApEntity


@dataclass(frozen=True, kw_only=True)
class RuckusOneApBinarySensorDescription(BinarySensorEntityDescription):
    """Describe an AP binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


AP_BINARY_SENSORS: tuple[RuckusOneApBinarySensorDescription, ...] = (
    RuckusOneApBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda ap: ap.get("status", "").startswith(STATUS_OPERATIONAL_PREFIX),
    ),
    RuckusOneApBinarySensorDescription(
        key="poe_underpowered",
        translation_key="poe_underpowered",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ap: ap.get("poeUnderPowered"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RuckusOneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def add_new_aps() -> None:
        new = set(coordinator.data.aps) - known
        if not new:
            return
        known.update(new)
        async_add_entities(
            RuckusOneApBinarySensor(coordinator, serial, description)
            for serial in new
            for description in AP_BINARY_SENSORS
        )

    add_new_aps()
    entry.async_on_unload(coordinator.async_add_listener(add_new_aps))


class RuckusOneApBinarySensor(RuckusOneApEntity, BinarySensorEntity):
    """Binary sensor of one access point."""

    entity_description: RuckusOneApBinarySensorDescription

    def __init__(
        self,
        coordinator: RuckusOneCoordinator,
        serial: str,
        description: RuckusOneApBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, serial)
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.ap) if self.ap else None
