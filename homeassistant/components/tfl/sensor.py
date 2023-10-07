"""Sensor for Transport for London (TfL)."""
from __future__ import annotations

from datetime import timedelta
import logging
from operator import itemgetter

from tflwrapper import stopPoint

from homeassistant.components.sensor import (  # ENTITY_ID_FORMAT,; PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_helper import config_from_entry
from .const import (
    CONF_STOP_POINTS,
    DOMAIN,
    RAW_ARRIVAL_DESTINATION_NAME,
    RAW_ARRIVAL_LINE_NAME,
    RAW_ARRIVAL_TIME_TO_STATION,
)

SCAN_INTERVAL = timedelta(seconds=30)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the TfL sensor."""
    stop_point_api = hass.data[DOMAIN][entry.entry_id]

    conf = config_from_entry(entry)

    stop_point_ids = conf[CONF_STOP_POINTS]

    stop_point_infos = await hass.async_add_executor_job(
        stop_point_api.getByIDs, stop_point_ids, False
    )
    devices = []
    if isinstance(stop_point_infos, list):
        for idx, stop_point_id in enumerate(stop_point_ids):
            devices.append(
                StopPointSensor(
                    stop_point_api,
                    stop_point_infos[idx]["commonName"],
                    stop_point_id,
                    entry.entry_id,
                )
            )
    else:
        devices.append(
            StopPointSensor(
                stop_point_api,
                stop_point_infos["commonName"],
                stop_point_ids[0],
                entry.entry_id,
            )
        )

    async_add_entities(devices, True)


class StopPointSensor(SensorEntity):
    """Representation of a TfL StopPoint as a Sensor."""

    _attr_attribution = "Powered by TfL Open Data"
    _attr_icon = "mdi:bus"

    def __init__(
        self, stop_point_api: stopPoint, name: str, stop_point_id: str, entry_id: str
    ) -> None:
        """Initialize the TfL StopPoint sensor."""
        # super().__init__(coordinator)
        self._name = name
        self._attr_name = name
        self._attr_unique_id = stop_point_id
        self._attr_device_info = DeviceInfo(
            name="TfL",
            identifiers={(DOMAIN, entry_id)},
            entry_type=DeviceEntryType.SERVICE,
        )

        self._stop_point_api = stop_point_api
        self._stop_point_id = stop_point_id

    async def async_update(self) -> None:
        """Update Stop Point state."""

        def raw_arrival_to_arrival_mapper(raw_arrival):
            return {
                "line_name": raw_arrival[RAW_ARRIVAL_LINE_NAME],
                "destination_name": raw_arrival[RAW_ARRIVAL_DESTINATION_NAME],
                "time_to_station": raw_arrival[RAW_ARRIVAL_TIME_TO_STATION],
            }

        raw_arrivals = await self.hass.async_add_executor_job(
            self._stop_point_api.getStationArrivals, self._stop_point_id
        )
        raw_arrivals_sorted = sorted(
            raw_arrivals, key=itemgetter(RAW_ARRIVAL_TIME_TO_STATION)
        )

        arrivals = list(map(raw_arrival_to_arrival_mapper, raw_arrivals_sorted))
        _LOGGER.debug("Got arrivals=%s", arrivals)

        arrival_next = arrivals[0]
        arrivals_next_3 = arrivals[:3]

        # Due to 255 character limit, the value of the sensor is the next arrival and
        # the next 3 and full list are provided as attributes
        self._attr_native_value = arrival_next
        attributes = {}
        attributes["next_3"] = arrivals_next_3
        attributes["all"] = arrivals
        self._attr_extra_state_attributes = attributes
