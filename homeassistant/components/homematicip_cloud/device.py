"""Generic device for the HomematicIP Cloud component."""
import logging

from homeassistant.components import homematicip_cloud
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

ATTR_CONNECTED = 'connected'
ATTR_DEVICE_ID = 'device_id'
ATTR_DEVICE_LABEL = 'device_label'
ATTR_DEVICE_RSSI = 'device_rssi'
ATTR_DUTY_CYCLE = 'duty_cycle'
ATTR_FIRMWARE_STATE = 'firmware_state'
ATTR_GROUP_TYPE = 'group_type'
ATTR_HOME_ID = 'home_id'
ATTR_HOME_NAME = 'home_name'
ATTR_LOW_BATTERY = 'low_battery'
ATTR_MODEL_TYPE = 'model_type'
ATTR_OPERATION_LOCK = 'operation_lock'
ATTR_SABOTAGE = 'sabotage'
ATTR_STATUS_UPDATE = 'status_update'
ATTR_UNREACHABLE = 'unreachable'
CONST_MANUFACTURER = 'eQ-3'


class HomematicipGenericDevice(Entity):
    """Representation of an HomematicIP generic device."""

    def __init__(self, home, device, post=None):
        """Initialize the generic device."""
        self._home = home
        self._device = device
        self.post = post
        _LOGGER.info("Setting up %s (%s)", self.name, self._device.modelType)

    @property
    def device_info(self):
        """Return device specific attributes."""
        # Only physical devices should be HA device.
        # Every HomematicIP device has a serial number,
        # that is stored in id property.
        if hasattr(self._device, 'id') and self._device.id is not None:
            identifier = self._device.id
        else:
            return None

        name = self._device.label \
            if hasattr(self._device, 'label') \
            else None
        manufacturer = self._device.oem \
            if hasattr(self._device, 'oem') \
            else CONST_MANUFACTURER
        model_type = self._device.modelType \
            if hasattr(self._device, 'modelType') \
            else None
        sw_version = self._device.firmwareVersion \
            if hasattr(self._device, 'firmwareVersion') \
            else None
        via_hub = self._device.homeId \
            if hasattr(self._device, 'homeId') \
            else None

        return {
            'identifiers': {
                # Serial numbers of Homematic IP device
                (homematicip_cloud.DOMAIN, identifier)
            },
            'name': name,
            'manufacturer': manufacturer,
            'model': model_type,
            'sw_version': sw_version,
            'via_hub': (homematicip_cloud.DOMAIN, via_hub),
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._device.on_update(self._device_changed)

    def _device_changed(self, *args, **kwargs):
        """Handle device state changes."""
        _LOGGER.debug("Event %s (%s)", self.name, self._device.modelType)
        self.async_schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the generic device."""
        name = self._device.label
        if self._home.name is not None and self._home.name != '':
            name = "{} {}".format(self._home.name, name)
        if self.post is not None and self.post != '':
            name = "{} {}".format(name, self.post)
        return name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def available(self):
        """Device available."""
        return not self._device.unreach

    @property
    def unique_id(self):
        """Return a unique ID."""
        return "{}_{}".format(self.__class__.__name__, self._device.id)

    @property
    def icon(self):
        """Return the icon."""
        if hasattr(self._device, 'lowBat') and self._device.lowBat:
            return 'mdi:battery-outline'
        if hasattr(self._device, 'sabotage') and self._device.sabotage:
            return 'mdi:alert'
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the generic device."""
        attr = {ATTR_MODEL_TYPE: self._device.modelType}
        if hasattr(self._device, 'lowBat') and self._device.lowBat:
            attr.update({ATTR_LOW_BATTERY: self._device.lowBat})
        if hasattr(self._device, 'sabotage') and self._device.sabotage:
            attr.update({ATTR_SABOTAGE: self._device.sabotage})
        return attr
