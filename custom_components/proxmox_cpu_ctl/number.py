"""Number platform: CPU max frequency slider (in MHz)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfFrequency
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxCPUCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ProxmoxCPUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        MaxFrequencyNumber(coordinator, entry),
        ActiveCPUsNumber(coordinator, entry),
    ])


class MaxFrequencyNumber(CoordinatorEntity[ProxmoxCPUCoordinator], NumberEntity):
    """Slider: set scaling_max_freq on all cores. Values are in MHz."""

    _attr_has_entity_name = True
    _attr_translation_key = "cpu_max_frequency"
    _attr_name = "CPU Max Frequency"
    _attr_icon = "mdi:speedometer"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfFrequency.MEGAHERTZ
    _attr_native_step = 100

    def __init__(self, coordinator: ProxmoxCPUCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_max_freq_number"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Proxmox CPU ({coordinator.host}/{coordinator.node})",
            manufacturer="Proxmox CPU Dashboard",
            model="proxmox-node-hw-api",
        )

    @property
    def native_min_value(self) -> float:
        if self.coordinator.data is None:
            return 400.0
        khz = _first(
            self.coordinator.data,
            ("cpu", "cpufreq", "hw_min_khz"),
            ("cpufreq", "hw_min_khz"),
        ) or 400000
        return round(khz / 1000)

    @property
    def native_max_value(self) -> float:
        if self.coordinator.data is None:
            return 5000.0
        khz = _first(
            self.coordinator.data,
            ("cpu", "cpufreq", "hw_max_khz"),
            ("cpufreq", "hw_max_khz"),
        ) or 5000000
        return round(khz / 1000)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        khz = _first(
            self.coordinator.data,
            ("cpu", "cpufreq", "max_khz"),
            ("cpufreq", "max_khz"),
        ) or 0
        return round(khz / 1000) if khz else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_cpufreq(max_freq_khz=int(value) * 1000)


class ActiveCPUsNumber(CoordinatorEntity[ProxmoxCPUCoordinator], NumberEntity):
    """Slider: number of online logical CPUs.

    Offlining logical CPUs cuts power draw (each SMT thread consumes a few
    watts even idle). CPU0 is always kept online (kernel constraint).
    """

    _attr_has_entity_name = True
    _attr_translation_key = "cpus_online"
    _attr_name = "Active CPUs"
    _attr_icon = "mdi:chip"
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 1
    _attr_native_min_value = 1

    def __init__(self, coordinator: ProxmoxCPUCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_cpus_online_number"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Proxmox CPU ({coordinator.host}/{coordinator.node})",
            manufacturer="Proxmox CPU Dashboard",
            model="proxmox-node-hw-api",
        )

    @property
    def native_max_value(self) -> float:
        if self.coordinator.data is None:
            return 16.0
        total = _first(self.coordinator.data, ("cpu", "total_cpus"), ("cpus", "total")) or 16
        return float(total)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        val = _first(self.coordinator.data, ("cpu", "online_cpus"), ("cpus", "online"))
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_cpus(online=int(value))


def _get(data: dict, path: tuple) -> object | None:
    cur: object = data
    for key in path:
        if cur is None:
            return None
        if isinstance(key, int):
            if not isinstance(cur, list) or key >= len(cur):
                return None
            cur = cur[key]
        else:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
    return cur


def _first(data: dict, *paths: tuple) -> object | None:
    for p in paths:
        val = _get(data, p)
        if val is not None:
            return val
    return None
