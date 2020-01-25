"""Sensor platform for hvv."""
from datetime import datetime, timedelta
import logging

from pygti.gti import GTI, Auth

from homeassistant.const import DEVICE_CLASS_TIMESTAMP
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from .const import DOMAIN, MANUFACTURER

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)
MAX_LIST = 10
MAX_TIME_OFFSET = 200
ICON = "mdi:bus"
UNIT_OF_MEASUREMENT = "min"

ATTR_DEPARTURE = "departure"
ATTR_LINE = "line"
ATTR_ORIGIN = "origin"
ATTR_DIRECTION = "direction"
ATTR_TYPE = "type"
ATTR_ID = "id"
ATTR_DELAY = "delay"
ATTR_NEXT = "next"

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Set up the sensor platform.

    Skipped, as setup through configuration.yaml is not supported.
    """

    pass


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the sensor platform."""

    session = aiohttp_client.async_get_clientsession(hass)
    async_add_devices([HVVDepartureSensor(hass, config_entry, session)], True)


class HVVDepartureSensor(Entity):
    """HVVDepartureSensor class."""

    def __init__(self, hass, entry, session):
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.config = self.entry.data
        self.station_name = self.config["station"]["name"]
        self.attr = {}
        self._state = None
        self._name = f"Departures at {self.station_name}"

        self.gti = GTI(
            Auth(
                session,
                self.config["username"],
                self.config["password"],
                self.config["host"],
            )
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Update the sensor."""

        try:

            departure_time = datetime.now() + timedelta(minutes=self.config["offset"])

            payload = {
                "station": self.config["station"],
                "time": {
                    "date": departure_time.strftime("%d.%m.%Y"),
                    "time": departure_time.strftime("%H:%M"),
                },
                "maxList": MAX_LIST,
                "maxTimeOffset": MAX_TIME_OFFSET,
                "useRealtime": self.config["realtime"],
                "filter": self.config["filter"],
            }

            data = await self.gti.departureList(payload)

            if data["returnCode"] == "OK" and len(data["departures"]) > 0:
                departure = data["departures"][0]
                self._state = (
                    departure_time
                    + timedelta(minutes=departure["timeOffset"])
                    + timedelta(seconds=departure.get("delay", 0))
                )

                self.attr[ATTR_LINE] = departure["line"]["name"]
                self.attr[ATTR_ORIGIN] = departure["line"]["origin"]
                self.attr[ATTR_DIRECTION] = departure["line"]["direction"]
                self.attr[ATTR_TYPE] = departure["line"]["type"]["shortInfo"]
                self.attr[ATTR_ID] = departure["line"]["id"]
                self.attr[ATTR_DELAY] = departure.get("delay", 0)

                departures = []
                for departure in data["departures"]:
                    departures.append(
                        {
                            ATTR_DEPARTURE: departure_time
                            + timedelta(minutes=departure["timeOffset"])
                            + timedelta(seconds=departure.get("delay", 0)),
                            ATTR_LINE: departure["line"]["name"],
                            ATTR_ORIGIN: departure["line"]["origin"],
                            ATTR_DIRECTION: departure["line"]["direction"],
                            ATTR_TYPE: departure["line"]["type"]["shortInfo"],
                            ATTR_ID: departure["line"]["id"],
                            ATTR_DELAY: departure.get("delay", 0),
                        }
                    )
                self.attr[ATTR_NEXT] = departures
            else:
                self._state = None
                self.attr = {}

        except Exception as error:
            _LOGGER.error("Error occurred while fetching data: %r", error)
            self._state = None
            self.attr = {}

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        station_id = self.config["station"]["id"]
        station_type = self.config["station"]["type"]

        return f"{DOMAIN}-{self.entry.entry_id}-{station_id}-{station_type}"

    @property
    def device_info(self):
        """Return the device info for this sensor."""
        return {
            "identifiers": {
                (
                    DOMAIN,
                    self.entry.entry_id,
                    self.config["station"]["id"],
                    self.config["station"]["type"],
                )
            },
            "name": self.config["station"]["name"],
            "manufacturer": MANUFACTURER,
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_TIMESTAMP

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.attr
