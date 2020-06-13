"""Adds support for generic hygrostat units."""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.humidifier import PLATFORM_SCHEMA, HumidifierEntity
from homeassistant.components.humidifier.const import (
    ATTR_MODE,
    ATTR_HUMIDITY,
    DEVICE_CLASS_DEHUMIDIFIER,
    DEVICE_CLASS_HUMIDIFIER,
    SUPPORT_MODES,
    MODE_NORMAL,
    MODE_AWAY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, callback
from homeassistant.helpers import condition
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 0.3
DEFAULT_NAME = "Generic Hygrostat"

ATTR_SAVED_HUMIDITY = "saved_humidity"

CONF_HUMIDIFIER = "humidifier"
CONF_SENSOR = "target_sensor"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_TARGET_HUMIDITY = "target_humidity"
CONF_DEVICE_CLASS = "device_class"
CONF_MIN_DUR = "min_cycle_duration"
CONF_DRY_TOLERANCE = "dry_tolerance"
CONF_WET_TOLERANCE = "wet_tolerance"
CONF_KEEP_ALIVE = "keep_alive"
CONF_INITIAL_STATE = "initial_state"
CONF_AWAY_HUMIDITY = "away_humidity"
CONF_AWAY_FIXED = "away_fixed"
CONF_STALE_DURATION = "sensor_stale_duration"

SUPPORT_FLAGS = 0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HUMIDIFIER): cv.entity_id,
        vol.Required(CONF_SENSOR): cv.entity_id,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(
            [DEVICE_CLASS_HUMIDIFIER, DEVICE_CLASS_DEHUMIDIFIER]
        ),
        vol.Optional(CONF_MAX_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_MIN_DUR): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DRY_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_WET_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_TARGET_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_KEEP_ALIVE): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_INITIAL_STATE): cv.boolean,
        vol.Optional(CONF_AWAY_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_AWAY_FIXED): cv.boolean,
        vol.Optional(CONF_STALE_DURATION): vol.All(
            cv.time_period, cv.positive_timedelta
        ),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the generic hygrostat platform."""
    name = config.get(CONF_NAME)
    switch_entity_id = config.get(CONF_HUMIDIFIER)
    sensor_entity_id = config.get(CONF_SENSOR)
    min_humidity = config.get(CONF_MIN_HUMIDITY)
    max_humidity = config.get(CONF_MAX_HUMIDITY)
    target_humidity = config.get(CONF_TARGET_HUMIDITY)
    device_class = config.get(CONF_DEVICE_CLASS)
    min_cycle_duration = config.get(CONF_MIN_DUR)
    sensor_stale_duration = config.get(CONF_STALE_DURATION)
    dry_tolerance = config.get(CONF_DRY_TOLERANCE)
    wet_tolerance = config.get(CONF_WET_TOLERANCE)
    keep_alive = config.get(CONF_KEEP_ALIVE)
    initial_state = config.get(CONF_INITIAL_STATE)
    away_humidity = config.get(CONF_AWAY_HUMIDITY)
    away_fixed = config.get(CONF_AWAY_FIXED)

    async_add_entities(
        [
            GenericHygrostat(
                name,
                switch_entity_id,
                sensor_entity_id,
                min_humidity,
                max_humidity,
                target_humidity,
                device_class,
                min_cycle_duration,
                dry_tolerance,
                wet_tolerance,
                keep_alive,
                initial_state,
                away_humidity,
                away_fixed,
                sensor_stale_duration,
            )
        ]
    )


class GenericHygrostat(HumidifierEntity, RestoreEntity):
    """Representation of a Generic Hygrostat device."""

    def __init__(
        self,
        name,
        switch_entity_id,
        sensor_entity_id,
        min_humidity,
        max_humidity,
        target_humidity,
        device_class,
        min_cycle_duration,
        dry_tolerance,
        wet_tolerance,
        keep_alive,
        initial_state,
        away_humidity,
        away_fixed,
        sensor_stale_duration,
    ):
        """Initialize the hygrostat."""
        self._name = name
        self._switch_entity_id = switch_entity_id
        self._sensor_entity_id = sensor_entity_id
        self._device_class = device_class
        self._min_cycle_duration = min_cycle_duration
        self._dry_tolerance = dry_tolerance
        self._wet_tolerance = wet_tolerance
        self._keep_alive = keep_alive
        self._state = initial_state
        self._saved_target_humidity = target_humidity or away_humidity
        self._active = False
        self._cur_humidity = None
        self._humidity_lock = asyncio.Lock()
        self._min_humidity = min_humidity
        self._max_humidity = max_humidity
        self._target_humidity = target_humidity
        self._support_flags = SUPPORT_FLAGS
        if away_humidity:
            self._support_flags = SUPPORT_FLAGS | SUPPORT_MODES
        self._away_humidity = away_humidity
        self._away_fixed = away_fixed
        self._sensor_stale_duration = sensor_stale_duration
        self._is_away = False
        if not self._device_class:
            self._device_class = DEVICE_CLASS_HUMIDIFIER

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        async_track_state_change(
            self.hass, self._sensor_entity_id, self._async_sensor_changed
        )
        async_track_state_change(
            self.hass, self._switch_entity_id, self._async_switch_changed
        )

        if self._sensor_stale_duration:
            async_track_time_interval(
                self.hass,
                self._async_check_sensor_not_responding,
                self._sensor_stale_duration,
            )

        if self._keep_alive:
            async_track_time_interval(self.hass, self._async_operate, self._keep_alive)

        @callback
        async def _async_startup(event):
            """Init on startup."""
            sensor_state = self.hass.states.get(self._sensor_entity_id)
            if sensor_state:
                await self._async_update_humidity(sensor_state)
                await self.async_update_ha_state()

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

        # Check If we have an old state
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if old_state.attributes.get(ATTR_MODE) == MODE_AWAY:
                self._is_away = True
            # If we have no initial humidity, restore
            if self._target_humidity is None:
                # If we have a previously saved humidity
                if old_state.attributes.get(ATTR_HUMIDITY) is None:
                    if self._device_class == DEVICE_CLASS_HUMIDIFIER:
                        self._target_humidity = self.min_humidity
                    else:
                        self._target_humidity = self.max_humidity
                    _LOGGER.warning(
                        "Undefined target humidity," "falling back to %s",
                        self._target_humidity,
                    )
                else:
                    self._target_humidity = float(old_state.attributes[ATTR_HUMIDITY])
            elif self._is_away:
                self._saved_target_humidity = self._target_humidity
                if old_state.attributes.get(ATTR_HUMIDITY):
                    self._target_humidity = float(
                        old_state.attributes.get(ATTR_HUMIDITY)
                    )
                else:
                    self._target_humidity = self._away_humidity
            if old_state.attributes.get(ATTR_SAVED_HUMIDITY):
                self._saved_target_humidity = float(
                    old_state.attributes[ATTR_SAVED_HUMIDITY]
                )
            if not self._state and old_state.state:
                self._state = old_state.state == STATE_ON

        else:
            # No previous state, try and restore defaults
            if self._target_humidity is None:
                if self._device_class == DEVICE_CLASS_HUMIDIFIER:
                    self._target_humidity = self.min_humidity
                else:
                    self._target_humidity = self.max_humidity
            _LOGGER.warning(
                "No previously saved humidity, setting to %s", self._target_humidity
            )

        # Set default state to off
        if not self._state:
            self._state = False

        await _async_startup(None)  # init the sensor

    @property
    def state(self):
        """Return unknown state on sensor error."""
        if self._state is None:
            return STATE_UNKNOWN
        return super().state

    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        data = super().state_attributes

        if self._saved_target_humidity:
            data[ATTR_SAVED_HUMIDITY] = self._saved_target_humidity

        return data

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the hygrostat."""
        return self._name

    @property
    def is_on(self):
        """Return true if the hygrostat is on."""
        return self._state

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return self._target_humidity

    @property
    def mode(self):
        """Return the current mode."""
        if self._away_humidity is None:
            return None
        if self._is_away:
            return MODE_AWAY
        return MODE_NORMAL

    @property
    def available_modes(self):
        """Return a list of available modes."""
        if self._away_humidity:
            return [MODE_NORMAL, MODE_AWAY]
        return None

    @property
    def device_class(self):
        """Return the device class of the humidifier."""
        return self._device_class

    async def async_turn_on(self):
        """Turn hygrostat on."""
        if self._state is None:
            return
        self._state = True
        await self._async_operate(force=True)
        await self.async_update_ha_state()

    async def async_turn_off(self):
        """Turn hygrostat off."""
        if self._state is None:
            return
        self._state = False
        if self._is_device_active:
            await self._async_device_turn_off()
        await self.async_update_ha_state()

    async def async_set_humidity(self, humidity: int):
        """Set new target humidity."""
        if humidity is None:
            return

        if self._is_away and self._away_fixed:
            self._saved_target_humidity = humidity
            await self.async_update_ha_state()
            return

        self._target_humidity = humidity
        await self._async_operate(force=True)
        await self.async_update_ha_state()

    @property
    def min_humidity(self):
        """Return the minimum humidity."""
        if self._min_humidity:
            return self._min_humidity

        # get default humidity from super class
        return super().min_humidity

    @property
    def max_humidity(self):
        """Return the maximum humidity."""
        if self._max_humidity:
            return self._max_humidity

        # Get default humidity from super class
        return super().max_humidity

    async def _async_sensor_changed(self, entity_id, old_state, new_state):
        """Handle ambient humidity changes."""
        if new_state is None:
            return

        await self._async_update_humidity(new_state)
        await self._async_operate()
        await self.async_update_ha_state()

    async def _async_check_sensor_not_responding(self, now=None):
        """Check if the sensor has emitted a value during the allowed stale period."""

        sensor_state = self.hass.states.get(self._sensor_entity_id)

        if sensor_state.last_updated < now - self._sensor_stale_duration:
            _LOGGER.debug("Time is %s, last changed is %s, stale duration is %s")
            _LOGGER.warning("Sensor is stalled, call the emergency stop")
            self._state = None
            if self._is_device_active:
                await self._async_device_turn_off()

        return

    @callback
    def _async_switch_changed(self, entity_id, old_state, new_state):
        """Handle humidifier switch state changes."""
        if new_state is None:
            return
        self.async_schedule_update_ha_state()

    @callback
    async def _async_update_humidity(self, state):
        """Update hygrostat with latest state from sensor."""
        try:
            self._cur_humidity = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)
            self._state = None
            if self._is_device_active:
                await self._async_device_turn_off()

    async def _async_operate(self, time=None, force=False):
        """Check if we need to turn humidifying on or off."""
        async with self._humidity_lock:
            if not self._active and None not in (
                self._cur_humidity,
                self._target_humidity,
                self._state,
            ):
                self._active = True
                _LOGGER.info(
                    "Obtained current and target humidity. "
                    "Generic hygrostat active. %s, %s",
                    self._cur_humidity,
                    self._target_humidity,
                )

            if not self._active or not self._state:
                return

            if not force and time is None:
                # If the `force` argument is True, we
                # ignore `min_cycle_duration`.
                # If the `time` argument is not none, we were invoked for
                # keep-alive purposes, and `min_cycle_duration` is irrelevant.
                if self._min_cycle_duration:
                    if self._is_device_active:
                        current_state = STATE_ON
                    else:
                        current_state = STATE_OFF
                    long_enough = condition.state(
                        self.hass,
                        self._switch_entity_id,
                        current_state,
                        self._min_cycle_duration,
                    )
                    if not long_enough:
                        return

            too_dry = self._target_humidity - self._cur_humidity >= self._dry_tolerance
            too_wet = self._cur_humidity - self._target_humidity >= self._wet_tolerance
            if self._is_device_active:
                if (self._device_class == DEVICE_CLASS_HUMIDIFIER and too_wet) or (
                    self._device_class == DEVICE_CLASS_DEHUMIDIFIER and too_dry
                ):
                    _LOGGER.info("Turning off humidifier %s", self._switch_entity_id)
                    await self._async_device_turn_off()
                elif time is not None:
                    # The time argument is passed only in keep-alive case
                    await self._async_device_turn_on()
            else:
                if (self._device_class == DEVICE_CLASS_HUMIDIFIER and too_dry) or (
                    self._device_class == DEVICE_CLASS_DEHUMIDIFIER and too_wet
                ):
                    _LOGGER.info("Turning on humidifier %s", self._switch_entity_id)
                    await self._async_device_turn_on()
                elif time is not None:
                    # The time argument is passed only in keep-alive case
                    await self._async_device_turn_off()

    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        return self.hass.states.is_state(self._switch_entity_id, STATE_ON)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    async def _async_device_turn_on(self):
        """Turn humidifier toggleable device on."""
        data = {ATTR_ENTITY_ID: self._switch_entity_id}
        await self.hass.services.async_call(HA_DOMAIN, SERVICE_TURN_ON, data)

    async def _async_device_turn_off(self):
        """Turn humidifier toggleable device off."""
        data = {ATTR_ENTITY_ID: self._switch_entity_id}
        await self.hass.services.async_call(HA_DOMAIN, SERVICE_TURN_OFF, data)

    async def async_set_mode(self, mode: str):
        """Set new mode.

        This method must be run in the event loop and returns a coroutine.
        """
        if self._away_humidity is None:
            return
        if mode == MODE_AWAY and not self._is_away:
            self._is_away = True
            if not self._saved_target_humidity:
                self._saved_target_humidity = self._away_humidity
            self._saved_target_humidity, self._target_humidity = (
                self._target_humidity,
                self._saved_target_humidity,
            )
            await self._async_operate(force=True)
        elif mode == MODE_NORMAL and self._is_away:
            self._is_away = False
            self._saved_target_humidity, self._target_humidity = (
                self._target_humidity,
                self._saved_target_humidity,
            )
            await self._async_operate(force=True)

        await self.async_update_ha_state()
