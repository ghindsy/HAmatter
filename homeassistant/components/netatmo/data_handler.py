"""The Netatmo data handler."""
import asyncio
from datetime import timedelta
from functools import partial
import logging
from typing import Dict, List

import pyatmo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import AUTH, DOMAIN

_LOGGER = logging.getLogger(__name__)


DATA_CLASSES = {
    "WeatherStationData": pyatmo.WeatherStationData,
    "HomeCoachData": pyatmo.HomeCoachData,
    "CameraData": pyatmo.CameraData,
    "HomeData": pyatmo.HomeData,
    "HomeStatus": pyatmo.HomeStatus,
}

MAX_CALLS_10S = 2
MAX_CALLS_1H = 20


class NetatmoDataHandler:
    """Manages the Netatmo data handling."""

    # Central class to manage the polling data from the Netatmo API
    # as well as the push data from the webhook
    #
    # Create one instance of the handler and store it in hass.data
    #
    # Register entities of its platforms when added to HA
    # to receive signals once new data is available
    #
    # Fetch data for all data classes for the first time
    # to gather all available entities
    # then only update periodically the registered data classes and
    # dispatch signals for the registered entities to fetch the new data

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the system."""
        self.hass = hass
        self._auth = hass.data[DOMAIN][entry.entry_id][AUTH]
        self.listeners: List[CALLBACK_TYPE] = []
        self._data_classes: Dict = {}
        self.data = {}
        self._intervals = {}
        self._queue: List = []
        self._parallel = 2
        self._wait = 20

    async def async_setup(self):
        """Set up a UniFi controller."""
        for data_class_name in [
            "WeatherStationData",
            "HomeCoachData",
            "CameraData",
            "HomeData",
        ]:
            await self.register_data_class(data_class_name)

        async def async_update(event_time):
            """Update device."""
            queue = [entry for entry in self._queue[0 : self._parallel]]
            for _ in queue:
                self._queue.append(self._queue.pop(0))

            try:
                results = await asyncio.gather(
                    *[
                        self.hass.async_add_executor_job(
                            partial(data_class["class"], **data_class["kwargs"],),
                            self._auth,
                        )
                        for data_class in queue
                    ]
                )
            except pyatmo.NoDevice as err:
                _LOGGER.debug(err)

            for data_class, result in zip(queue, results):
                self.data[data_class["name"]] = result
                async_dispatcher_send(self.hass, f"netatmo-update-{data_class['name']}")

        async_track_time_interval(
            self.hass, async_update, timedelta(seconds=self._wait)
        )

    async def register_data_class(self, data_class_name, **kwargs):
        """Register data class."""
        if "home_id" in kwargs:
            data_class_entry = f"{data_class_name}-{kwargs['home_id']}"
        else:
            data_class_entry = data_class_name

        if data_class_entry not in self._data_classes:
            self._data_classes[data_class_entry] = {
                "class": DATA_CLASSES[data_class_name],
                "name": data_class_entry,
                "kwargs": kwargs,
                "registered": 1,
            }
            self.data[data_class_entry] = await self.hass.async_add_executor_job(
                partial(DATA_CLASSES[data_class_name], **kwargs,), self._auth,
            )
            self._queue.append(self._data_classes[data_class_entry])
            _LOGGER.debug("Data class %s added", data_class_name)
        else:
            self._data_classes[data_class_entry].update(
                registered=self._data_classes[data_class_entry]["registered"] + 1
            )

    async def unregister_data_class(self, data_class_entry):
        """Unregister data class."""
        registered = self._data_classes[data_class_entry]["registered"]
        if registered > 1:
            self._data_classes[data_class_entry].update(registered=registered - 1)
        else:
            self._data_classes.pop(data_class_entry)
            _LOGGER.debug("Data class %s removed", data_class_entry)

    # def update_interval(self):
    #     self._wait =


@callback
def add_entities(entities, async_add_entities, hass):
    """Add new sensor entities."""
    async_add_entities(entities)


async def async_config_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle signals of config entry being updated."""
    async_dispatcher_send(hass, "signal_update")
