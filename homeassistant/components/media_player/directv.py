"""
Support for the DirecTV receivers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.directv/
"""
import logging
from datetime import timedelta
from functools import partial
import requests
import voluptuous as vol

from homeassistant.components.media_player import (
    MEDIA_TYPE_CHANNEL, MEDIA_TYPE_MOVIE, MEDIA_TYPE_TVSHOW, PLATFORM_SCHEMA,
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_TURN_ON,
    MediaPlayerDevice)
from homeassistant.const import (
    CONF_DEVICE, CONF_HOST, CONF_NAME, CONF_PORT, EVENT_HOMEASSISTANT_START,
    STATE_OFF, STATE_PAUSED, STATE_PLAYING)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

REQUIREMENTS = ['directpy==0.5']

_LOGGER = logging.getLogger(__name__)

ATTR_MEDIA_CURRENTLY_RECORDING = 'media_currently_recording'
ATTR_MEDIA_RATING = 'media_rating'
ATTR_MEDIA_RECORDED = 'media_recorded'
ATTR_MEDIA_START_TIME = 'media_start_time'

CONF_DISCOVER_CLIENTS = 'discover_clients'
CONF_CLIENT_DISCOVER_INTERVAL = 'client_discover_interval'

DEFAULT_DEVICE = '0'
DEFAULT_DISCOVER_CLIENTS = True
DEFAULT_NAME = "DirecTV Receiver"
DEFAULT_PORT = 8080
DEFAULT_CLIENT_DISCOVER_INTERVAL = timedelta(seconds=300)

SUPPORT_DTV = SUPPORT_PAUSE | SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
    SUPPORT_PLAY_MEDIA | SUPPORT_STOP | SUPPORT_NEXT_TRACK | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_PLAY

SUPPORT_DTV_CLIENT = SUPPORT_PAUSE | \
    SUPPORT_PLAY_MEDIA | SUPPORT_STOP | SUPPORT_NEXT_TRACK | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_PLAY

