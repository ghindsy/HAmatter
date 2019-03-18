"""Support for Sure PetCare Flaps binary sensors."""
import logging
from typing import AnyStr

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (CONF_FLAPS, CONF_HOUSEHOLD_ID, CONF_PETS,
                    DATA_SURE_PETCARE, DEFAULT_DEVICE_CLASS, DEFAULT_ICON,
                    SURE_IDS, SURE_TYPES, TOPIC_UPDATE)

_LOGGER = logging.getLogger(__name__)

# SCAN_INTERVAL = timedelta(seconds=600)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Sure PetCare Flaps sensors based on a config entry."""
    hass.data[DATA_SURE_PETCARE][CONF_HOUSEHOLD_ID] = entry.data[CONF_HOUSEHOLD_ID]
    hass.data[DATA_SURE_PETCARE][CONF_FLAPS] = dict()
    hass.data[DATA_SURE_PETCARE][CONF_PETS] = dict()

    sensors = list()

    for thing in entry.data[SURE_IDS]:
        sure_id = thing[CONF_ID]
        sure_type = thing[CONF_TYPE]

        if sure_type in SURE_TYPES:

            if sure_id not in hass.data[DATA_SURE_PETCARE][sure_type]:
                hass.data[DATA_SURE_PETCARE][sure_type][sure_id] = None

            if sure_type == CONF_PETS:
                entity = Pet(sure_id, thing[CONF_NAME], hass=hass)
            elif sure_type == CONF_FLAPS:
                entity = Flap(sure_id, thing[CONF_NAME], hass=hass)

            sensors.append(entity)

    async_add_entities(sensors, True)


class SurePetcareBinarySensor(BinarySensorDevice):
    """A binary sensor implementation for Sure Petcare Entities."""

    def __init__(self, _id: int, name: int, hass=None):
        self._hass = hass

        self._household_id: int = hass.data[DATA_SURE_PETCARE][CONF_HOUSEHOLD_ID]
        self._id: int = _id
        self._name: AnyStr = f"{self._type[:-1].capitalize()} {name}"

        self._data = hass.data[DATA_SURE_PETCARE][self._type]
        self._state = dict()

    @property
    def is_on(self):
        """Return true if light is on."""
        # return self._state
        # pass

    @property
    def should_poll(self):
        """Return true."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state

    @property
    def device_class(self):
        """Return the device class."""
        return DEFAULT_DEVICE_CLASS if not self._device_class else self._device_class

    @property
    def icon(self):
        """Return the device class."""
        return DEFAULT_ICON if not self._icon else self._icon

    @property
    def unique_id(self):
        """Return an unique ID."""
        return "{}-{}".format(self._household_id, self._id)

    async def async_update(self):
        """Get the latest data and update the state."""
        try:
            self._state = self._data[self._id]
        except (AttributeError, KeyError, TypeError):
            pass

    async def async_added_to_hass(self):
        """Register callbacks."""
        @callback
        def update():
            """Update the state."""
            self.async_schedule_update_ha_state(True)

        self._async_unsub_dispatcher_connect = async_dispatcher_connect(self._hass, TOPIC_UPDATE, update)

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()


class Flap(SurePetcareBinarySensor):

    def __init__(self, _id: int, name: int, hass=None):
        self._device_class = "door"
        self._icon = "mdi:lock"
        self._type = CONF_FLAPS

        super().__init__(
            _id,
            name,
            hass=hass,
        )

    @property
    def is_on(self):
        """Return true if light is on."""
        try:
            return bool(self._state["locking"]["mode"])
        except (KeyError, TypeError):
            return False


class Pet(SurePetcareBinarySensor):

    def __init__(self, _id: int, name: int, hass=None):
        self._device_class = "presence"
        self._icon = "mdi:cat"
        self._type = CONF_PETS

        super().__init__(
            _id,
            name,
            hass=hass,
        )

    @property
    def is_on(self):
        """Return true if light is on."""
        try:
            return bool(self._state["where"])
        except (KeyError, TypeError):
            return False
