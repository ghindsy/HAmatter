"""Support for Honeywell Round Connected and Honeywell Evohome thermostats."""
import datetime
import logging
from typing import Dict, Optional, List

import requests
import voluptuous as vol
import somecomfort

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    FAN_AUTO, FAN_DIFFUSE, FAN_ON,
    SUPPORT_AUX_HEAT, SUPPORT_FAN_MODE, SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    CURRENT_HVAC_COOL, CURRENT_HVAC_HEAT, CURRENT_HVAC_IDLE,
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_AUTO,
    PRESET_AWAY,
)
from homeassistant.const import (
    CONF_PASSWORD, CONF_USERNAME, TEMP_CELSIUS, TEMP_FAHRENHEIT,
    ATTR_TEMPERATURE, CONF_REGION)

_LOGGER = logging.getLogger(__name__)

ATTR_FAN = 'fan'
ATTR_SYSTEM_MODE = 'system_mode'
ATTR_CURRENT_OPERATION = 'equipment_output_status'

CONF_AWAY_TEMPERATURE = 'away_temperature'
CONF_COOL_AWAY_TEMPERATURE = 'away_cool_temperature'
CONF_HEAT_AWAY_TEMPERATURE = 'away_heat_temperature'

DEFAULT_AWAY_TEMPERATURE = 16  # in C, for eu regions, the others are F/us
DEFAULT_COOL_AWAY_TEMPERATURE = 88
DEFAULT_HEAT_AWAY_TEMPERATURE = 61
DEFAULT_REGION = 'eu'
REGIONS = ['eu', 'us']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_AWAY_TEMPERATURE,
                 default=DEFAULT_AWAY_TEMPERATURE): vol.Coerce(float),
    vol.Optional(CONF_COOL_AWAY_TEMPERATURE,
                 default=DEFAULT_COOL_AWAY_TEMPERATURE): vol.Coerce(int),
    vol.Optional(CONF_HEAT_AWAY_TEMPERATURE,
                 default=DEFAULT_HEAT_AWAY_TEMPERATURE): vol.Coerce(int),
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): vol.In(REGIONS),
})

