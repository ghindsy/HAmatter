"""
Support for Freebox devices (Freebox v6 and Freebox mini 4K).

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.freebox/
"""
import logging

from homeassistant.components.freebox import DATA_FREEBOX
from homeassistant.components.switch import SwitchDevice

DEPENDENCIES = ['freebox']

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """Set up the switch."""
    fbx = hass.data[DATA_FREEBOX]
    async_add_entities([FbxWifiSwitch(fbx)], True)


class FbxWifiSwitch(SwitchDevice):
    """Representation of a freebox wifi switch."""

    def __init__(self, fbx):
        """Initilize the Wifi switch."""
        self._name = 'Freebox WiFi'
        self._state = None
        self._fbx = fbx

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    async def _async_set_state(self, enabled):
        """Turn the switch on or off."""
        from aiofreepybox.exceptions import InsufficientPermissionsError

        wifi_config = {"enabled": enabled}
        try:
            await self._fbx.wifi.set_global_config(wifi_config)
        except InsufficientPermissionsError:
            _LOGGER.warning('Home Assistant does not have permissions to'
                            ' modify the Freebox settings. Please refer'
                            ' to documentation. https://home-assistant.'
                            '.io/components/switch.freebox/')

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._async_set_state(False)

    async def async_update(self):
        """Get the state and update it."""
        datas = await self._fbx.wifi.get_global_config()
        active = datas['enabled']
        self._state = bool(active)
