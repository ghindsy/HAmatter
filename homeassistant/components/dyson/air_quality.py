"""Support for Dyson Pure Cool Air Quality Sensors."""
import logging

from libpurecool.dyson_pure_cool import DysonPureCool
from libpurecool.dyson_pure_state_v2 import DysonEnvironmentalSensorV2State

from homeassistant.components.air_quality import (
    DOMAIN as AIR_QUALITY_DOMAIN,
    AirQualityEntity,
)

from . import DYSON_DEVICES, DysonEntity

ATTRIBUTION = "Dyson purifier air quality sensor"

_LOGGER = logging.getLogger(__name__)

DYSON_AIQ_DEVICES = "dyson_aiq_devices"

ATTR_VOC = "volatile_organic_compounds"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Dyson Sensors."""

    if discovery_info is None:
        return

    hass.data.setdefault(DYSON_AIQ_DEVICES, [])

    # Get Dyson Devices from parent component
    device_ids = [device.unique_id for device in hass.data[DYSON_AIQ_DEVICES]]
    new_entities = []
    for device in hass.data[DYSON_DEVICES]:
        if (
            isinstance(device, DysonPureCool)
            and f"{device.serial}/air_quality" not in device_ids
        ):
            new_entities.append(DysonAirSensor(device))

    if not new_entities:
        return

    hass.data[DYSON_AIQ_DEVICES].extend(new_entities)
    add_entities(hass.data[DYSON_AIQ_DEVICES])


class DysonAirSensor(DysonEntity, AirQualityEntity):
    """Representation of a generic Dyson air quality sensor."""

    def __init__(self, device):
        """Create a new generic air quality Dyson sensor."""
        super().__init__(device, DysonEnvironmentalSensorV2State, AIR_QUALITY_DOMAIN)
        self._old_value = None

    def on_message(self, message):
        """Handle new messages which are received from the fan."""
        if (
            self._old_value is None
            or self._old_value != self._device.environmental_state
        ):
            self._old_value = self._device.environmental_state
            return True
        return False

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def air_quality_index(self):
        """Return the Air Quality Index (AQI)."""
        return max(
            self.particulate_matter_2_5,
            self.particulate_matter_10,
            self.nitrogen_dioxide,
            self.volatile_organic_compounds,
        )

    @property
    def particulate_matter_2_5(self):
        """Return the particulate matter 2.5 level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.particulate_matter_25)
        return None

    @property
    def particulate_matter_10(self):
        """Return the particulate matter 10 level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.particulate_matter_10)
        return None

    @property
    def nitrogen_dioxide(self):
        """Return the NO2 (nitrogen dioxide) level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.nitrogen_dioxide)
        return None

    @property
    def volatile_organic_compounds(self):
        """Return the VOC (Volatile Organic Compounds) level."""
        if self._device.environmental_state:
            return int(self._device.environmental_state.volatile_organic_compounds)
        return None

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        data = {}

        voc = self.volatile_organic_compounds
        if voc is not None:
            data[ATTR_VOC] = voc
        return data
