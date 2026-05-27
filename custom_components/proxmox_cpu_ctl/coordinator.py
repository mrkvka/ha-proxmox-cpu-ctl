"""DataUpdateCoordinator for Proxmox CPU Dashboard."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ProxmoxCPUCoordinator(DataUpdateCoordinator):
    """Polls Proxmox Node Hardware API and sends control commands."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        node: str,
        token: str,
        verify_ssl: bool,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.node = node
        self._token = token
        self._verify_ssl = verify_ssl
        self._base = f"https://{host}:{port}"
        self._session: aiohttp.ClientSession = async_get_clientsession(hass)

    @property
    def base_url(self) -> str:
        """Return the base URL of the API."""
        return self._base

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": self._token}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from /nodes/{node}/hwlive."""
        try:
            async with self._session.get(
                f"{self._base}/api2/json/nodes/{self.node}/hwlive",
                headers=self._auth_headers(),
                ssl=self._verify_ssl,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise UpdateFailed(f"HTTP {resp.status} from /hwlive: {body}")
                payload = await resp.json()
                return payload.get("data") or {}
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot reach {self._base}: {err}") from err

    async def async_health(self) -> bool:
        """Return True if the API responds to /hwlive."""
        try:
            async with self._session.get(
                f"{self._base}/api2/json/nodes/{self.node}/hwlive",
                headers=self._auth_headers(),
                ssl=self._verify_ssl,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001
            return False

    async def _post(self, endpoint: str, data: dict[str, str]) -> None:
        url = f"{self._base}/api2/json/nodes/{self.node}/{endpoint.lstrip('/')}"
        async with self._session.post(
            url,
            headers=self._auth_headers(),
            data=data,
            ssl=self._verify_ssl,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise UpdateFailed(f"POST {endpoint} failed ({resp.status}): {body}")

    async def async_set_cpufreq(
        self,
        governor: str | None = None,
        max_freq_khz: int | None = None,
    ) -> None:
        """Send POST /hwcpufreq and trigger refresh."""
        form: dict[str, str] = {}
        if governor:
            form["governor"] = governor
        if max_freq_khz is not None:
            form["max_freq"] = str(int(max_freq_khz))
        if not form:
            return
        await self._post("/hwcpufreq", form)
        await self.async_request_refresh()

    async def async_set_cpus(self, online: int) -> None:
        """Send POST /hwcpus — change the number of online logical CPUs."""
        if online < 1:
            return
        await self._post("/hwcpus", {"online_cpus": str(int(online))})
        await self.async_request_refresh()

    async def async_apply_profile(self, profile: str) -> None:
        """Send POST /hwapply with a named profile."""
        if not profile:
            return
        await self._post("/hwapply", {"profile": profile})
        await self.async_request_refresh()
