"""Sensor platform for Proxmox CPU Dashboard."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxCPUCoordinator


@dataclass(frozen=True, kw_only=True)
class ProxmoxSensorDescription(SensorEntityDescription):
    """Describes a ProxmoxCPU sensor (with an extraction callback)."""

    value_fn: Callable[[dict[str, Any]], Any] = lambda d: None


SENSORS: tuple[ProxmoxSensorDescription, ...] = (
    ProxmoxSensorDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        name="CPU Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _first(
            d,
            ("sensors", "cpu_temp"),
            ("sensors", "cpu_tctl"),
            ("temps", "cpu_tctl"),  # legacy
        ),
    ),
    ProxmoxSensorDescription(
        key="nvme_composite_temperature",
        translation_key="nvme_composite_temperature",
        name="NVMe Composite Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _first(
            d,
            ("sensors", "nvme", 0, "temp"),
            ("temps", "nvme_composite"),  # legacy
        ),
    ),
    ProxmoxSensorDescription(
        key="nvme_sensor1_temperature",
        translation_key="nvme_sensor1_temperature",
        name="NVMe Sensor 1 Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _first(
            d,
            ("sensors", "nvme", 1, "temp"),
            ("temps", "nvme_sensor1"),  # legacy
        ),
    ),
    ProxmoxSensorDescription(
        key="cpu_frequency",
        translation_key="cpu_frequency",
        name="CPU Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _mhz(_first(d, ("cpu", "cpufreq", "current_khz"), ("cpufreq", "current_khz"))),
    ),
    ProxmoxSensorDescription(
        key="cpu_max_frequency",
        translation_key="cpu_max_frequency",
        name="CPU Max Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _mhz(_first(d, ("cpu", "cpufreq", "max_khz"), ("cpufreq", "max_khz"))),
    ),
    ProxmoxSensorDescription(
        key="cpu_governor",
        translation_key="cpu_governor",
        name="CPU Governor",
        value_fn=lambda d: _first(d, ("cpu", "cpufreq", "governor"), ("cpufreq", "governor")),
    ),
    ProxmoxSensorDescription(
        key="cpu_power",
        translation_key="cpu_power",
        name="CPU Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _first(
            d,
            ("power", "package_watts"),
            ("power_w",),  # legacy :8087 API
        ),
    ),
    ProxmoxSensorDescription(
        key="system_power",
        translation_key="system_power",
        name="System Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _first(
            d,
            ("power", "system_watts"),
        ),
    ),
    ProxmoxSensorDescription(
        key="cpus_online",
        translation_key="cpus_online",
        name="Active CPUs",
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _first(d, ("cpu", "online_cpus"), ("cpus", "online")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: ProxmoxCPUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ProxmoxCPUSensor(coordinator, entry, desc) for desc in SENSORS
    )


class ProxmoxCPUSensor(CoordinatorEntity[ProxmoxCPUCoordinator], SensorEntity):
    """A single sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxmoxCPUCoordinator,
        entry: ConfigEntry,
        description: ProxmoxSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Proxmox CPU ({coordinator.host}/{coordinator.node})",
            manufacturer="Proxmox CPU Dashboard",
            model="proxmox-node-hw-api",
            configuration_url=f"https://{coordinator.host}:{coordinator.port}",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Hide sensor if no value (e.g. power_w when RAPL unavailable)."""
        val = self.native_value
        if self.entity_description.key == "cpu_power":
            return val is not None
        return super().available


def _get(data: dict[str, Any], path: tuple[Any, ...]) -> Any:
    cur: Any = data
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


def _first(data: dict[str, Any], *paths: tuple[Any, ...]) -> Any:
    for p in paths:
        val = _get(data, p)
        if val is not None:
            return val
    return None


def _mhz(khz: Any) -> Any:
    try:
        if khz is None:
            return None
        return round(float(khz) / 1000.0)
    except (TypeError, ValueError):
        return None
