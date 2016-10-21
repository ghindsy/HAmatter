"""
Notifications for Android TV notification service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.nfandroidtv/
"""
import logging
import requests
import os
import voluptuous as vol

from homeassistant.components.notify import (ATTR_TITLE,
                                             ATTR_TITLE_DEFAULT,
                                             ATTR_DATA,
                                             BaseNotificationService,
                                             PLATFORM_SCHEMA)
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_IP = 'ip'
CONF_DURATION = 'duration'
CONF_POSITION = 'position'
CONF_TRANSPARENCY = 'transparency'
CONF_COLOR = 'color'
CONF_INTERRUPT = 'interrupt'
CONF_TIMEOUT = 'timeout'

DEFAULT_DURATION = 5
DEFAULT_POSITION = 'bottom-right'
DEFAULT_TRANSPARENCY = 'default'
DEFAULT_COLOR = 'grey'
DEFAULT_INTERRUPT = False
DEFAULT_TIMEOUT = 5

ATTR_DURATION = 'duration'
ATTR_POSITION = 'position'
ATTR_TRANSPARENCY = 'transparency'
ATTR_COLOR = 'color'
ATTR_BKGCOLOR = 'bkgcolor'
ATTR_INTERRUPT = 'interrupt'

POSITIONS = {
    "bottom-right": 0,
    "bottom-left": 1,
    "top-right": 2,
    "top-left": 3,
    "center": 4,
}

TRANSPARENCIES = {
    "default": 0,
    "0%": 1,
    "25%": 2,
    "50%": 3,
    "75%": 4,
    "100%": 5,
}

COLORS = {
    "grey": "#607d8b",
    "black": "#000000",
    "indigo": "#303F9F",
    "green": "#4CAF50",
    "red": "#F44336",
    "cyan": "#00BCD4",
    "teal": "#009688",
    "amber": "#FFC107",
    "pink": "#E91E63",
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP): cv.string,
    vol.Optional(CONF_DURATION, default=DEFAULT_DURATION): vol.Coerce(int),
    vol.Optional(CONF_POSITION, default=DEFAULT_POSITION):
        vol.In(POSITIONS.keys()),
    vol.Optional(CONF_TRANSPARENCY, default=DEFAULT_TRANSPARENCY):
        vol.In(TRANSPARENCIES.keys()),
    vol.Optional(CONF_COLOR, default=DEFAULT_COLOR):
        vol.In(COLORS.keys()),
    vol.Optional(CONF_COLOR, default=DEFAULT_COLOR): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(int),
    vol.Optional(CONF_INTERRUPT, default=DEFAULT_INTERRUPT): cv.boolean,
})


def get_service(hass, config):
    """Get the Notifications for Android TV notification service."""
    ip = config.get(CONF_IP)
    duration = config.get(CONF_DURATION)
    position = config.get(CONF_POSITION)
    transparency = config.get(CONF_TRANSPARENCY)
    color = config.get(CONF_COLOR)
    interrupt = config.get(CONF_INTERRUPT)
    timeout = config.get(CONF_TIMEOUT)

    return NFAndroidTVNotificationService(ip,
                                          duration,
                                          position,
                                          transparency,
                                          color,
                                          interrupt,
                                          timeout)


# pylint: disable=too-few-public-methods
class NFAndroidTVNotificationService(BaseNotificationService):
    """Notification service for Notifications for Android TV."""

    def __init__(self, ip, duration, position, transparency,
                 color, interrupt, timeout):
        """Initialize the service."""
        self._target = "http://%s:7676" % ip
        self._default_duration = duration
        self._default_position = position
        self._default_transparency = transparency
        self._default_color = color
        self._default_interrupt = interrupt
        self._timeout = timeout
        self._icon_file = os.path.join(os.path.dirname(__file__), "..",
                                       "frontend",
                                       "www_static", "icons",
                                       "favicon-192x192.png")

    def send_message(self, message="", **kwargs):
        """Send a message to a Android TV device."""
        _LOGGER.debug("Sending notification to: %s", self._target)

        payload = dict(filename=('icon.png',
                                 open(self._icon_file, 'rb'),
                                 'application/octet-stream',
                                 {'Expires': '0'}), type="0",
                       title=kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT),
                       msg=message, duration="%i" % self._default_duration,
                       position="%i" % POSITIONS.get(self._default_position),
                       bkgcolor="%s" % COLORS.get(self._default_color),
                       transparency="%i" % TRANSPARENCIES.get(
                               self._default_transparency), offset="0",
                       app=ATTR_TITLE_DEFAULT, force="true",
                       interrupt="%i" % self._default_interrupt)

        data = kwargs.get(ATTR_DATA)
        if data:
            if ATTR_DURATION in data:
                d = data.get(ATTR_DURATION)
                try:
                    payload[ATTR_DURATION] = "%i" % int(d)
                except ValueError:
                    _LOGGER.warning("Invalid duration-value: %s", str(d))
            if ATTR_POSITION in data:
                p = data.get(ATTR_POSITION)
                if p in POSITIONS:
                    payload[ATTR_POSITION] = "%i" % POSITIONS.get(p)
                else:
                    _LOGGER.warning("Invalid position-value: %s", str(p))
            if ATTR_TRANSPARENCY in data:
                t = data.get(ATTR_TRANSPARENCY)
                if t in TRANSPARENCIES:
                    payload[ATTR_TRANSPARENCY] = "%i" % TRANSPARENCIES.get(t)
                else:
                    _LOGGER.warning("Invalid transparency-value: %s", str(t))
            if ATTR_COLOR in data:
                c = data.get(ATTR_COLOR)
                if c in COLORS:
                    payload[ATTR_BKGCOLOR] = "%s" % COLORS.get(c)
                else:
                    _LOGGER.warning("Invalid color-value: %s", str(c))
            if ATTR_INTERRUPT in data:
                i = data.get(ATTR_INTERRUPT)
                try:
                    payload[ATTR_INTERRUPT] = "%i" % cv.boolean(i)
                except vol.Invalid:
                    _LOGGER.warning("Invalid interrupt-value: %s", str(i))

        try:
            _LOGGER.debug("Payload: %s", str(payload))
            response = requests.post(self._target,
                                     files=payload,
                                     timeout=self._timeout)
            if response.status_code != 200:
                _LOGGER.error("Error sending message: %s", str(response))
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("Error communicating with %s: %s",
                          self._target, str(e))