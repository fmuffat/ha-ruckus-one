# RUCKUS One for Home Assistant

Monitor the access points of a **RUCKUS One** venue in Home Assistant.

> Unofficial community integration. Not affiliated with or endorsed by RUCKUS Networks.

## Features

- Pick the **venue** to monitor from a dropdown (add the integration again for another venue)
- Per access point:
  - **Online** (connectivity) and **Status** (Operational, DisconnectedFromCloud, ...)
  - **Clients** connected
  - Channels 2.4 / 5 / 6 GHz (with bandwidth and TX power), IP address, uplink, last boot
  - **PoE underpowered** problem sensor
- Per venue: total **Wi-Fi clients** and **access points online**
- **Client presence**: one `device_tracker` per Wi-Fi client of the venue (home / away), with access point, SSID, VLAN, band, channel, RSSI, SNR, device and OS type. Each client gets its own device (linked by MAC address to an existing device when there is one); clients without a hostname get a readable name such as `Amazon Kindle 2c:91`
- New APs added to the venue appear automatically
- Polls the RUCKUS One API every 60 s; the OAuth token is renewed automatically

## Installation

### HACS (custom repository)

1. HACS > Integrations > ⋮ > Custom repositories
2. Add `https://github.com/fmuffat/ha-ruckus-one`, category **Integration**
3. Install **RUCKUS One** and restart Home Assistant

### Manual

Copy `custom_components/ruckus_one` into your `config/custom_components/` folder and restart.

## Configuration

1. In RUCKUS One, create an **Application Token**: *Administration > Account Management > Settings > Add Token*. A **read-only** scope is enough.
2. In Home Assistant: *Settings > Devices & services > Add integration > RUCKUS One*.
3. Enter the **region** (Europe, North America, Asia), your **tenant ID** (visible in the dashboard URL), the token **client ID** and **shared secret**.
4. Choose the **venue** in the list.

## Roadmap

- Per-SSID client counts
- Alarms and events

## License

MIT