DATA_DIRECTV = 'data_directv'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
    vol.Optional(CONF_DISCOVER_CLIENTS, default=DEFAULT_DISCOVER_CLIENTS):
        cv.boolean,
    vol.Optional(CONF_CLIENT_DISCOVER_INTERVAL,
                 default=DEFAULT_CLIENT_DISCOVER_INTERVAL):
        cv.time_period,
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the DirecTV platform."""
    known_devices = hass.data.get(DATA_DIRECTV, set())
    directv_entity = None

    if CONF_HOST in config:
        discovered = False
        _LOGGER.debug("Adding configured device %s with client address %s ",
                      config.get(CONF_NAME), config.get(CONF_DEVICE))
        directv_entity = {
            CONF_NAME: config.get(CONF_NAME),
            CONF_HOST: config.get(CONF_HOST),
            CONF_PORT: config.get(CONF_PORT),
            CONF_DEVICE: config.get(CONF_DEVICE),
            CONF_DISCOVER_CLIENTS: config.get(CONF_DISCOVER_CLIENTS),
            CONF_CLIENT_DISCOVER_INTERVAL: config.get(
                CONF_CLIENT_DISCOVER_INTERVAL),
        }

    elif discovery_info:
        discovered = True
        host = discovery_info.get('host')
        name = 'DirecTV_{}'.format(discovery_info.get('serial', ''))
        resp = []

        if (host, DEFAULT_DEVICE) in known_devices:
            _LOGGER.debug("Discovered device on host %s is already"
                          " configured", host)
            return

        from DirectPy import DIRECTV
        try:
            dtv = await hass.async_add_executor_job(
                DIRECTV, host, DEFAULT_PORT, DEFAULT_DEVICE)
        except requests.exceptions.RequestException as ex:
            # Use uPnP data only
            _LOGGER.debug("Request exception %s trying to connect to %s",
                          ex, name)
            resp = []

        if dtv:
            try:
                resp = await hass.async_add_executor_job(
                    dtv.get_locations)
            except requests.exceptions.RequestException as ex:
                # Use uPnP data only
                _LOGGER.debug("Request exception %s trying to get "
                              "locations for %s", ex, name)
                resp = []

        for loc in resp.get("locations") or []:
            if loc.get("clientAddr") == DEFAULT_DEVICE and \
               "locationName" in loc:
                name = str.title(loc["locationName"])
                break

        _LOGGER.debug("Adding discovered device %s on host %s",
                      name, host)
        directv_entity = {
            CONF_NAME: name,
            CONF_HOST: host,
            CONF_PORT: DEFAULT_PORT,
            CONF_DEVICE: DEFAULT_DEVICE,
            CONF_DISCOVER_CLIENTS: DEFAULT_DISCOVER_CLIENTS,
            CONF_CLIENT_DISCOVER_INTERVAL:
                DEFAULT_CLIENT_DISCOVER_INTERVAL,
        }

    if directv_entity is not None:
        hass.data.setdefault(DATA_DIRECTV, set()).add((
            directv_entity[CONF_HOST], directv_entity[CONF_DEVICE]))

        async_add_entities([DirecTvDevice(**directv_entity)])

        # Only enable client discovery if not disabled in configuration
        # and this is the main DVR (not a client device itself).
        if directv_entity[CONF_DISCOVER_CLIENTS] and \
           directv_entity[CONF_DEVICE] == DEFAULT_DEVICE:
            # Client discovery is to be enabled for this DVR.
            DirecTvClientDiscovery(
                hass, async_add_entities, discovered,
                directv_entity[CONF_HOST], directv_entity[CONF_NAME],
                directv_entity[CONF_PORT],
                directv_entity[CONF_CLIENT_DISCOVER_INTERVAL]
            )


class DirecTvClientDiscovery():
    """Discover client devices attached to DVR."""

    def __init__(self, hass, async_add_entities, discovered, host, name,
                 port=DEFAULT_PORT, interval=DEFAULT_CLIENT_DISCOVER_INTERVAL):
        """Initialize discovery for client devices."""
        self._hass = hass
        self._async_add_entities = async_add_entities
        self._discovered = discovered
        self._host = host
        self._name = name if name else host
        self._port = port

        self.dtv = None

        # Client discovery to be started once HASS is started to ensure
        # all configured devices have been added first.
        @callback
        def async_client_discovery_startup(event):
            # Create task to perform already perform a discovery if the main
            # entity was discovered as well or HASS started.
            if self._discovered or event:
                self._hass.async_create_task(
                    self._async_discover_directv_client_devices()
                )

            # Schedule discovery to run based on interval.
            async_track_time_interval(
                self._hass, self._async_discover_directv_client_devices,
                interval)
            _LOGGER.debug("%s: Client discovery scheduled for every %s",
                          self._name, interval)

        # If HASS is already running then start the discovery.
        # If HASS is not yet running, register for the event before starting
        # the discovery.
        if self._hass.is_running:
            async_client_discovery_startup(None)
        else:
            self._hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, async_client_discovery_startup)

    async def _async_discover_directv_client_devices(self, now=None):
        """Discover new client devices connected to the main DVR."""
        known_devices = self._hass.data.get(DATA_DIRECTV, set())
        discovered_devices = []
        dtvs = []

        # Attempt to discover additional RVU units
        if now:
            _LOGGER.debug("%s: Scheduled discovery of DirecTV devices on %s",
                          self._name, self._host)
        else:
            _LOGGER.debug("%s: Initial discovery of DirecTV devices on %s",
                          self._name, self._host)

        _LOGGER.debug("%s: Current known devices: %s",
                      self._name, known_devices)

        if not self.dtv:
            from DirectPy import DIRECTV
            try:
                self.dtv = await self._hass.async_add_executor_job(
                    DIRECTV, self._host, self._port, DEFAULT_DEVICE)
            except requests.exceptions.RequestException as ex:
                # Use uPnP data only
                _LOGGER.debug("%s: Request exception %s trying to get "
                              "locations", self._name, ex)
                self.dtv = None

        if not self.dtv:
            return

        try:
            resp = await self._hass.async_add_executor_job(
                self.dtv.get_locations)
        except requests.exceptions.RequestException as ex:
            # Use uPnP data only
            _LOGGER.debug("%s: Request exception %s trying to get "
                          "locations", self._name, ex)
            resp = None

        if not resp:
            return

        for loc in resp.get('locations') or []:
            if 'locationName' not in loc or 'clientAddr' not in loc or\
               loc.get('clientAddr') == DEFAULT_DEVICE:
                continue

            # Make sure that this device is not already configured
            # Comparing based on host (IP) and clientAddr.
            if (self._host, loc['clientAddr']) in known_devices:
                _LOGGER.debug("%s: Discovered device %s on host %s with "
                              "client address %s is already "
                              "configured",
                              self._name,
                              str.title(loc['locationName']),
                              self._host, loc['clientAddr'])
            else:
                _LOGGER.debug("%s: Adding discovered device %s with"
                              " client address %s",
                              self._name,
                              str.title(loc['locationName']),
                              loc['clientAddr'])
                discovered_devices.append({
                    CONF_NAME: str.title(loc['locationName']),
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_DEVICE: loc['clientAddr'],
                    CONF_DISCOVER_CLIENTS: False,
                })

        if discovered_devices:
            _LOGGER.debug("%s: Adding %s new DirecTV entities to HASS",
                          self._name, len(discovered_devices))

            for new_device in discovered_devices:
                dtvs.append(DirecTvDevice(**new_device))
                self._hass.data.setdefault(DATA_DIRECTV, set()).add(
                    (new_device[CONF_HOST], new_device[CONF_DEVICE]))

            self._async_add_entities(dtvs)


class DirecTvDevice(MediaPlayerDevice):
    """Representation of a DirecTV receiver on the network."""

    def __init__(self, **kwargs):
        """Initialize the device."""
        self._host = kwargs.get(CONF_HOST)
        self._name = kwargs.get(CONF_NAME, self._host)
        self._port = kwargs.get(CONF_PORT, DEFAULT_PORT)
        self._device = kwargs.get(CONF_DEVICE, DEFAULT_DEVICE)

        # This is a client device is client address is not 0
        self._is_client = self._device != DEFAULT_DEVICE

        self.dtv = None
        self._is_standby = True
        self._current = None
        self._last_update = None
        self._paused = None
        self._last_position = None
        self._is_recorded = None
        self._assumed_state = None
        self._available = False
        self._first_error_timestamp = None

    async def async_added_to_hass(self):
        """Connect to DVR instance."""
        if self._is_client:
            _LOGGER.debug("%s: Created entity DirecTV client %s",
                          self.entity_id, self._device)
        else:
            _LOGGER.debug("%s: Created entity DirecTV device",
                          self.entity_id)

        await self._async_get_dtv_instance()

    async def async_update(self):
        """Retrieve latest state."""
        _LOGGER.debug("%s: Updating status", self.entity_id)
        try:
            self._available = True
            self._is_standby = await self._async_call_api(None, 'get_standby')
            if self._is_standby or self._is_standby is None:
                self._current = None
                self._is_recorded = None
                self._paused = None
                self._assumed_state = False
                self._last_position = None
                self._last_update = None
                if self._is_standby is None:
                    self._available = False
            else:
                self._current = await self._async_call_api(None, 'get_tuned')
                if self._current['status']['code'] == 200:
                    self._first_error_timestamp = None
                    self._is_recorded = self._current.get('uniqueId')\
                        is not None
                    self._paused = self._last_position == \
                        self._current['offset']
                    # Assumed state of playing if offset is changing and
                    # it is greater then duration.
                    self._assumed_state = self._current['offset'] > \
                        self._current['duration'] and not self._paused
                    self._last_position = self._current['offset']
                    self._last_update = dt_util.utcnow() if not self._paused \
                        or self._last_update is None else self._last_update
                else:
                    # If an error is received then only set to unavailable if
                    # this started at least 1 minute ago.
                    if not self._first_error_timestamp:
                        self._first_error_timestamp = dt_util.utcnow()
                    else:
                        tdelta = dt_util.utcnow() - self._first_error_timestamp
                        if tdelta.total_seconds() >= 60:
                            _LOGGER.error("%s: Invalid status %s received",
                                          self.entity_id,
                                          self._current['status']['code'])
                            self._available = False
                        else:
                            _LOGGER.debug("%s: Invalid status %s received",
                                          self.entity_id,
                                          self._current['status']['code'])

        except requests.RequestException as ex:
            _LOGGER.error("%s: Request error trying to update current status: "
                          "%s", self.entity_id, ex)
            if not self._first_error_timestamp:
                self._first_error_timestamp = dt_util.utcnow()
            else:
                tdelta = dt_util.utcnow() - self._first_error_timestamp
                if tdelta.total_seconds() >= 60:
                    self._available = False

        except Exception as ex:
            _LOGGER.error("%s: Exception trying to update current status: %s",
                          self.entity_id, ex)
            self._available = False
            if not self._first_error_timestamp:
                self._first_error_timestamp = dt_util.utcnow()
            raise

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attributes = {}
        if not self._is_standby:
            attributes[ATTR_MEDIA_CURRENTLY_RECORDING] =\
                self.media_currently_recording
            attributes[ATTR_MEDIA_RATING] = self.media_rating
            attributes[ATTR_MEDIA_RECORDED] = self.media_recorded
            attributes[ATTR_MEDIA_START_TIME] = self.media_start_time

        return attributes

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    # MediaPlayerDevice properties and methods
    @property
    def state(self):
        """Return the state of the device."""
        if self._is_standby:
            return STATE_OFF

        return STATE_PAUSED if self._paused else STATE_PLAYING

    @property
    def available(self):
        """Return if able to retrieve information from DVR or not."""
        return self._available

    @property
    def assumed_state(self):
        """Return if we assume the state or not."""
        return self._assumed_state

    @property
    def media_content_id(self):
        """Return the content ID of current playing media."""
        if self._is_standby:
            return None

        return self._current['programId']

    @property
    def media_content_type(self):
        """Return the content type of current playing media."""
        if self._is_standby:
            return None

        if 'episodeTitle' in self._current:
            return MEDIA_TYPE_TVSHOW

        return MEDIA_TYPE_MOVIE

    @property
    def media_duration(self):
        """Return the duration of current playing media in seconds."""
        if self._is_standby:
            return None

        return self._current['duration']

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        if self._is_standby:
            return None

        return self._last_position

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.

        Returns value from homeassistant.util.dt.utcnow().
        """
        if self._is_standby:
            return None

        return self._last_update

    @property
    def media_title(self):
        """Return the title of current playing media."""
        if self._is_standby:
            return None

        return self._current['title']

    @property
    def media_series_title(self):
        """Return the title of current episode of TV show."""
        if self._is_standby:
            return None

        return self._current.get('episodeTitle')

    @property
    def media_channel(self):
        """Return the channel current playing media."""
        if self._is_standby:
            return None

        return "{} ({})".format(
            self._current['callsign'], self._current['major'])

    @property
    def source(self):
        """Name of the current input source."""
        if self._is_standby:
            return None

        return self._current['major']

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DTV_CLIENT if self._is_client else SUPPORT_DTV

    @property
    def media_currently_recording(self):
        """If the media is currently being recorded or not."""
        if self._is_standby:
            return None

        return self._current['isRecording']

    @property
    def media_rating(self):
        """TV Rating of the current playing media."""
        if self._is_standby:
            return None

        return self._current['rating']

    @property
    def media_recorded(self):
        """If the media was recorded or live."""
        if self._is_standby:
            return None

        return self._is_recorded

    @property
    def media_start_time(self):
        """Start time the program aired."""
        if self._is_standby:
            return None

        return dt_util.as_local(
            dt_util.utc_from_timestamp(self._current['startTime']))

    async def async_turn_on(self):
        """Turn on the receiver."""
        if self._is_client:
            raise NotImplementedError()

        _LOGGER.debug("%s: Turn on", self.entity_id)
        await self._async_key_press('poweron')

    async def async_turn_off(self):
        """Turn off the receiver."""
        if self._is_client:
            raise NotImplementedError()

        _LOGGER.debug("%s: Turn off", self.entity_id)
        await self._async_key_press('poweroff')

    async def async_media_play(self):
        """Send play command."""
        _LOGGER.debug("%s: Play", self.entity_id)
        await self._async_key_press('play')

    async def async_media_pause(self):
        """Send pause command."""
        _LOGGER.debug("%s: Pause", self.entity_id)
        await self._async_key_press('pause')

    async def async_media_stop(self):
        """Send stop command."""
        _LOGGER.debug("%s: Stop", self.entity_id)
        await self._async_key_press('stop')

    async def async_media_previous_track(self):
        """Send rewind command."""
        _LOGGER.debug("%s: Rewind", self.entity_id)
        await self._async_key_press('rew')

    async def async_media_next_track(self):
        """Send fast forward command."""
        _LOGGER.debug("%s: Fast forward", self.entity_id)
        await self._async_key_press('ffwd')

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Select input source."""
        if media_type != MEDIA_TYPE_CHANNEL:
            _LOGGER.error("%s: Invalid media type %s. Only %s is supported",
                          self.entity_id, media_type, MEDIA_TYPE_CHANNEL)
            raise NotImplementedError()

        _LOGGER.debug("%s: Changing channel to %s", self.entity_id, media_id)
        try:
            await self._async_call_api("Not yet connected to DVR",
                                       'tune_channel', media_id)
        except requests.RequestException as ex:
            _LOGGER.error("%s: Request error trying to change channel: %s",
                          self.entity_id, ex)

    async def _async_get_dtv_instance(self):
        """Get the DTV instance to work with."""
        if self.dtv:
            return self.dtv

        from DirectPy import DIRECTV
        try:
            self.dtv = await self.hass.async_add_executor_job(
                DIRECTV, self._host, self._port, self._device)
        except requests.exceptions.RequestException as ex:
            _LOGGER.warning("%s: Exception trying to connect to DVR, will try "
                            "again later: %s", self.entity_id, ex)
            self.dtv = None

        if not self.dtv:
            return

        _LOGGER.debug("%s: Successfully connected to %s",
                      self.entity_id, self._host)
        return self.dtv

    async def _async_call_api(self, not_connected_error, api_call, *args,
                              **kwargs):
        """Call API method of DirecTV class."""
        if not await self._async_get_dtv_instance():
            if not_connected_error:
                _LOGGER.error("%s: Not yet connected to DVR", self.entity_id)
            else:
                _LOGGER.debug("%s: No connection to DVR", self.entity_id)
            return

        _LOGGER.debug("%s: Executing API call: %s", self.entity_id, api_call)
        return await self.hass.async_add_executor_job(
            partial(getattr(self.dtv, api_call), *args, **kwargs))

    async def _async_key_press(self, key):
        """Call sync function for key_press."""
        try:
            return await self._async_call_api("Not yet connected to DVR",
                                              'key_press', key)

        except requests.RequestException as ex:
            _LOGGER.error("%s: Request error trying to send key press: %s",
                          self.entity_id, ex)
            return
