# custom_components/checkpoint_gaia/coordinator.py
# Version 1.3.1 – Fixed CPU/Memory 404 errors (now uses reliable run-script)

import aiohttp
import re
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_VERIFY_SSL, CONF_API_VERSION, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class GaiaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        super().__init__(
            hass,
            logger=_LOGGER,                    # Fixed logger (required by HA 2024.10+)
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.host = entry.data[CONF_HOST]
        self.port = entry.data.get(CONF_PORT, 443)
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        self.verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)
        self.api_version = entry.data.get(CONF_API_VERSION, "v1.8")
        self.sid = None
        self.base_url = f"https://{self.host}:{self.port}/gaia_api"

    async def _async_update_data(self):
        if not self.sid:
            await self._login()

        try:
            data = {}

            # === Serial Number (direct endpoint – works on all versions) ===
            asset = await self._api_post(f"/{self.api_version}/show-asset")
            data["serial_number"] = asset.get("serial-number") or asset.get("serial_number", "Unknown")

            # === CPU Usage – FIXED: now uses run-script (no more 404) ===
            cpu_raw = await self._run_script("show cpu usage")
            output = cpu_raw.get("output", "").strip()
            percentages = re.findall(r"(\d+)%", output)
            if percentages:
                data["cpu_usage"] = round(sum(float(p) for p in percentages) / len(percentages), 1)
            else:
                data["cpu_usage"] = 0.0

            # === Memory Usage – FIXED: now uses run-script ===
            mem_raw = await self._run_script("show memory usage")
            output = mem_raw.get("output", "").strip()
            match = re.search(r"(\d+)%", output)
            data["memory_usage"] = float(match.group(1)) if match else 0.0

            # === Number of Routes ===
            routes = await self._api_post(f"/{self.api_version}/show-routes")
            data["routes_count"] = len(routes.get("routes", routes.get("static-routes", [])))

            # === Interfaces ===
            ifaces = await self._api_post(f"/{self.api_version}/show-interfaces")
            data["interfaces"] = ifaces.get("interfaces", ifaces.get("physical-interfaces", []))

            # === Active Sessions ===
            sessions_raw = await self._run_script("cpstat fw -f connections | grep '^connections' | awk '{print $2}'")
            data["sessions"] = int(sessions_raw.get("output", "0").strip() or 0)

            # === Version ===
            ver = await self._api_post(f"/{self.api_version}/show-version")
            data["version"] = f"{ver.get('product-version', 'Unknown')} (Build {ver.get('os-build', '')})"

            # === Uptime ===
            uptime_raw = await self._run_script("show uptime")
            data["uptime"] = uptime_raw.get("output", "Unknown").strip()

            # === Content Updates Package ===
            content_raw = await self._run_script(
                "cpinfo -y all | grep -E 'IPS|Threat|Anti|Content|Jumbo' | head -5"
            )
            data["content_package"] = content_raw.get("output", "N/A").strip() or "N/A"

            # === Throughput (Mbps) + Sessions per second ===
            perf_raw = await self._run_script("cpstat fw -f perf")
            output = perf_raw.get("output", "")

            match_throughput = re.search(r"bytes per second.*?(\d+).*?(\d+)", output, re.IGNORECASE | re.DOTALL)
            if match_throughput:
                total_bytes = int(match_throughput.group(1)) + int(match_throughput.group(2))
                data["throughput_mbps"] = round(total_bytes / 1_000_000, 2)
            else:
                data["throughput_mbps"] = 0.0

            match_sps = re.search(r"new conns? per sec.*?(\d+)", output, re.IGNORECASE)
            data["sessions_per_second"] = int(match_sps.group(1)) if match_sps else 0

            # === VPN Status ===
            vpn_raw = await self._run_script("cpstat vpn -f all")
            vpn_out = vpn_raw.get("output", "").lower()
            data["vpn_status"] = "Up" if "up" in vpn_out or "active" in vpn_out else "Down"

            return data

        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                self.sid = None
                raise ConfigEntryAuthFailed("GAIA session expired") from err
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error in Gaia update")
            raise UpdateFailed(f"Update failed: {err}") from err

    async def _login(self):
        url = f"{self.base_url}/login"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"user": self.username, "password": self.password},
                ssl=self.verify_ssl
            ) as resp:
                resp.raise_for_status()
                self.sid = (await resp.json()).get("sid")

    async def _api_post(self, endpoint, payload=None):
        if payload is None:
            payload = {}
        url = f"{self.base_url}{endpoint}"
        headers = {"X-chkp-sid": self.sid, "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, ssl=self.verify_ssl
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _run_script(self, command: str):
        return await self._api_post(
            f"/{self.api_version}/run-script",
            {"command": command}
        )
