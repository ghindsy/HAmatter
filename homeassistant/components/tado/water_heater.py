"""
Support for Tado hot water zones.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/water_heater/tado/
"""
import logging

from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
)
from homeassistant.components.water_heater import (
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    WaterHeaterDevice,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN, SIGNAL_TADO_UPDATE_RECEIVED, TYPE_HOT_WATER

_LOGGER = logging.getLogger(__name__)

CONST_MODE_SMART_SCHEDULE = "SMART_SCHEDULE"
CONST_MODE_OFF = "OFF"
CONST_OVERLAY_TADO_MODE = "TADO_MODE"
CONST_OVERLAY_MANUAL = "MANUAL"

WATER_HEATER_MAP_TADO = {
    "MANUAL": HVAC_MODE_HEAT,
    "TIMER": HVAC_MODE_HEAT,
    "TADO_MODE": HVAC_MODE_HEAT,
    "SMART_SCHEDULE": HVAC_MODE_AUTO,
    "OFF": HVAC_MODE_OFF,
}

SUPPORT_FLAGS_HEATER = SUPPORT_OPERATION_MODE


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tado water heater platform."""
    tado = hass.data[DOMAIN]

    try:
        zones = tado.get_zones()
    except RuntimeError:
        _LOGGER.error("Unable to get zone info")
        return

    water_heater_devices = []
    for zone in zones:
        if zone["type"] == TYPE_HOT_WATER:
            device = create_water_heater_device(tado, zone["name"], zone["id"])
            if device:
                water_heater_devices.append(device)

    if water_heater_devices:
        add_entities(water_heater_devices, True)


def create_water_heater_device(tado, name, zone_id):
    """Create a Tado water heater device."""
    capabilities = tado.get_capabilities(zone_id)
    supports_temperature_control = capabilities["canSetTemperature"]

    if supports_temperature_control and "temperatures" in capabilities:
        temperatures = capabilities["temperatures"]
        min_temp = float(temperatures["celsius"]["min"])
        max_temp = float(temperatures["celsius"]["max"])
    else:
        min_temp = None
        max_temp = None

    device = TadoWaterHeater(
        tado, name, zone_id, supports_temperature_control, min_temp, max_temp
    )

    return device


class TadoWaterHeater(WaterHeaterDevice):
    """Representation of a Tado water heater."""

    def __init__(
        self,
        tado,
        zone_name,
        zone_id,
        supports_temperature_control,
        min_temp,
        max_temp,
    ):
        """Initialize of Tado water heater device."""
        self._tado = tado

        self.zone_name = zone_name
        self.zone_id = zone_id

        self._device_is_active = False
        self._is_away = False

        self._supports_temperature_control = supports_temperature_control
        self._min_temperature = min_temp
        self._max_temperature = max_temp

        self._target_temp = None

        self._supported_features = SUPPORT_FLAGS_HEATER
        if self._supports_temperature_control:
            self._supported_features |= SUPPORT_TARGET_TEMPERATURE

        self._current_operation = CONST_MODE_SMART_SCHEDULE
        self._overlay_mode = CONST_MODE_SMART_SCHEDULE

    async def async_added_to_hass(self):
        """Register for sensor updates."""
        async_dispatcher_connect(
            self.hass,
            SIGNAL_TADO_UPDATE_RECEIVED.format(self.zone_id),
            self._handle_update,
        )
        self._tado.add_sensor("zone", self.zone_id)
        await self.hass.async_add_executor_job(self._tado.update)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._supported_features

    @property
    def name(self):
        """Return the name of the device."""
        return self.zone_name

    @property
    def current_operation(self):
        """Return current readable operation mode."""
        return WATER_HEATER_MAP_TADO.get(self._current_operation)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._is_away

    @property
    def operation_list(self):
        """Return the list of available operation modes (readable)."""
        return [HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temperature

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temperature

    def set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        mode = None

        if operation_mode == HVAC_MODE_OFF:
            mode = CONST_MODE_OFF
        elif operation_mode == HVAC_MODE_AUTO:
            mode = CONST_MODE_SMART_SCHEDULE
        elif operation_mode == HVAC_MODE_HEAT:
            mode = CONST_OVERLAY_TADO_MODE

        self._current_operation = mode
        self._overlay_mode = None

        # Set a target temperature if we don't have any
        if mode == CONST_OVERLAY_TADO_MODE and self._target_temp is None:
            self._target_temp = self.min_temp
            self.schedule_update_ha_state()

        self._control_heater()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if not self._supports_temperature_control or temperature is None:
            return

        self._current_operation = CONST_OVERLAY_TADO_MODE
        self._overlay_mode = None
        self._target_temp = temperature
        self._control_heater()

    def _handle_update(self, data):
        """Handle update callbacks."""
        if "tadoMode" in data:
            mode = data["tadoMode"]
            self._is_away = mode == "AWAY"

        if "setting" in data:
            power = data["setting"]["power"]
            if power == "OFF":
                self._current_operation = CONST_MODE_OFF
                # There is no overlay, the mode will always be
                # "SMART_SCHEDULE"
                self._overlay_mode = CONST_MODE_SMART_SCHEDULE
                self._device_is_active = False
            else:
                self._device_is_active = True

        # temperature setting will not exist when device is off
        if (
            "temperature" in data["setting"]
            and data["setting"]["temperature"] is not None
        ):
            setting = float(data["setting"]["temperature"]["celsius"])
            self._target_temp = setting

        overlay = False
        overlay_data = None
        termination = CONST_MODE_SMART_SCHEDULE

        if "overlay" in data:
            overlay_data = data["overlay"]
            overlay = overlay_data is not None

        if overlay:
            termination = overlay_data["termination"]["type"]

        if self._device_is_active:
            # If you set mode manually to off, there will be an overlay
            # and a termination, but we want to see the mode "OFF"
            self._overlay_mode = termination
            self._current_operation = termination

        self.schedule_update_ha_state()

    def _control_heater(self):
        """Send new target temperature."""
        if self._current_operation == CONST_MODE_SMART_SCHEDULE:
            _LOGGER.info(
                "Switching to SMART_SCHEDULE for zone %s (%d)",
                self.zone_name,
                self.zone_id,
            )
            self._tado.reset_zone_overlay(self.zone_id)
            self._overlay_mode = self._current_operation
            return

        if self._current_operation == CONST_MODE_OFF:
            _LOGGER.info(
                "Switching to OFF for zone %s (%d)", self.zone_name, self.zone_id
            )
            self._tado.set_zone_off(self.zone_id, CONST_OVERLAY_MANUAL, TYPE_HOT_WATER)
            self._overlay_mode = self._current_operation
            return

        _LOGGER.info(
            "Switching to %s for zone %s (%d) with temperature %s",
            self._current_operation,
            self.zone_name,
            self.zone_id,
            self._target_temp,
        )
        self._tado.set_zone_overlay(
            self.zone_id,
            self._current_operation,
            self._target_temp,
            None,
            TYPE_HOT_WATER,
        )
        self._overlay_mode = self._current_operation
