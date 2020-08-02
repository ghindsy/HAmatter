"""Support for Blink Home Camera System."""
import asyncio
from copy import deepcopy
import logging

from blinkpy.auth import Auth
from blinkpy.blinkpy import Blink
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.components.blink.const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_REFRESH,
    SERVICE_SAVE_VIDEO,
    SERVICE_SEND_PIN,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_FILENAME, CONF_NAME, CONF_PIN, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

SERVICE_SAVE_VIDEO_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME): cv.string, vol.Required(CONF_FILENAME): cv.string}
)
SERVICE_SEND_PIN_SCHEMA = vol.Schema({vol.Optional(CONF_PIN): cv.string})


def _blink_startup_wrapper(entry):
    """Startup wrapper for blink."""
    blink = Blink()
    blink.auth = Auth(deepcopy(dict(entry.data)), no_prompt=True)
    blink.refresh_rate = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    if blink.start():
        blink.setup_post_verify()
    return blink


async def async_setup(hass, config):
    """Set up a Blink component."""
    hass.data[DOMAIN] = {}
    return True


async def async_migrate_entry(hass, entry):
    """Handle migration of a previous version config entry."""
    data = {**entry.data}
    if entry.version == 1:
        data.pop("login_response", None)
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=data
            )
        )
        persistent_notification.async_create(
            hass,
            "Blink configuration migrated to a new version. Please go to the integrations page to re-configure (such as sending a new 2FA key).",
            "Blink Migration",
        )
        return False
    return True


async def async_setup_entry(hass, entry):
    """Set up Blink via config entry."""
    _async_import_options_from_data_if_missing(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = await hass.async_add_executor_job(
        _blink_startup_wrapper, entry
    )

    if not hass.data[DOMAIN][entry.entry_id].available:
        _LOGGER.error("Blink unavailable for setup")
        return False

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    def blink_refresh(event_time=None):
        """Call blink to refresh info."""
        hass.data[DOMAIN][entry.entry_id].refresh(force_cache=True)

    async def async_save_video(call):
        """Call save video service handler."""
        await async_handle_save_video_service(hass, entry, call)

    def send_pin(call):
        """Call blink to send new pin."""
        pin = call.data[CONF_PIN]
        hass.data[DOMAIN][entry.entry_id].auth.send_auth_key(
            hass.data[DOMAIN][entry.entry_id], pin,
        )

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, blink_refresh)
    hass.services.async_register(
        DOMAIN, SERVICE_SAVE_VIDEO, async_save_video, schema=SERVICE_SAVE_VIDEO_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_PIN, send_pin, schema=SERVICE_SEND_PIN_SCHEMA
    )

    return True


@callback
def _async_import_options_from_data_if_missing(hass, entry):
    options = dict(entry.options)
    if CONF_SCAN_INTERVAL not in entry.options:
        options[CONF_SCAN_INTERVAL] = entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        hass.config_entries.async_update_entry(entry, options=options)


async def async_unload_entry(hass, entry):
    """Unload Blink entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.entry_id)

    if len(hass.data[DOMAIN]) != 0:
        return True

    hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    hass.services.async_remove(DOMAIN, SERVICE_SAVE_VIDEO_SCHEMA)
    hass.services.async_remove(DOMAIN, SERVICE_SEND_PIN)

    return True


async def async_handle_save_video_service(hass, entry, call):
    """Handle save video service calls."""
    camera_name = call.data[CONF_NAME]
    video_path = call.data[CONF_FILENAME]
    if not hass.config.is_allowed_path(video_path):
        _LOGGER.error("Can't write %s, no access to path!", video_path)
        return

    def _write_video(camera_name, video_path):
        """Call video write."""
        all_cameras = hass.data[DOMAIN][entry.entry_id].cameras
        if camera_name in all_cameras:
            all_cameras[camera_name].video_to_file(video_path)

    try:
        await hass.async_add_executor_job(_write_video, camera_name, video_path)
    except OSError as err:
        _LOGGER.error("Can't write image to file: %s", err)
