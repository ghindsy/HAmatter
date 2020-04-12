"""The Wolf SmartSet Service integration."""
from _datetime import timedelta
import logging

from wolf_smartset.token_auth import InvalidAuth
from wolf_smartset.wolf_client import WolfClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Wolf SmartSet Service component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Wolf SmartSet Service from a config entry."""
    username = entry.data["username"]
    password = entry.data["password"]
    device_name = entry.data["device_name"]
    _LOGGER.debug("Setting up wolflink integration for device: %s", device_name)
    hub = WolfClient(username, password)

    try:
        systems = await hub.fetch_system_list()
    except InvalidAuth:
        _LOGGER.error("Could not set up wolflink integration due to wrong credentials")
        return False

    filtered_systems = [device for device in systems if device.name == device_name]
    gateway_id = filtered_systems[0].gateway
    device_id = filtered_systems[0].id
    parameters = await fetch_parameters(hub, gateway_id, device_id)

    async def async_update_data():
        """Update all stored entities for Wolf SmartSet."""
        try:
            values = await hub.fetch_value(gateway_id, device_id, parameters)
            return {v.value_id: v.value for v in values}
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="wolflink",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["parameters"] = parameters
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def fetch_parameters(client: WolfClient, gateway_id: int, device_id: int):
    """
    Fetch all available parameters with usage of WolfClient.

    By default Reglertyp entity is removed because API will not provide value for this parameter.
    """
    fetched_parameters = await client.fetch_parameters(gateway_id, device_id)
    return [param for param in fetched_parameters if param.name != "Reglertyp"]
