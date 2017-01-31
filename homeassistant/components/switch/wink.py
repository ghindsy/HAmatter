"""
Support for Wink switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.wink/
"""

from homeassistant.components.wink import WinkDevice, DOMAIN
from homeassistant.helpers.entity import ToggleEntity

DEPENDENCIES = ['wink']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Wink platform."""
    import pywink

    for switch in pywink.get_switches():
        if switch.object_id() + switch.name() not in hass.data[DOMAIN]['unique_ids']:
            add_devices([WinkToggleDevice(switch, hass)])
    for switch in pywink.get_powerstrips():
        if switch.object_id() + switch.name() not in hass.data[DOMAIN]['unique_ids']:
            add_devices([WinkToggleDevice(switch, hass)])
    for switch in pywink.get_sirens():
        if switch.object_id() + switch.name() not in hass.data[DOMAIN]['unique_ids']:
            add_devices([WinkToggleDevice(switch, hass)])
    for sprinkler in pywink.get_sprinklers():
        if sprinkler.object_id() + sprinkler.name() not in hass.data[DOMAIN]['unique_ids']:
            add_devices([WinkToggleDevice(sprinkler, hass)])


class WinkToggleDevice(WinkDevice, ToggleEntity):
    """Representation of a Wink toggle device."""

    def __init__(self, wink, hass):
        """Initialize the Wink device."""
        super().__init__(wink, hass)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.wink.state()

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self.wink.set_state(True)

    def turn_off(self):
        """Turn the device off."""
        self.wink.set_state(False)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        try:
            event = self.wink.last_event()
        except AttributeError:
            event = None
        return {
            'last_event': event
        }
