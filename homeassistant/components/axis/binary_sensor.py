"""Support for Axis binary sensors."""
from datetime import timedelta

from homeassistant.components.axis.const import DOMAIN as AXIS_DOMAIN, LOGGER
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.const import CONF_MAC, CONF_TRIGGER_TIME
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow

DEPENDENCIES = [AXIS_DOMAIN]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up a Axis binary sensor."""
    serial_number = config_entry.data[CONF_MAC]
    device = hass.data[AXIS_DOMAIN][serial_number]

    @callback
    def async_add_sensor(event):
        """Add binary sensor from Axis device."""
        async_add_entities([AxisBinarySensor(event, device)], True)

    device.listeners.append(
        async_dispatcher_connect(hass, 'axis_add_sensor', async_add_sensor))


class AxisBinarySensor(BinarySensorDevice):
    """Representation of a binary Axis event."""

    def __init__(self, event, device):
        """Initialize the Axis binary sensor."""
        self.axis_event = event
        self.device = device
        self.delay = device.config_entry.data[CONF_TRIGGER_TIME]
        self.remove_timer = None

    async def async_added_to_hass(self):
        """Subscribe sensors events."""
        self.axis_event.callback = self.update_callback

    def update_callback(self):
        """Update the sensor's state, if needed."""
        if self.remove_timer is not None:
            self.remove_timer()
            self.remove_timer = None

        if self.delay == 0 or self.is_on:
            self.schedule_update_ha_state()
            return

        @callback
        def _delay_update(now):
            """Timer callback for sensor update."""
            LOGGER.debug(
                "%s called delayed (%s sec) update", self.name, self.delay)
            self.async_schedule_update_ha_state()
            self.remove_timer = None

        self.remove_timer = async_track_point_in_utc_time(
            self.hass, _delay_update,
            utcnow() + timedelta(seconds=self.delay))

    @property
    def is_on(self):
        """Return true if event is active."""
        return self.axis_event.is_tripped

    @property
    def name(self):
        """Return the name of the event."""
        return '{} {} {}'.format(
            self.device.name, self.axis_event.event_type, self.axis_event.id)

    @property
    def device_class(self):
        """Return the class of the event."""
        return self.axis_event.event_class

    @property
    def should_poll(self):
        """No polling needed."""
        return False
