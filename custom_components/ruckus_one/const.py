"""Constants for the RUCKUS One integration."""

from datetime import timedelta

DOMAIN = "ruckus_one"

CONF_REGION = "region"
CONF_TENANT_ID = "tenant_id"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_VENUE_ID = "venue_id"
CONF_VENUE_NAME = "venue_name"

# Region -> (OAuth host, API host, dashboard host)
REGIONS: dict[str, tuple[str, str, str]] = {
    "eu": ("eu.ruckus.cloud", "api.eu.ruckus.cloud", "eu.ruckus.cloud"),
    "na": ("ruckus.cloud", "api.ruckus.cloud", "ruckus.cloud"),
    "asia": ("asia.ruckus.cloud", "api.asia.ruckus.cloud", "asia.ruckus.cloud"),
}

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

MANUFACTURER = "RUCKUS"

# AP status codes start with the severity digit: "2_00_Operational", "3_04_DisconnectedFromCloud", ...
STATUS_OPERATIONAL_PREFIX = "2_"
