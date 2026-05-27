"""Constants for proxmox_cpu_ctl."""
from __future__ import annotations

DOMAIN = "proxmox_cpu_ctl"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NODE = "node"
CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8006
DEFAULT_SCAN_INTERVAL = 15  # seconds

PLATFORMS = ["sensor", "select", "number", "button"]

# Preset profiles supported by proxmox-cpu-dashboard (proxmox-node-hw-api).
# If `cpus` is present, the preset also adjusts online CPUs first.
PRESETS = {
    "performance": {"profile": "performance"},
    "balanced": {"profile": "balanced"},
    "powersave": {"profile": "powersave"},
    # Not a native profile; keep as a practical "survival" shortcut.
    "ups": {"profile": "powersave", "cpus": 4},
}
