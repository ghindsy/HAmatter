"""
Support for ZhongHong HVAC Controller.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.zhong_hong/
"""
import logging

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_OPERATION_MODE, PLATFORM_SCHEMA, STATE_COOL, STATE_DRY,
    STATE_FAN_ONLY, STATE_HEAT, SUPPORT_FAN_MODE, SUPPORT_ON_OFF,
    SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE, ClimateDevice)
from homeassistant.const import (
    ATTR_TEMPERATURE, CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP, TEMP_CELSIUS)
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_GATEWAY_ADDRRESS = 'gateway_address'

REQUIREMENTS = ['zhong_hong_hvac==1.0.9']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST):
    cv.string,
    vol.Optional(CONF_PORT, default=9999):
    vol.Coerce(int),
    vol.Optional(CONF_GATEWAY_ADDRRESS, default=1):
    vol.Coerce(int),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZhongHong HVAC platform."""
    from zhong_hong_hvac.hub import ZhongHongGateway
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    gw_addr = config.get(CONF_GATEWAY_ADDRRESS)
    hub = ZhongHongGateway(host, port, gw_addr)
    try:
        devices = [
            ZhongHongClimate(hub, addr_out, addr_in)
            for (addr_out, addr_in) in hub.discovery_ac()
        ]
    except Exception as exc:
        _LOGGER.error("ZhongHong controller is not ready", exc_info=exc)
        raise PlatformNotReady

    def startup(event):
        """Add devices to HA and start hub socket."""
        add_devices(devices)
        hub.start_listen()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, startup)

    def stop_listen(event):
        """Stop ZhongHongHub socket."""
        hub.stop_listen()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_listen)


class ZhongHongClimate(ClimateDevice):
    """Representation of a ZhongHong controller support HVAC."""

    def __init__(self, hub, addr_out, addr_in):
        """Set up the ZhongHong climate devices."""
        from zhong_hong_hvac.hvac import HVAC
        self._device = HVAC(hub, addr_out, addr_in)
        self._hub = hub
        self._current_operation = None
        self._current_temperature = None
        self._target_temperature = None
        self._current_fan_mode = None
        self._is_on = None

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._device.register_update_callback(self._after_update)
        await self.hass.async_add_job(self.update)

    def update(self):
        """Update device status from hub."""
        self._device.update()

    def _after_update(self, climate):
        """Callback to update state."""
        _LOGGER.debug("async update ha state")
        if self._device.current_operation:
            self._current_operation = self._device.current_operation.lower()
        if self._device.current_temperature:
            self._current_temperature = self._device.current_temperature
        if self._device.current_fan_mode:
            self._current_fan_mode = self._device.current_fan_mode
        if self._device.target_temperature:
            self._target_temperature = self._device.target_temperature
        self._is_on = self._device.is_on
        self.schedule_update_ha_state()

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self.unique_id

    @property
    def unique_id(self):
        """Return the unique ID of the HVAC."""
        return "zhong_hong_hvac_{}_{}".format(self._device.addr_out,
                                              self._device.addr_in)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
                | SUPPORT_OPERATION_MODE | SUPPORT_ON_OFF)

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return [STATE_COOL, STATE_HEAT, STATE_DRY, STATE_FAN_ONLY]

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def is_on(self):
        """Return true if on."""
        return self._device.is_on

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return self._device.fan_list

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._device.min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._device.max_temp

    def turn_on(self):
        """Turn on ac."""
        return self._device.turn_on()

    def turn_off(self):
        """Turn off ac."""
        return self._device.turn_off()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._device.set_temperature(temperature)

        operation_mode = kwargs.get(ATTR_OPERATION_MODE)
        if operation_mode is not None:
            self._device.set_operation_mode(operation_mode)

    def set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        self._device.set_operation_mode(operation_mode.upper())

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        self._device.set_fan_mode(fan_mode)
