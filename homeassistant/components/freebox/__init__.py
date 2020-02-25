"""Support for Freebox devices (Freebox v6 and Freebox mini 4K)."""
import asyncio
import logging

from aiofreepybox.exceptions import HttpRequestError
import voluptuous as vol

from homeassistant.components.discovery import SERVICE_FREEBOX
from homeassistant.config_entries import SOURCE_DISCOVERY, SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.typing import HomeAssistantType

from .const import DOMAIN, PLATFORMS
from .router import FreeboxRouter

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Required(CONF_HOST): cv.string, vol.Required(CONF_PORT): cv.port}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the Freebox component from legacy config file."""
    conf = config.get(DOMAIN)

    async def discovery_dispatch(service, discovery_info):
        if conf is None:
            host = discovery_info.get("properties", {}).get("api_domain")
            port = discovery_info.get("properties", {}).get("https_port")
            _LOGGER.info("Discovered Freebox server: %s:%s", host, port)
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_DISCOVERY},
                    data={CONF_HOST: host, CONF_PORT: port},
                )
            )

    discovery.async_listen(hass, SERVICE_FREEBOX, discovery_dispatch)

    if conf is None:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf,
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up Freebox component."""
    router = FreeboxRouter(hass, entry)

    try:
        await router.setup()
    except HttpRequestError:
        _LOGGER.exception("Failed to connect to Freebox")
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = router

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    # Services
    async def async_reboot(call):
        """Handle reboot service call."""
        await router.reboot()

    hass.services.async_register(DOMAIN, "reboot", async_reboot)

    async def async_close_connection(event):
        """Close Freebox connection on HA Stop."""
        await router.close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_connection)

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        router = hass.data[DOMAIN][entry.unique_id]
        await router.close()
        hass.data.pop(DOMAIN)

    return unload_ok
