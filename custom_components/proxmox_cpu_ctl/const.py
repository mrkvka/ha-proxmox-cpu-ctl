"""Constants for proxmox_cpu_ctl."""
from __future__ import annotations

DOMAIN = "proxmox_cpu_ctl"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8087
DEFAULT_SCAN_INTERVAL = 15  # seconds

PLATFORMS = ["sensor", "select", "number", "button"]

# Preset profiles: name -> {governor, max_freq_khz, optional cpus}
# If `cpus` is present, the preset also brings only that many cores online.
PRESETS = {
    "performance": {"governor": "performance", "max_freq": 2900000, "cpus": 16},
    "balanced": {"governor": "conservative", "max_freq": 1700000, "cpus": 16},
    "powersave": {"governor": "powersave", "max_freq": 1400000, "cpus": 16},
    "ups": {"governor": "powersave", "max_freq": 1400000, "cpus": 4},
}
