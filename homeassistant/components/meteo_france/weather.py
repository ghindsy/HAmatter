"""Support for Meteo-France weather service."""
import logging

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    WeatherEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.typing import HomeAssistantType

from . import MeteoFranceDataUpdateCoordinator
from .const import ATTRIBUTION, CONDITION_CLASSES, DOMAIN

_LOGGER = logging.getLogger(__name__)


def format_condition(condition: str):
    """Return condition from dict CONDITION_CLASSES."""
    for key, value in CONDITION_CLASSES.items():
        if condition in value:
            return key
    return condition


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Meteo-France weather platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([MeteoFranceWeather(coordinator)], True)


class MeteoFranceWeather(WeatherEntity):
    """Representation of a weather condition."""

    def __init__(self, coordinator: MeteoFranceDataUpdateCoordinator):
        """Initialise the platform with a data instance and station name."""
        self.coordinator = coordinator

    @property
    def available(self):
        """Return if state is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return self.coordinator.data.position["name"]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.coordinator.data.position["name"]

    @property
    def condition(self):
        """Return the current condition."""
        return format_condition(self.coordinator.data.forecast[2]["weather"]["desc"])

    @property
    def temperature(self):
        """Return the temperature."""
        return self.coordinator.data.forecast[2]["T"]["value"]

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def humidity(self):
        """Return the humidity."""
        return self.coordinator.data.forecast[2]["humidity"]

    @property
    def wind_speed(self):
        """Return the wind speed."""
        return self.coordinator.data.forecast[2]["wind"]["speed"]

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        wind_bearing = self.coordinator.data.forecast[2]["wind"]["direction"]
        if wind_bearing != -1:
            return wind_bearing

    @property
    def forecast(self):
        """Return the forecast."""
        _LOGGER.warning(self.coordinator.data.forecast[2])
        forecast_data = []
        for index, forecast in enumerate(self.coordinator.data.daily_forecast):
            # The first day is yesterday
            if index == 0:
                continue
            # keeping until we don't have a weather condition
            if not forecast.get("weather12H"):
                break
            forecast_data.append(
                {
                    ATTR_FORECAST_TIME: self.coordinator.data.timestamp_to_locale_time(
                        forecast["dt"]
                    ),
                    ATTR_FORECAST_CONDITION: format_condition(
                        forecast["weather12H"]["desc"]
                    ),
                    ATTR_FORECAST_TEMP: forecast["T"]["max"],
                    ATTR_FORECAST_TEMP_LOW: forecast["T"]["min"],
                    ATTR_FORECAST_PRECIPITATION: forecast["precipitation"]["24h"],
                }
            )
        return forecast_data

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION
