"""Config flow for RUCKUS One: credentials first, then pick a venue from a list."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import RuckusOneApi, RuckusOneAuthError, RuckusOneError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_TENANT_ID,
    CONF_VENUE_ID,
    CONF_VENUE_NAME,
    DOMAIN,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION, default="eu"): SelectSelector(
            SelectSelectorConfig(
                options=list(REGIONS),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="region",
            )
        ),
        vol.Required(CONF_TENANT_ID): str,
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class RuckusOneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RUCKUS One."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, Any] = {}
        self._venues: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for region, tenant and Application Token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {k: v.strip() if isinstance(v, str) else v for k, v in user_input.items()}
            api = RuckusOneApi(
                async_get_clientsession(self.hass),
                user_input[CONF_REGION],
                user_input[CONF_TENANT_ID],
                user_input[CONF_CLIENT_ID],
                user_input[CONF_CLIENT_SECRET],
            )
            try:
                venues = await api.async_get_venues()
            except RuckusOneAuthError:
                errors["base"] = "invalid_auth"
            except RuckusOneError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while listing venues")
                errors["base"] = "unknown"
            else:
                if not venues:
                    errors["base"] = "no_venues"
                else:
                    self._credentials = user_input
                    self._venues = {v["id"]: v["name"] for v in venues}
                    return await self.async_step_venue()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_venue(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the venue to monitor from a dropdown."""
        if user_input is not None:
            venue_id = user_input[CONF_VENUE_ID]
            await self.async_set_unique_id(
                f"{self._credentials[CONF_TENANT_ID]}_{venue_id}"
            )
            self._abort_if_unique_id_configured()
            venue_name = self._venues[venue_id]
            return self.async_create_entry(
                title=venue_name,
                data={
                    **self._credentials,
                    CONF_VENUE_ID: venue_id,
                    CONF_VENUE_NAME: venue_name,
                },
            )

        options = [
            SelectOptionDict(value=venue_id, label=name)
            for venue_id, name in sorted(self._venues.items(), key=lambda v: v[1].lower())
        ]
        return self.async_show_form(
            step_id="venue",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VENUE_ID): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    )
                }
            ),
        )
