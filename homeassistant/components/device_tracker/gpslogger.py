"""
Support for the GPSLogger platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.gpslogger/
"""
import asyncio
from functools import partial
import logging

from aiohttp.web import Request, HTTPUnauthorized  # NOQA
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_PASSWORD, HTTP_UNPROCESSABLE_ENTITY
)
from homeassistant.components.http import (
    CONF_API_PASSWORD, HomeAssistantView
)
# pylint: disable=unused-import
from homeassistant.components.device_tracker import (  # NOQA
    DOMAIN, PLATFORM_SCHEMA
)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['http']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_PASSWORD): cv.string,
})


def setup_scanner(hass, config, see, _discovery_info=None):
    """Set up an endpoint for the GPSLogger application."""
    hass.http.register_view(GPSLoggerView(see, config))

    return True


class GPSLoggerView(HomeAssistantView):
    """View to handle GPSLogger requests."""

    url = '/api/gpslogger'
    name = 'api:gpslogger'

    def __init__(self, see, config):
        """Initialize GPSLogger url endpoints."""
        self.see = see
        self._password = config.get(CONF_PASSWORD)
        # this component does not require external authentication if
        # password is set
        self.requires_auth = self._password is None

    @asyncio.coroutine
    def get(self, request: Request):
        """Handle for GPSLogger message received as GET."""
        res = yield from self._handle(request.app['hass'], request)
        return res

    @asyncio.coroutine
    def _handle(self, hass, request: Request):
        """Handle GPSLogger requests."""
        data = request.query

        if self._password is not None:
            from hmac import compare_digest
            authenticated = CONF_API_PASSWORD in data and compare_digest(
                self._password,
                data[CONF_API_PASSWORD]
            )
            if not authenticated:
                raise HTTPUnauthorized()

        if 'latitude' not in data or 'longitude' not in data:
            return ('Latitude and longitude not specified.',
                    HTTP_UNPROCESSABLE_ENTITY)

        if 'device' not in data:
            _LOGGER.error("Device id not specified")
            return ('Device id not specified.',
                    HTTP_UNPROCESSABLE_ENTITY)

        device = data['device'].replace('-', '')
        gps_location = (data['latitude'], data['longitude'])
        accuracy = 200
        battery = -1

        if 'accuracy' in data:
            accuracy = int(float(data['accuracy']))
        if 'battery' in data:
            battery = float(data['battery'])

        attrs = {}
        if 'speed' in data:
            attrs['speed'] = float(data['speed'])
        if 'direction' in data:
            attrs['direction'] = float(data['direction'])
        if 'altitude' in data:
            attrs['altitude'] = float(data['altitude'])
        if 'provider' in data:
            attrs['provider'] = data['provider']
        if 'activity' in data:
            attrs['activity'] = data['activity']

        yield from hass.async_add_job(
            partial(self.see, dev_id=device,
                    gps=gps_location, battery=battery,
                    gps_accuracy=accuracy,
                    attributes=attrs))

        return 'Setting location for {}'.format(device)
