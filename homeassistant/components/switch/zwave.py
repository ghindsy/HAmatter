"""
Z-Wave platform that handles simple binary switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.zwave/
"""
import asyncio
import logging
# Because we do not compile openzwave on CI
# pylint: disable=import-error
from homeassistant.components.switch import DOMAIN, SwitchDevice
from homeassistant.components import zwave

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
def get_device(node, value, **kwargs):
    """Create zwave entity device."""
    if not node.has_command_class(zwave.const.COMMAND_CLASS_SWITCH_BINARY):
        return None
    if value.type != zwave.const.TYPE_BOOL or value.genre != \
            zwave.const.GENRE_USER:
        return None
    value.set_change_verified(False)
    return ZwaveSwitch(value)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Create zwave entity device."""
    return zwave.async_setup_platform(hass, async_add_devices, discovery_info)


class ZwaveSwitch(zwave.ZWaveDeviceEntity, SwitchDevice):
    """Representation of a Z-Wave switch."""

    def __init__(self, value):
        """Initialize the Z-Wave switch device."""
        zwave.ZWaveDeviceEntity.__init__(self, value, DOMAIN)
        self.update_properties()

    def update_properties(self):
        """Callback on data changes for node values."""
        self._state = self._value.data

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._value.node.set_switch(self._value.value_id, True)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._value.node.set_switch(self._value.value_id, False)
