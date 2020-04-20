"""
Support for controlling GPIO pins of a Numato Labs USB GPIO expander.

For more details about this component, please refer to the documentation at
https://home-assistant.io/integrations/numato
"""
# pylint: disable=import-error
import logging

import numato_gpio as gpio
import voluptuous as vol

# pylint: disable=no-member
from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_ID,
    CONF_NAME,
    CONF_SENSORS,
    CONF_SWITCHES,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "numato"

CONF_INVERT_LOGIC = "invert_logic"
CONF_DISCOVER = "discover"
CONF_DEVICES = "devices"
CONF_DEVICE_ID = "id"
CONF_PORTS = "ports"
CONF_SRC_RANGE = "source_range"
CONF_DST_RANGE = "destination_range"
CONF_DST_UNIT = "unit"
DEFAULT_INVERT_LOGIC = False
DEFAULT_SRC_RANGE = [0, 1024]
DEFAULT_DST_RANGE = [0.0, 100.0]
DEFAULT_UNIT = "%"
DEFAULT_DEV = [f"/dev/ttyACM{i}" for i in range(10)]

PORT_RANGE = range(1, 8)  # ports 0-7 are ADC capable


def int_range(rng):
    """Validate the input array to describe a range by two integers."""
    if not (isinstance(rng[0], int) and isinstance(rng[1], int)):
        raise vol.Invalid(f"Only integers are allowed: {rng}")
    if len(rng) != 2:
        raise vol.Invalid(f"Only two numbers allowed in a range: {rng}")
    if rng[0] > rng[1]:
        raise vol.Invalid(f"Lower range bound must come first: {rng}")
    return rng


def float_range(rng):
    """Validate the input array to describe a range by two floats."""
    try:
        coe = vol.Coerce(float)
        coe(rng[0])
        coe(rng[1])
    except vol.CoerceInvalid:
        raise vol.Invalid(f"Only int or float values are allowed: {rng}")
    if len(rng) != 2:
        raise vol.Invalid(f"Only two numbers allowed in a range: {rng}")
    if rng[0] > rng[1]:
        raise vol.Invalid(f"Lower range bound must come first: {rng}")
    return rng


def adc_port_number(num):
    """Validate input number to be in the range of ADC enabled ports."""
    try:
        num = int(num)
    except (ValueError):
        raise vol.Invalid(f"Port numbers must be integers: {num}")
    if num not in range(1, 8):
        raise vol.Invalid(f"Only port numbers from 1 to 7 are ADC capable: {num}")
    return num


ADC_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_SRC_RANGE, default=DEFAULT_SRC_RANGE): int_range,
        vol.Optional(CONF_DST_RANGE, default=DEFAULT_DST_RANGE): float_range,
        vol.Optional(CONF_DST_UNIT, default=DEFAULT_UNIT): cv.string,
    }
)

PORTS_SCHEMA = vol.Schema({cv.positive_int: cv.string})

IO_PORTS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORTS): PORTS_SCHEMA,
        vol.Optional(CONF_INVERT_LOGIC, default=DEFAULT_INVERT_LOGIC): cv.boolean,
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): cv.positive_int,
        CONF_BINARY_SENSORS: IO_PORTS_SCHEMA,
        CONF_SWITCHES: IO_PORTS_SCHEMA,
        CONF_SENSORS: {CONF_PORTS: {adc_port_number: ADC_SCHEMA}},
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            CONF_DEVICES: vol.All(cv.ensure_list, [DEVICE_SCHEMA]),
            vol.Optional(CONF_DISCOVER, default=DEFAULT_DEV): vol.All(
                cv.ensure_list, [cv.string]
            ),
        },
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Initialize the integration by discovering available Numato devices."""
    hass.data[DOMAIN] = config[DOMAIN][CONF_DEVICES]

    gpio.discover(config[DOMAIN][CONF_DISCOVER])

    _LOGGER.info(
        "Initializing Numato 32 port USB GPIO expanders with IDs: %s",
        ", ".join(str(d) for d in gpio.devices),
    )

    def cleanup_gpio(event):
        """Stuff to do before stopping."""
        _LOGGER.debug("Clean up Numato GPIO")
        gpio.cleanup()
        PORTS_IN_USE.clear()

    def prepare_gpio(event):
        """Stuff to do when home assistant starts."""
        _LOGGER.debug("Setup cleanup at stop for Numato GPIO")
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, cleanup_gpio)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, prepare_gpio)

    return True


PORTS_IN_USE = dict()


def check_port_free(device_id, port, direction):
    """Check whether a port is still free set up.

    Fail with exception if it has already been registered.
    """
    if (device_id, port) not in PORTS_IN_USE:
        PORTS_IN_USE[(device_id, port)] = direction
    else:
        raise gpio.NumatoGpioError(
            "Device {} Port {} already in use as {}.".format(
                device_id,
                port,
                "input" if PORTS_IN_USE[(device_id, port)] == gpio.IN else "output",
            )
        )


def check_device_id(device_id):
    """Check whether a device has been discovered.

    Fail with exception.
    """
    if device_id not in gpio.devices:
        raise gpio.NumatoGpioError(f"Device {device_id} not available.")


def setup_output(device_id, port):
    """Set up a GPIO as output."""
    check_device_id(device_id)
    check_port_free(device_id, port, gpio.OUT)
    gpio.devices[device_id].setup(port, gpio.OUT)


def setup_input(device_id, port):
    """Set up a GPIO as input."""
    check_device_id(device_id)
    gpio.devices[device_id].setup(port, gpio.IN)
    check_port_free(device_id, port, gpio.IN)


def write_output(device_id, port, value):
    """Write a value to a GPIO."""
    gpio.devices[device_id].write(port, value)


def read_input(device_id, port):
    """Read a value from a GPIO."""
    return gpio.devices[device_id].read(port)


def read_adc_input(device_id, port):
    """Read an ADC value from a GPIO ADC port."""
    return gpio.devices[device_id].adc_read(port)


def edge_detect(device_id, port, event_callback):
    """Add detection for RISING and FALLING events."""
    gpio.devices[device_id].add_event_detect(port, event_callback, gpio.BOTH)
    gpio.devices[device_id].notify(True)
