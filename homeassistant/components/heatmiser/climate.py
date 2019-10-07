"""Support for the PRT Heatmiser themostats using the V3 protocol."""
import logging

from heatmiserV3 import connection, heatmiser
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateDevice
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    TEMP_CELSIUS,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_IPADDRESS = "ipaddress"
CONF_TSTATS = "tstats"

TSTATS_SCHEMA = vol.Schema(
    {vol.Required(CONF_ID): cv.string, vol.Required(CONF_NAME): cv.string}
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IPADDRESS): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Required(CONF_TSTATS, default={}): vol.Schema({cv.string: TSTATS_SCHEMA}),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the heatmiser thermostat."""

    ipaddress = config.get(CONF_IPADDRESS)
    port = str(config.get(CONF_PORT))
    tstats = config.get(CONF_TSTATS)

    serport = connection.connection(ipaddress, port)
    serport.open()

    add_entities(
        [
            HeatmiserV3Thermostat(
                heatmiser, tstat.get(CONF_ID), tstat.get(CONF_NAME), serport
            )
            for tstat in tstats.values()
        ],
        True,
    )


class HeatmiserV3Thermostat(ClimateDevice):
    """Representation of a HeatmiserV3 thermostat."""

    def __init__(self, heatmiser, device, name, serport):
        """Initialize the thermostat."""
        self.heatmiser = heatmiser
        self.serport = serport
        self._current_temperature = None
        self._target_temperature = None
        self._name = name
        self._id = device
        self.dcb = None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self.heatmiser.hmSendAddress(self._id, 18, temperature, 1, self.serport)

    def update(self):
        """Get the latest data."""
        self.dcb = self.heatmiser.hmReadAddress(self._id, "prt", self.serport)
        low = self.dcb.get("floortemplow ")
        high = self.dcb.get("floortemphigh")
        self._current_temperature = (high * 256 + low) / 10.0
        self._target_temperature = int(self.dcb.get("roomset"))