HA_HVAC_MODE_TO_HW_MODE = {
    HVAC_MODE_OFF: 'off',
    HVAC_MODE_HEAT: 'heat',
    HVAC_MODE_COOL: 'cool',
    HVAC_MODE_AUTO: 'auto'
}
HW_MODE_TO_HA_HVAC_MODE = {
    'off': HVAC_MODE_OFF,
    'emheat': HVAC_MODE_HEAT,
    'heat': HVAC_MODE_HEAT,
    'cool': HVAC_MODE_COOL,
    'auto': HVAC_MODE_AUTO,
}
HW_MODE_TO_HA_HVAC_ACTION = {
    'off': CURRENT_HVAC_IDLE,
    'fan': CURRENT_HVAC_IDLE,
    'heat': CURRENT_HVAC_HEAT,
    'cool': CURRENT_HVAC_COOL,
}
HA_FAN_MODE_TO_HW = {
    FAN_ON: 'on',
    FAN_AUTO: 'auto',
    FAN_DIFFUSE: 'circulate'
}
HW_FAN_MODE_TO_HA = {
    'on': FAN_ON,
    'auto': FAN_AUTO,
    'circulate': FAN_DIFFUSE,
    'follow schedule': FAN_AUTO,
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Honeywell thermostat."""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    if config.get(CONF_REGION) == 'us':
        try:
            client = somecomfort.SomeComfort(username, password)
        except somecomfort.AuthError:
            _LOGGER.error("Failed to login to honeywell account %s", username)
            return False
        except somecomfort.SomeComfortError as ex:
            _LOGGER.error("Failed to initialize honeywell client: %s", str(ex))
            return False

        dev_id = config.get('thermostat')
        loc_id = config.get('location')
        cool_away_temp = config.get(CONF_COOL_AWAY_TEMPERATURE)
        heat_away_temp = config.get(CONF_HEAT_AWAY_TEMPERATURE)

        add_entities([HoneywellUSThermostat(client, device, cool_away_temp,
                                            heat_away_temp, username, password)
                      for location in client.locations_by_id.values()
                      for device in location.devices_by_id.values()
                      if ((not loc_id or location.locationid == loc_id) and
                          (not dev_id or device.deviceid == dev_id))])
        return True

    _LOGGER.warning(
        "The honeywell component has been deprecated for EU (i.e. non-US) "
        "systems. For EU-based systems, use the evohome component, "
        "see: https://home-assistant.io/components/evohome")
    return False


class HoneywellUSThermostat(ClimateDevice):
    """Representation of a Honeywell US Thermostat."""

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        self._device.system_mode = 'auto'

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (SUPPORT_AUX_HEAT |
                SUPPORT_FAN_MODE |
                SUPPORT_PRESET_MODE |
                SUPPORT_TARGET_TEMPERATURE)

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        return HW_MODE_TO_HA_HVAC_MODE[self._device.system_mode]

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return list(HA_HVAC_MODE_TO_HW_MODE)

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        return HW_MODE_TO_HA_HVAC_ACTION[self._device.equipment_output_status]

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        self._device.system_mode = \
            somecomfort.SYSTEM_MODES.index(HA_HVAC_MODE_TO_HW_MODE[hvac_mode])

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return PRESET_AWAY if self._away else None

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        return [PRESET_AWAY]

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_AWAY:
            self._turn_away_mode_on()
        else:
            self._turn_away_mode_off()

    @property
    def is_aux_heat(self) -> Optional[str]:
        """Return true if aux heater."""
        return self._device.system_mode == 'emheat'

    @property
    def fan_mode(self) -> Optional[str]:
        """Return the fan setting."""
        return HW_FAN_MODE_TO_HA[self._device.fan_mode]

    @property
    def fan_modes(self) -> Optional[List[str]]:
        """Return the list of available fan modes."""
        return list(HA_FAN_MODE_TO_HW)

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._device.fan_mode = \
            somecomfort.FAN_MODES.index(HA_FAN_MODE_TO_HW[fan_mode])

    @property
    def name(self) -> Optional[str]:
        """Return the name of the honeywell, if any."""
        return self._device.name

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return (TEMP_CELSIUS if self._device.temperature_unit == 'C'
                else TEMP_FAHRENHEIT)

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._device.current_temperature

    @property
    def current_humidity(self) -> Optional[int]:
        """Return the current humidity."""
        return self._device.current_humidity

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_COOL:
            return self._device.setpoint_cool
        elif self.hvac_mode != HVAC_MODE_OFF:
            return self._device.setpoint_heat
        return None

    def set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        try:
            # Get current mode
            mode = self._device.system_mode
            # Set hold if this is not the case
            if getattr(self._device, "hold_{}".format(mode)) is False:
                # Get next period key
                next_period_key = '{}NextPeriod'.format(mode.capitalize())
                # Get next period raw value
                next_period = self._device.raw_ui_data.get(next_period_key)
                # Get next period time
                hour, minute = divmod(next_period * 15, 60)
                # Set hold time
                setattr(self._device,
                        "hold_{}".format(mode),
                        datetime.time(hour, minute))
            # Set temperature
            setattr(self._device,
                    "setpoint_{}".format(mode),
                    temperature)
        except somecomfort.SomeComfortError:
            _LOGGER.error("Temperature %.1f out of range", temperature)

    @property
    def device_state_attributes(self) -> Dict:
        """Return the device specific state attributes."""
        data = {
            'fan': (self._device.fan_running and 'running' or 'idle'),
            'fan_mode': self._device.fan_mode,
            'operation_mode': self._device.system_mode,
        }
        return data

    def _turn_away_mode_on(self):
        """Turn away on.

        Somecomfort does have a proprietary away mode, but it doesn't really
        work the way it should. For example: If you set a temperature manually
        it doesn't get overwritten when away mode is switched on.
        """
        self._away = True
        try:
            # Get current mode
            mode = self._device.system_mode
        except somecomfort.SomeComfortError:
            _LOGGER.error('Can not get system mode')
            return
        try:

            # Set permanent hold
            setattr(self._device,
                    "hold_{}".format(mode),
                    True)
            # Set temperature
            setattr(self._device,
                    "setpoint_{}".format(mode),
                    getattr(self, "_{}_away_temp".format(mode)))
        except somecomfort.SomeComfortError:
            _LOGGER.error('Temperature %.1f out of range',
                          getattr(self, "_{}_away_temp".format(mode)))

    def _turn_away_mode_off(self):
        """Turn away off."""
        self._away = False
        try:
            # Disabling all hold modes
            self._device.hold_cool = False
            self._device.hold_heat = False
        except somecomfort.SomeComfortError:
            _LOGGER.error('Can not stop hold mode')

    def update(self):
        """Update the state."""
        retries = 3
        while retries > 0:
            try:
                self._device.refresh()
                break
            except (somecomfort.client.APIRateLimited, OSError,
                    requests.exceptions.ReadTimeout) as exp:
                retries -= 1
                if retries == 0:
                    raise exp
                if not self._retry():
                    raise exp
                _LOGGER.error(
                    "SomeComfort update failed, Retrying - Error: %s", exp)

    def _retry(self):
        """Recreate a new somecomfort client.

        When we got an error, the best way to be sure that the next query
        will succeed, is to recreate a new somecomfort client.
        """
        try:
            self._client = somecomfort.SomeComfort(
                self._username, self._password)
        except somecomfort.AuthError:
            _LOGGER.error("Failed to login to honeywell account %s",
                          self._username)
            return False
        except somecomfort.SomeComfortError as ex:
            _LOGGER.error("Failed to initialize honeywell client: %s",
                          str(ex))
            return False

        devices = [device
                   for location in self._client.locations_by_id.values()
                   for device in location.devices_by_id.values()
                   if device.name == self._device.name]

        if len(devices) != 1:
            _LOGGER.error("Failed to find device %s", self._device.name)
            return False

        self._device = devices[0]
        return True
