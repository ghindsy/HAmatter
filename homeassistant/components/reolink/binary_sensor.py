"""This component provides support for Reolink motion events."""
import asyncio
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import EVENT_DATA_RECEIVED
from .entity import ReolinkEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_CLASS = "motion"


@asyncio.coroutine
async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Reolink IP Camera switches."""
    sensor = motionSensor(hass, config_entry)
    async_add_devices([sensor], update_before_add=False)


class motionSensor(ReolinkEntity, BinarySensorEntity):
    """An implementation of a Reolink IP camera motion sensor."""

    def __init__(self, hass, config):
        """Initialize a the switch."""
        ReolinkEntity.__init__(self, hass, config)
        BinarySensorEntity.__init__(self)

        self._state = False

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"reolink_motion_{self._base.api.mac_address}"

    @property
    def name(self):
        """Return the name of this camera."""
        return f"{self._base.api.name} motion"

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._base.sman.renewTimer > 0

    @property
    def device_class(self):
        """Return the class of this device."""
        return DEFAULT_DEVICE_CLASS

    async def async_added_to_hass(self) -> None:
        """Entity created."""
        await super().async_added_to_hass()
        event_id = (
            f"{EVENT_DATA_RECEIVED}-{self._base.api.mac_address.replace(':', '')}"
        )
        self.hass.bus.async_listen(event_id, self.handle_event)

    async def handle_event(self, event):
        """Handle incoming webhook from Reolink for inbound messages and calls."""
        self._state = event.data["IsMotion"]
        self.async_schedule_update_ha_state()
