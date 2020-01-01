"""Support for Sure PetCare Flaps binary sensors."""
import logging
import pprint

from homeassistant.const import (
    ATTR_VOLTAGE,
    CONF_ID,
    CONF_NAME,
    CONF_TYPE,
    DEVICE_CLASS_BATTERY,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    BATTERY_ICON,
    CONF_DATA,
    CONF_HOUSEHOLD_ID,
    DATA_SURE_PETCARE,
    SURE_BATT_VOLTAGE_DIFF,
    SURE_BATT_VOLTAGE_LOW,
    SURE_IDS,
    TOPIC_UPDATE,
    SureThingID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Sure PetCare Flaps sensors based on a config entry."""
    if not discovery_info:
        return

    entities = []

    for thing in hass.data[DATA_SURE_PETCARE][SURE_IDS]:
        sure_id = thing[CONF_ID]
        sure_type = thing[CONF_TYPE]
        sure_data = thing[CONF_DATA]

        if sure_type != SureThingID.FLAP.name:
            continue

        if sure_id not in hass.data[DATA_SURE_PETCARE][sure_type]:
            hass.data[DATA_SURE_PETCARE][sure_type][sure_id] = sure_data

        entities.append(FlapBattery(sure_id, thing[CONF_NAME]))

    async_add_entities(entities, True)


class FlapBattery(Entity):
    """Sure Petcare Flap."""

    def __init__(self, _id: int, name: str, data: dict = None):
        """Initialize a Sure Petcare Flap battery sensor."""
        self._id = _id
        self._name = f"Flap {name.capitalize()} Battery Level"
        self._unit_of_measurement = "%"
        self._icon = BATTERY_ICON
        self._state = {}

    @property
    def should_poll(self):
        """Return true."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def state(self):
        """Return battery level in percent."""
        try:
            per_battery_voltage = self._state["battery"] / 4
            voltage_diff = per_battery_voltage - SURE_BATT_VOLTAGE_LOW
            battery_percent = int(voltage_diff / SURE_BATT_VOLTAGE_DIFF * 100)
        except (KeyError, TypeError):
            battery_percent = None

        return battery_percent

    @property
    def unique_id(self):
        """Return an unique ID."""
        return f"{self._household_id}-{self._id}"

    @property
    def device_classe(self):
        """Return the device class."""
        return DEVICE_CLASS_BATTERY

    @property
    def device_state_attributes(self):
        """Return an unique ID."""
        try:
            voltage_per_battery = float(self._state["battery"]) / 4
            attributes = {
                ATTR_VOLTAGE: f"{float(self._state['battery']):.2f} V",
                f"{ATTR_VOLTAGE}_per_battery": f"{voltage_per_battery:.2f} V",
            }
        except (KeyError, TypeError) as error:
            attributes = None
            _LOGGER.debug(
                "error getting device state attributes from %s: %s\n\n%s",
                self._name,
                error,
                self._state,
            )

        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    async def async_update(self):
        """Get the latest data and update the state."""
        try:
            if self._data[self._id]:
                self._state = self._data[self._id]
            else:
                _LOGGER.debug(
                    "async_update from %s got no new data: %s",
                    self._name,
                    pprint.pformat(self._data),
                )
        except (AttributeError, KeyError, TypeError) as error:
            _LOGGER.debug("async_update error from %s: %s", self._name, error)

    async def async_added_to_hass(self):
        """Register callbacks."""

        # pylint: disable=attribute-defined-outside-init
        self._household_id = self.hass.data[DATA_SURE_PETCARE][CONF_HOUSEHOLD_ID]
        self._data = self.hass.data[DATA_SURE_PETCARE][SureThingID.FLAP.name]

        @callback
        def update():
            """Update the state."""
            self.async_schedule_update_ha_state(True)

        # pylint: disable=attribute-defined-outside-init
        self._async_unsub_dispatcher_connect = async_dispatcher_connect(
            self.hass, TOPIC_UPDATE, update
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        # pylint: disable=using-constant-test
        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()
