from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import GaiaCoordinator

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback):
    coordinator: GaiaCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GaiaSensor(coordinator, "cpu_usage", "CPU Usage", PERCENTAGE, SensorDeviceClass.PERCENTAGE, "mdi:cpu-64-bit"),
        GaiaSensor(coordinator, "memory_usage", "Memory Usage", PERCENTAGE, SensorDeviceClass.PERCENTAGE, "mdi:memory"),
        GaiaSensor(coordinator, "sessions", "Active Sessions", None, None, "mdi:account-multiple"),
        GaiaSensor(coordinator, "routes_count", "Number of Routes", None, SensorStateClass.MEASUREMENT, "mdi:router-network"),
        GaiaSensor(coordinator, "throughput_mbps", "Total Current Throughput", "Mbps", SensorDeviceClass.DATA_RATE, "mdi:download-network"),
        GaiaSensor(coordinator, "sessions_per_second", "Sessions Per Second", "conn/s", None, "mdi:connection"),
        GaiaTextSensor(coordinator, "serial_number", "Serial Number", "mdi:identifier"),
        GaiaTextSensor(coordinator, "version", "Version", "mdi:information"),
        GaiaTextSensor(coordinator, "uptime", "Uptime", "mdi:clock-time-eight-outline"),
        GaiaTextSensor(coordinator, "vpn_status", "VPN Status", "mdi:shield-lock"),
        GaiaTextSensor(coordinator, "content_package", "Content Updates Package", "mdi:package-variant"),
        GaiaInterfacesSensor(coordinator),
    ]
    async_add_entities(entities)


class GaiaSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key: str, name: str, unit: str | None, device_class: str | None, icon: str):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Gaia {name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_state_class = SensorStateClass.MEASUREMENT if (unit or device_class) else None

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class GaiaTextSensor(GaiaSensor):
    def __init__(self, coordinator, key: str, name: str, icon: str):
        super().__init__(coordinator, key, name, None, None, icon)
        self._attr_state_class = None


class GaiaInterfacesSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Gaia Interfaces"
    _attr_icon = "mdi:ethernet"
    _attr_unique_id = "gaia_interfaces"

    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def native_value(self):
        return len(self.coordinator.data.get("interfaces", []))

    @property
    def extra_state_attributes(self):
        ifaces = self.coordinator.data.get("interfaces", [])
        return {
            iface.get("name", "unknown"): {
                "status": iface.get("state", "down"),
                "link": iface.get("link-state", "down"),
                "ip": iface.get("ipv4-address", ""),
            }
            for iface in ifaces
        }
