"""Support for Matrix notifications."""
import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import RoomID
from .const import DOMAIN, SERVICE_SEND_MESSAGE

CONF_DEFAULT_ROOM = "default_room"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_DEFAULT_ROOM): cv.string})


def get_service(hass: HomeAssistant, config: ConfigType, discovery_info=None):
    """Get the Matrix notification service."""
    return MatrixNotificationService(config[CONF_DEFAULT_ROOM])


class MatrixNotificationService(BaseNotificationService):
    """Send notifications to a Matrix room."""

    def __init__(self, default_room: RoomID) -> None:
        """Set up the Matrix notification service."""
        self._default_room = default_room

    def send_message(self, message: str = "", **kwargs):
        """Send the message to the Matrix server."""
        target_rooms = kwargs.get(ATTR_TARGET) or [self._default_room]
        service_data = {ATTR_TARGET: target_rooms, ATTR_MESSAGE: message}
        if (data := kwargs.get(ATTR_DATA)) is not None:
            service_data[ATTR_DATA] = data
        return self.hass.services.call(
            DOMAIN, SERVICE_SEND_MESSAGE, service_data=service_data
        )
