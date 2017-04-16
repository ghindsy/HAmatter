"""Support for the IKEA Tradfri platform."""

import logging


import voluptuous as vol

import homeassistant.util.color as color_util
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_RGB_COLOR, Light,
    PLATFORM_SCHEMA, SUPPORT_BRIGHTNESS, SUPPORT_RGB_COLOR)
from homeassistant.const import CONF_API_KEY, CONF_HOST
import homeassistant.helpers.config_validation as cv

SUPPORTED_FEATURES = (SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR)

# Home Assistant depends on 3rd party packages for API specific code.
REQUIREMENTS = ['pytradfri==0.4']

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_API_KEY): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the IKEA Tradfri Light platform."""
    import pytradfri

    # Assign configuration variables.
    host = config.get(CONF_HOST)
    securitycode = config.get(CONF_API_KEY)

    api = pytradfri.coap_cli.api_factory(host, securitycode)

    gateway = pytradfri.gateway.Gateway(api)
    devices = gateway.get_devices()
    lights = [dev for dev in devices if dev.has_light_control]

    _LOGGER.debug("IKEA Tradfri Hub | init | Initialization Process Complete")

    add_devices(IKEATradfri(light) for light in lights)
    _LOGGER.debug("IKEA Tradfri Hub | get_lights | All Lights Loaded")


class IKEATradfri(Light):
    """The platform class required by hass."""

    def __init__(self, light):
        """Initialize a Light."""
        self._light = light

        # Caching of LightControl and light object
        self._light_control = light.light_control
        self._light_data = light.light_control.lights[0]
        self._name = light.name

        self._brightness = None
        self._rgb_color = None

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORTED_FEATURES

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._light_data.state

    @property
    def brightness(self):
        """Brightness of the light (an integer in the range 1-255)."""
        return self._light_data.dimmer

    @property
    def rgb_color(self):
        """RGB color of the light."""
        return self._rgb_color

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        return self._light_control.set_state(False)

    def turn_on(self, **kwargs):
        """
        Instruct the light to turn on.

        After adding "self._light_data.hexcolor is not None"
        for ATTR_RGB_COLOR, this also supports Philips Hue bulbs.
        """
        if ATTR_BRIGHTNESS in kwargs:
            self._light.light_control.set_dimmer(kwargs.get(ATTR_BRIGHTNESS))
        if ATTR_RGB_COLOR in kwargs and self._light_data.hex_color is not None:
            self._light.light_control.set_hex_color(
                color_util.color_rgb_to_hex(*kwargs[ATTR_RGB_COLOR]))
        else:
            self._light.light_control.set_state(True)

    def update(self):
        """Fetch new state data for this light."""
        self._light.update()
        self._brightness = self._light_data.dimmer

        # Handle Hue lights paired with the gatway
        if self._light_data.hex_color is not None:
            self._rgb_color = color_util.rgb_hex_to_rgb_list(
                self._light_data.hex_color)
