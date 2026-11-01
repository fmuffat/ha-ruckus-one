"""The RUCKUS One integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RuckusOneApi
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_TENANT_ID,
    CONF_VENUE_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import RuckusOneConfigEntry, RuckusOneCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: RuckusOneConfigEntry) -> bool:
    """Set up RUCKUS One from a config entry."""
    api = RuckusOneApi(
        async_get_clientsession(hass),
        entry.data[CONF_REGION],
        entry.data[CONF_TENANT_ID],
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
    )
    coordinator = RuckusOneCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Create the venue device first so AP devices can reference it as via_device.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.venue_id)},
        name=entry.data[CONF_VENUE_NAME],
        manufacturer=MANUFACTURER,
        model="RUCKUS One venue",
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RuckusOneConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
