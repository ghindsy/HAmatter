"""
Support for RFXtrx binary sensors.

Lighting4 devices (sensors based on PT2262 encoder) are supported and
tested. Other types may need some work.

"""

import logging
import voluptuous as vol
from homeassistant.components import rfxtrx
from homeassistant.util import slugify
from homeassistant.util import dt as dt_util
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import event as evt
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.rfxtrx import (
    ATTR_AUTOMATIC_ADD, ATTR_NAME, ATTR_OFF_DELAY, ATTR_FIREEVENT,
    ATTR_DATABITS, CONF_DEVICES
)
from homeassistant.const import (
    CONF_SENSOR_CLASS, CONF_COMMAND_ON, CONF_COMMAND_OFF
)

DEPENDENCIES = ["rfxtrx"]

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema({
    vol.Required("platform"): rfxtrx.DOMAIN,
    vol.Optional(CONF_DEVICES, default={}): vol.All(
        dict, rfxtrx.valid_binary_sensor),
    vol.Optional(ATTR_AUTOMATIC_ADD, default=False):  cv.boolean,
}, extra=vol.ALLOW_EXTRA)


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the Binary Sensor platform to rfxtrx."""
    import RFXtrx as rfxtrxmod
    sensors = []

    for packet_id, entity in config['devices'].items():
        event = rfxtrx.get_rfx_object(packet_id)
        device_id = slugify(event.device.id_string.lower())

        if device_id in rfxtrx.RFX_DEVICES:
            continue

        if not entity[ATTR_DATABITS] is None:
            _LOGGER.info("Masked device id: %s",
                         rfxtrx.get_pt2262_deviceid(device_id, 4))

        _LOGGER.info("Add %s rfxtrx.binary_sensor (class %s)",
                     entity[ATTR_NAME], entity[CONF_SENSOR_CLASS])

        device = RfxtrxBinarySensor(event, entity[ATTR_NAME],
                                    entity[CONF_SENSOR_CLASS],
                                    entity[ATTR_FIREEVENT],
                                    entity[ATTR_OFF_DELAY],
                                    entity[ATTR_DATABITS],
                                    entity[CONF_COMMAND_ON],
                                    entity[CONF_COMMAND_OFF])

        sensors.append(device)
        rfxtrx.RFX_DEVICES[device_id] = device

    add_devices_callback(sensors)

    # pylint: disable=too-many-branches
    def binary_sensor_update(event):
        """Callback for control updates from the RFXtrx gateway."""
        if not isinstance(event, rfxtrxmod.ControlEvent):
            return

        device_id = slugify(event.device.id_string.lower())

        if device_id in rfxtrx.RFX_DEVICES:
            sensor = rfxtrx.RFX_DEVICES[device_id]
        else:
            sensor = rfxtrx.get_pt2262_device(device_id)

        if sensor is None:
            # Add the entity if not exists and automatic_add is True
            if config[ATTR_AUTOMATIC_ADD]:
                pkt_id = "".join("{0:02x}".format(x) for x in event.data)
                sensor = RfxtrxBinarySensor(event, pkt_id)
                rfxtrx.RFX_DEVICES[device_id] = sensor
                add_devices_callback([sensor])
                _LOGGER.info("Added binary sensor %s "
                             "(Device_id: %s Class: %s Sub: %s)",
                             pkt_id,
                             slugify(event.device.id_string.lower()),
                             event.device.__class__.__name__,
                             event.device.subtype)
            else:
                return
        else:
            _LOGGER.info("Binary sensor update "
                         "(Device_id: %s Class: %s Sub: %s)",
                         slugify(event.device.id_string.lower()),
                         event.device.__class__.__name__,
                         event.device.subtype)

        if sensor.is_pt2262:
            cmd = rfxtrx.get_pt2262_cmd(device_id, sensor.data_bits)
            _LOGGER.info("applying cmd %s to device_id: %s)",
                         cmd, sensor.masked_id)
            sensor.apply_cmd(int(cmd, 16))
        else:
            if not sensor.is_on or sensor.should_fire_event:
                sensor.update_state(True)

        if (sensor.is_on and sensor.off_delay is not None and
                sensor.delay_listener is None):

            def off_delay_listener(now):
                """Switch device off after a delay."""
                sensor.delay_listener = None
                sensor.update_state(False)

            sensor.delay_listener = evt.track_point_in_time(
                hass, off_delay_listener, dt_util.utcnow() + sensor.off_delay
            )

    # Subscribe to main rfxtrx events
    if binary_sensor_update not in rfxtrx.RECEIVED_EVT_SUBSCRIBERS:
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS.append(binary_sensor_update)


# pylint: disable=too-many-instance-attributes,too-many-arguments
class RfxtrxBinarySensor(BinarySensorDevice):
    """An Rfxtrx binary sensor."""

    def __init__(self, event, name, sensor_class=None,
                 should_fire=False, off_delay=None, data_bits=None,
                 cmd_on=None, cmd_off=None):
        """Initialize the sensor."""
        self.event = event
        self._name = name
        self._should_fire_event = should_fire
        self._sensor_class = sensor_class
        self._off_delay = off_delay
        self._state = False
        self.delay_listener = None
        self._data_bits = data_bits
        self._cmd_on = cmd_on
        self._cmd_off = cmd_off

        if data_bits is not None:
            self._masked_id = rfxtrx.get_pt2262_deviceid(
                event.device.id_string.lower(),
                data_bits)
        else:
            self._masked_id = None

    def __str__(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def is_pt2262(self):
        """Return true if the device is PT2262-based."""
        return self._data_bits is not None

    @property
    def masked_id(self):
        """Return the masked device id (isolated address bits)."""
        return self._masked_id

    @property
    def data_bits(self):
        """Return the number of data bits."""
        return self._data_bits

    @property
    def cmd_on(self):
        """Return the value of the 'On' command."""
        return self._cmd_on

    @property
    def cmd_off(self):
        """Return the value of the 'Off' command."""
        return self._cmd_off

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def should_fire_event(self):
        """Return is the device must fire event."""
        return self._should_fire_event

    @property
    def sensor_class(self):
        """Return the sensor class."""
        return self._sensor_class

    @property
    def off_delay(self):
        """Return the off_delay attribute value."""
        return self._off_delay

    @property
    def is_on(self):
        """Return true if the sensor state is True."""
        return self._state

    def apply_cmd(self, cmd):
        """Apply a command for updating the state."""
        if cmd == self.cmd_on:
            self.update_state(True)
        elif cmd == self.cmd_off:
            self.update_state(False)

    def update_state(self, state):
        """Update the state of the device."""
        self._state = state
        self.update_ha_state()
