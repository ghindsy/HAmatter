"""
Support for Rflink switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.rflink/
"""
import asyncio
import logging

from homeassistant.components.rflink import (
    CONF_ALIASES, CONF_DEVICE_DEFAULTS, CONF_DEVICES, CONF_FIRE_EVENT,
    CONF_GROUP, CONF_GROUP_ALIASES, CONF_NOGROUP_ALIASES,
    CONF_SIGNAL_REPETITIONS, DATA_ENTITY_GROUP_LOOKUP, DATA_ENTITY_LOOKUP,
    DEVICE_DEFAULTS_SCHEMA, DOMAIN, EVENT_KEY_COMMAND,
    cv, vol, RflinkCommand)
from homeassistant.components.cover import CoverDevice
from homeassistant.const import CONF_NAME, CONF_PLATFORM

DEPENDENCIES = ['rflink']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): DOMAIN,
    vol.Optional(CONF_DEVICE_DEFAULTS, default=DEVICE_DEFAULTS_SCHEMA({})):
        DEVICE_DEFAULTS_SCHEMA,
    vol.Optional(CONF_DEVICES, default={}): vol.Schema({
        cv.string: {
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_ALIASES, default=[]):
                vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(CONF_GROUP_ALIASES, default=[]):
                vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(CONF_NOGROUP_ALIASES, default=[]):
                vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(CONF_FIRE_EVENT, default=False): cv.boolean,
            vol.Optional(CONF_SIGNAL_REPETITIONS): vol.Coerce(int),
            vol.Optional(CONF_GROUP, default=True): cv.boolean,
        },
    }),
})


def devices_from_config(domain_config, hass=None):
    """Parse configuration and add Rflink switch devices."""
    devices = []
    for device_id, config in domain_config[CONF_DEVICES].items():
        device_config = dict(domain_config[CONF_DEVICE_DEFAULTS], **config)
        device = RflinkCover(device_id, hass, **device_config)
        devices.append(device)

        # Register entity (and aliases) to listen to incoming rflink events
        # Device id and normal aliases respond to normal and group command
        hass.data[DATA_ENTITY_LOOKUP][
            EVENT_KEY_COMMAND][device_id].append(device)
        if config[CONF_GROUP]:
            hass.data[DATA_ENTITY_GROUP_LOOKUP][
                EVENT_KEY_COMMAND][device_id].append(device)
        for _id in config[CONF_ALIASES]:
            hass.data[DATA_ENTITY_LOOKUP][
                EVENT_KEY_COMMAND][_id].append(device)
            hass.data[DATA_ENTITY_GROUP_LOOKUP][
                EVENT_KEY_COMMAND][_id].append(device)
        # group_aliases only respond to group commands
        for _id in config[CONF_GROUP_ALIASES]:
            hass.data[DATA_ENTITY_GROUP_LOOKUP][
                EVENT_KEY_COMMAND][_id].append(device)
        # nogroup_aliases only respond to normal commands
        for _id in config[CONF_NOGROUP_ALIASES]:
            hass.data[DATA_ENTITY_LOOKUP][
                EVENT_KEY_COMMAND][_id].append(device)

    return devices


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Rflink platform."""
    async_add_devices(devices_from_config(config, hass))


class RflinkCover(RflinkCommand, CoverDevice):
    """Representation of a Rflink cover."""

    def _handle_event(self, event):
        """Adjust state if Rflink picks up a remote command for this device."""
        self.cancel_queued_send_commands()

        command = event['command']
        if command in ['on', 'allon']:
            self._state = True
        elif command in ['off', 'alloff']:
            self._state = False

    @property
    def should_poll(self):
        """No polling available in RFXtrx cover."""
        return False

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return None

    def async_close_cover(self, **kwargs):
        """Close the cover."""
        return self._async_handle_command("turn_on")

    def async_open_cover(self, **kwargs):
        """Open the cover."""
        return self._async_handle_command("turn_off")

    def async_stop_cover(self, **kwargs):
        """Stop the cover movement."""
        return self._async_handle_command("stop_roll")
