"""
Allows to configure a switch using a 433MHz module via GPIO on a Raspberry Pi.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.rpi_rf/
"""
import logging

import voluptuous as vol

from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_SWITCHES, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['rpi-rf==0.9.6']

_LOGGER = logging.getLogger(__name__)

CONF_CODE_OFF = 'code_off'
CONF_CODE_ON = 'code_on'
CONF_GPIO = 'gpio'
CONF_PROTOCOL = 'protocol'
CONF_PULSELENGTH = 'pulselength'
CONF_SIGNAL_REPETITIONS = 'signal_repetitions'

DEFAULT_PROTOCOL = 1
DEFAULT_SIGNAL_REPETITIONS = 10

SWITCH_SCHEMA = vol.Schema({
    vol.Required(CONF_CODE_OFF):
        vol.All(cv.ensure_list_csv, [cv.positive_int]),
    vol.Required(CONF_CODE_ON):
        vol.All(cv.ensure_list_csv, [cv.positive_int]),
    vol.Optional(CONF_PULSELENGTH): cv.positive_int,
    vol.Optional(CONF_SIGNAL_REPETITIONS,
                 default=DEFAULT_SIGNAL_REPETITIONS): cv.positive_int,
    vol.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): cv.positive_int,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_GPIO): cv.positive_int,
    vol.Required(CONF_SWITCHES): vol.Schema({cv.string: SWITCH_SCHEMA}),
})

class RFDeviceWrapper:
    def __init__(self, gpio):
        import rpi_rf
        import queue
        import threading
        
        self._rfdevice = rpi_rf.RFDevice(gpio)
        self._tx_queue = queue.Queue()
        def txsender():
            while True:
                code_list, protocol, pulselength, repetitions = queue.get()
                self._rfdevice._tx_repeat = repetitions
                for code in code_list:
                    self._rfdevice.tx_code(code, protocol, pulselength)
        self._tx_sender = threading.Thread(target=txsender, daemon=True)
        self._tx_sender.start()
        
    def send_code(code_list, protocol, pulselength, repetitions):
        for i in range(0, repetitions):
            self._tx_queue.put((code_list, protocol, pulselength))
            
    def enable_tx():
        self._rfdevice.enable_tx()
        
    def cleanup():
        self._rfdevice.cleanup()

# pylint: disable=unused-argument, import-error
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Find and return switches controlled by a generic RF device via GPIO."""

    gpio = config.get(CONF_GPIO)
    rfdevice = RFDeviceWrapper(gpio)
    switches = config.get(CONF_SWITCHES)

    devices = []
    for dev_name, properties in switches.items():
        devices.append(
            RPiRFSwitch(
                hass,
                properties.get(CONF_NAME, dev_name),
                rfdevice,
                properties.get(CONF_PROTOCOL),
                properties.get(CONF_PULSELENGTH),
                properties.get(CONF_SIGNAL_REPETITIONS),
                properties.get(CONF_CODE_ON),
                properties.get(CONF_CODE_OFF)
            )
        )
    if devices:
        rfdevice.enable_tx()

    add_devices(devices)

    hass.bus.listen_once(
        EVENT_HOMEASSISTANT_STOP, lambda event: rfdevice.cleanup())


class RPiRFSwitch(SwitchDevice):
    """Representation of a GPIO RF switch."""

    def __init__(self, hass, name, rfdevice, protocol, pulselength,
                 signal_repetitions, code_on, code_off):
        """Initialize the switch."""
        self._hass = hass
        self._name = name
        self._state = False
        self._rfdevice = rfdevice
        self._protocol = protocol
        self._pulselength = pulselength
        self._code_on = code_on
        self._code_off = code_off
        self._repetitions = signal_repetitions

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def _send_code(self, code_list, protocol, pulselength):
        """Send the code(s) with a specified pulselength."""
        _LOGGER.info("Sending code(s): %s", code_list)
        self._rfdevice.send_code(code_list, protocol, pulselength)
        return True

    def turn_on(self):
        """Turn the switch on."""
        if self._send_code(self._code_on, self._protocol, self._pulselength):
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self):
        """Turn the switch off."""
        if self._send_code(self._code_off, self._protocol, self._pulselength):
            self._state = False
            self.schedule_update_ha_state()
