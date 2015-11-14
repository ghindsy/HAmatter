"""
homeassistant.components.switch.s20
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Orvibo S20 Wifi Smart Switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.s20/
"""
import logging

from homeassistant.components.switch import SwitchDevice

from orvibo.s20 import S20, S20Exception

DEFAULT_NAME = "Orvibo S20 Switch"
REQUIREMENTS = ['orvibo==1.0.0']
_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """ Find and return S20 switches. """
    if config.get('host') is None:
        _LOGGER.error("Missing required variable: host")
        return
    try:
        s20 = S20(config.get('host'))
        add_devices_callback([S20Switch(config.get('name', DEFAULT_NAME),
                                        s20)])
    except S20Exception as exception:
        _LOGGER.error(exception)


class S20Switch(SwitchDevice):
    """ Represents an S20 switch. """
    def __init__(self, name, s20):
        self._name = name
        self._s20 = s20

    @property
    def should_poll(self):
        """ No polling needed. """
        return False

    @property
    def name(self):
        """ The name of the switch. """
        return self._name

    @property
    def is_on(self):
        """ True if device is on. """
        try:
            return self._s20.on
        except S20Exception as exception:
            _LOGGER.error(exception)
            return False

    def turn_on(self, **kwargs):
        """ Turn the device on. """
        try:
            self._s20.on = True
        except S20Exception as exception:
            _LOGGER.error(exception)
        self.update_ha_state()

    def turn_off(self, **kwargs):
        """ Turn the device off. """
        try:
            self._s20.on = False
        except S20Exception as exception:
            _LOGGER.error(exception)
        self.update_ha_state()
