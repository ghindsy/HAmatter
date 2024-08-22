"""The TP-Link Omada integration."""

from __future__ import annotations

from tplink_omada_client import OmadaSite
from tplink_omada_client.exceptions import (
    ConnectionFailed,
    LoginFailed,
    OmadaClientException,
    UnsupportedControllerVersion,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry

from .config_flow import CONF_SITE, create_omada_client
from .const import DOMAIN
from .controller import OmadaSiteController

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SWITCH,
    Platform.UPDATE,
]

type OmadaConfigEntry = ConfigEntry[OmadaSiteController]


async def async_setup_entry(hass: HomeAssistant, entry: OmadaConfigEntry) -> bool:
    """Set up TP-Link Omada from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    try:
        client = await create_omada_client(hass, entry.data)
        await client.login()

    except (LoginFailed, UnsupportedControllerVersion) as ex:
        raise ConfigEntryAuthFailed(
            f"Omada controller refused login attempt: {ex}"
        ) from ex
    except ConnectionFailed as ex:
        raise ConfigEntryNotReady(
            f"Omada controller could not be reached: {ex}"
        ) from ex

    except OmadaClientException as ex:
        raise ConfigEntryNotReady(
            f"Unexpected error connecting to Omada controller: {ex}"
        ) from ex

    site_client = await client.get_site_client(OmadaSite("", entry.data[CONF_SITE]))
    entry.runtime_data = controller = OmadaSiteController(hass, site_client)
    gateway_coordinator = await controller.get_gateway_coordinator()
    if gateway_coordinator:
        await gateway_coordinator.async_config_entry_first_refresh()
    await controller.get_clients_coordinator().async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OmadaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: OmadaConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    controller = config_entry.runtime_data

    devices = await controller.omada_client.get_devices()

    # Allow removal if the device is not present in the controller
    return not any(
        mac for _, mac in device_entry.identifiers if mac in (d.mac for d in devices)
    )
