"""
homeassistant.components.switch.zwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Zwave platform that handles simple binary switches.
"""
# Because we do not compile openzwave on CI
# pylint: disable=import-error
import homeassistant.components.zwave as zwave

from homeassistant.components.switch import SwitchDevice
from homeassistant.components.zwave import ZWaveDeviceEntity

DOMAIN = "switch"


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Find and return demo switches. """
    if discovery_info is None:
        return

    node = zwave.NETWORK.nodes[discovery_info[zwave.ATTR_NODE_ID]]
    value = node.values[discovery_info[zwave.ATTR_VALUE_ID]]

    if value.command_class != zwave.COMMAND_CLASS_SWITCH_BINARY:
        return
    if value.type != zwave.TYPE_BOOL:
        return
    if value.genre != zwave.GENRE_USER:
        return

    value.set_change_verified(False)
    add_devices([ZwaveSwitch(value)])


class ZwaveSwitch(ZWaveDeviceEntity, SwitchDevice):
    """ Provides a zwave switch. """
    def __init__(self, value):
        from openzwave.network import ZWaveNetwork
        from pydispatch import dispatcher

        ZWaveDeviceEntity.__init__(self, value, DOMAIN)

        self._state = value.data
        dispatcher.connect(
            self._value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)

    def _value_changed(self, value):
        """ Called when a value has changed on the network. """
        if self._value.value_id == value.value_id:
            self._state = value.data
            self.update_ha_state()

    @property
    def is_on(self):
        """ True if device is on. """
        return self._state

    def turn_on(self, **kwargs):
        """ Turn the device on. """
        self._value.node.set_switch(self._value.value_id, True)

    def turn_off(self, **kwargs):
        """ Turn the device off. """
        self._value.node.set_switch(self._value.value_id, False)
