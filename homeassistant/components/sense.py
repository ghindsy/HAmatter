"""
Support for monitoring a Sense energy sensor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sense/
"""
import logging
import voluptuous as vol

from homeassistant.const import (CONF_EMAIL, CONF_PASSWORD, CONF_TIMEOUT)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['sense_energy==0.5.1']

_LOGGER = logging.getLogger(__name__)

SENSE_DATA = 'sense_data'

DOMAIN = 'sense'

ACTIVE_UPDATE_RATE = 30
DEFAULT_TIMEOUT = 5

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_TIMEOUT, DEFAULT_TIMEOUT): cv.positive_int,
    })
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Sense sensor."""
    from sense_energy import Senseable

    username = config[DOMAIN].get(CONF_EMAIL)
    password = config[DOMAIN].get(CONF_PASSWORD)

    timeout = config[DOMAIN].get(CONF_TIMEOUT)
    hass.data[SENSE_DATA] = Senseable(api_timeout=timeout, wss_timeout=timeout)
    hass.data[SENSE_DATA].authenticate(username, password)
    hass.data[SENSE_DATA].rate_limit = ACTIVE_UPDATE_RATE
    return True
