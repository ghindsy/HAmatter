"""Sensor platform for local_ip."""
from homeassistant.const import CONF_NAME, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.util import get_local_ip

from . import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Set up the sensor platform."""
    name = hass.data[DOMAIN][CONF_NAME]
    async_add_entities([IPSensor(name)], True)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the platform from config_entry."""
    return await async_setup_platform(hass, {}, async_add_entities, None)


class IPSensor(Entity):
    """A simple sensor."""

    def __init__(self, name: str):
        """Initialize the sensor."""
        self._state = STATE_UNKNOWN
        self._name = name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Fetch new state data for the sensor."""
        self._state = get_local_ip()
