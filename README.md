# Proxmox CPU Control — Home Assistant Integration

Control Proxmox VE CPU frequency and monitor temperatures from Home Assistant.

Works in tandem with [**proxmox-cpu-dashboard**](https://github.com/mrkvka/proxmox-cpu-dashboard) (**Proxmox Node Hardware API**), which adds `hw*` endpoints to the native Proxmox API (`:8006`).

![entities](https://via.placeholder.com/600x200?text=Proxmox+CPU+Dashboard+in+HA)

## What it gives you

Under a single device "Proxmox CPU (`<host>`)":

| Entity | Type | Purpose |
|---|---|---|
| CPU Temperature | sensor | Tctl °C |
| NVMe Composite Temperature | sensor | °C |
| NVMe Sensor 1 Temperature | sensor | °C |
| CPU Frequency | sensor | current MHz |
| CPU Max Frequency | sensor | scaling_max_freq MHz |
| CPU Governor | sensor | text state |
| CPU Power | sensor | W (RAPL, if available) |
| CPU Governor | select | **change** governor |
| CPU Max Frequency | number | **slider**, MHz |
| Preset Performance | button | one-tap max-perf |
| Preset Balanced | button | conservative + mid-freq |
| Preset Powersave | button | powersave + min-freq |

## Prerequisites

1. A Proxmox VE 9.x host with **proxmox-cpu-dashboard** installed (API package is enough).
   - Install API only:
     `git clone https://github.com/mrkvka/proxmox-cpu-dashboard && cd proxmox-cpu-dashboard && bash install-api.sh`
2. A Proxmox API token with permissions:
   - Read sensors/status: `Sys.Audit` on `/nodes/<node>`
   - Change CPU settings: `Sys.Modify` on `/nodes/<node>`
3. Home Assistant 2024.10+ with network access to the Proxmox host (`:8006`).

## Installation

### Via HACS (recommended)

1. HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Add `https://github.com/mrkvka/ha-proxmox-cpu-ctl`, category **Integration**
3. Search for "Proxmox CPU Dashboard" → Install
4. Restart Home Assistant

### Manually

```bash
# On the HA host (HA OS terminal / SSH)
cd /config/custom_components
git clone https://github.com/mrkvka/ha-proxmox-cpu-ctl.git proxmox_cpu_ctl_tmp
cp -r proxmox_cpu_ctl_tmp/custom_components/proxmox_cpu_ctl .
rm -rf proxmox_cpu_ctl_tmp
ha core restart
```

## Configuration

**Settings → Devices & Services → + Add Integration → Proxmox CPU Dashboard**

- **Host** — IP/hostname of Proxmox (e.g. `192.168.1.200`)
- **Port** — `8006`
- **Node** — node name in Proxmox (usually `hostname -s`, e.g. `proxmox`)
- **Token** — `PVEAPIToken=user@pam!tokenid=SECRET`
- **Verify SSL** — enable only if your Proxmox HTTPS cert is trusted by Home Assistant
- **Scan interval** — `15` seconds

A device with 12 entities appears immediately.

## Example automations

**UPS on battery → Powersave**
```yaml
alias: "UPS on battery → Powersave"
trigger:
  - platform: state
    entity_id: switch.your_smart_socket
    to: "unavailable"
    for: "00:00:30"
action:
  - service: button.press
    target:
      entity_id: button.proxmox_cpu_preset_powersave
```

**CPU too hot → throttle**
```yaml
alias: "CPU too hot"
trigger:
  - platform: numeric_state
    entity_id: sensor.proxmox_cpu_temperature
    above: 80
action:
  - service: button.press
    target:
      entity_id: button.proxmox_cpu_preset_powersave
```

**Daytime Balanced, Nighttime Powersave**
```yaml
alias: "Night Powersave"
trigger:
  - platform: time
    at: "00:00:00"
action:
  - service: button.press
    target:
      entity_id: button.proxmox_cpu_preset_powersave
```

## Troubleshooting

- **"Cannot connect"** — verify the API is running on Proxmox:
  ```bash
  pvesh get /nodes/$(hostname -s)/hwlive
  ```
- **Power sensor `Unavailable`** — your CPU doesn't expose RAPL counters. Normal on many AMD mobile chips.
- **Integration doesn't appear after install** — hard-restart HA, not just reload.

## License

MIT
