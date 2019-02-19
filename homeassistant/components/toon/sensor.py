"""Support for Toon sensors."""
from datetime import timedelta
import logging

from homeassistant.components.toon import ToonEntity
from homeassistant.components.toon.const import DATA_TOON_CLIENT, DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from .const import CURRENCY_EUR, POWER_KWH, POWER_WATT, VOLUME_CM3, VOLUME_M3

DEPENDENCIES = ['toon']

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry,
                            async_add_entities) -> None:
    """Set up Toon sensors based on a config entry."""
    toon = hass.data[DATA_TOON_CLIENT][entry.entry_id]

    sensors = [
        ToonSensor(toon, 'power', 'value', "Current Power Usage",
                   'mdi:power-plug', POWER_WATT),
        ToonSensor(toon, 'power', 'average', "Average Power Usage",
                   'mdi:power-plug', POWER_WATT),
        ToonSensor(toon, 'power', 'daily_value', "Power Usage Today",
                   'mdi:power-plug', POWER_KWH),
        ToonSensor(toon, 'power', 'average_daily', "Average Daily Power Usage",
                   'mdi:power-plug', POWER_KWH),
        ToonSensor(toon, 'power', 'meter_reading',
                   "Power Meter Feed IN Tariff 1", 'mdi:power-plug',
                   POWER_KWH),
        ToonSensor(toon, 'power', 'meter_reading_low',
                   "Power Meter Feed IN Tariff 2", 'mdi:power-plug',
                   POWER_KWH),
    ]

    if toon.gas:
        sensors.extend([
            ToonSensor(toon, 'gas', 'value', "Current Gas Usage",
                       'mdi:gas-cylinder', VOLUME_CM3),
            ToonSensor(toon, 'gas', 'average', "Average Gas Usage",
                       'mdi:gas-cylinder', VOLUME_CM3),
            ToonSensor(toon, 'gas', 'daily_usage', "Gas Usage Today",
                       'mdi:gas-cylinder', VOLUME_M3),
            ToonSensor(toon, 'gas', 'average_daily', "Average Daily Gas Usage",
                       'mdi:gas-cylinder', VOLUME_M3),
            ToonSensor(toon, 'gas', 'meter_reading', "Gas Meter",
                       'mdi:gas-cylinder', VOLUME_M3),
            ToonSensor(toon, 'gas', 'daily_cost', "Gas Cost Today",
                       'mdi:gas-cylinder', CURRENCY_EUR),
        ])

    if toon.solar:
        sensors.extend([
            ToonSensor(toon, 'solar', 'value', "Current Solar Production",
                       'mdi:solar-power', POWER_WATT),
            ToonSensor(toon, 'solar', 'maximum', "Max Solar Production",
                       'mdi:solar-power', POWER_WATT),
            ToonSensor(toon, 'solar', 'produced', "Solar Production to Grid",
                       'mdi:solar-power', POWER_WATT),
            ToonSensor(toon, 'solar', 'average_produced',
                       "Average Solar Production to Grid", 'mdi:solar-power',
                       POWER_WATT),
            ToonSensor(toon, 'solar', 'meter_reading_produced',
                       "Power Meter Feed OUT Tariff 1", 'mdi:solar-power',
                       POWER_KWH),
            ToonSensor(toon, 'solar', 'meter_reading_low_produced',
                       "Power Meter Feed OUT Tariff 2", 'mdi:solar-power',
                       POWER_KWH),
        ])

    async_add_entities(sensors)


class ToonSensor(ToonEntity):
    """Representation of a Toon sensor."""

    def __init__(self, toon, section: str, measurement: str,
                 name: str, icon: str, unit_of_measurement: str) -> None:
        """Initialize the Toon sensor."""
        self._state = None
        self._unit_of_measurement = unit_of_measurement
        self.section = section
        self.measurement = measurement

        super().__init__(toon, name, icon)

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return '_'.join([DOMAIN, self.toon.agreement.id, 'sensor',
                         self.section, self.measurement])

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    async def async_update(self) -> None:
        """Get the latest data from the sensor."""
        section = getattr(self.toon, self.section)
        value = None

        if self.section == 'power' and self.measurement == 'daily_value':
            value = round((float(section.daily_usage)
                           + float(section.daily_usage_low)) / 1000.0, 2)

        if value is None:
            value = getattr(section, self.measurement)

        if self.section == 'power' and \
                self.measurement in ['meter_reading', 'meter_reading_low',
                                     'average_daily']:
            value = round(float(value)/1000.0, 2)

        if self.section == 'solar' and \
                self.measurement in ['meter_reading_produced',
                                     'meter_reading_low_produced']:
            value = float(value)/1000.0

        if self.section == 'gas' and \
                self.measurement in ['average_daily', 'daily_usage',
                                     'meter_reading']:
            value = round(float(value)/1000.0, 2)

        self._state = max(0, value)
