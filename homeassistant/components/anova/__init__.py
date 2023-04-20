"""The Anova integration."""
from __future__ import annotations

from anova_wifi import (
    AnovaApi,
    AnovaPrecisionCooker,
    AnovaPrecisionCookerSensor,
    InvalidLogin,
    NoDevicesFound,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN
from .coordinator import AnovaCoordinator
from .models import AnovaData

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Anova from a config entry."""
    api = AnovaApi(
        aiohttp_client.async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    try:
        await api.authenticate()
        online_devices = await api.get_devices()
    except InvalidLogin as err:
        raise ConfigEntryNotReady("Login was incorrect, please try again") from err
    except NoDevicesFound:
        # get_devices raises an exception if no devices are online
        online_devices = []
    assert api.jwt
    cached_devices = [
        AnovaPrecisionCooker(
            aiohttp_client.async_get_clientsession(hass),
            device[0],
            device[1],
            api.jwt,
        )
        for device in entry.data["devices"]
    ]
    existing_device_keys = [device[0] for device in entry.data["devices"]]
    new_devices = [
        device
        for device in online_devices
        if device.device_key not in existing_device_keys
    ]
    devices = cached_devices + new_devices
    if new_devices:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                **{"devices": [(device.device_key, device.type) for device in devices]},
            },
        )
    coordinators = [AnovaCoordinator(hass, device) for device in devices]
    for coordinator in coordinators:
        await coordinator.async_config_entry_first_refresh()
        firmware_version = coordinator.data["sensors"][
            AnovaPrecisionCookerSensor.FIRMWARE_VERSION
        ]
        coordinator.async_setup(str(firmware_version))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = AnovaData(
        api_jwt=api.jwt, precision_cookers=devices, coordinators=coordinators
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
