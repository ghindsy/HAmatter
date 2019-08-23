"""Support for Plex media server monitoring."""
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_SSL,
    CONF_VERIFY_SSL,
)

from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_ENABLE_SENSOR,
    CONF_SERVER,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN as PLEX_DOMAIN,
    PLEX_SERVER_CONFIG,
)
from .server import setup_plex_server

_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_TOKEN): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SERVER): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Plex sensor.

    Deprecated.
    """
    if config:
        if not hass.config_entries.async_entries(PLEX_DOMAIN):
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    PLEX_DOMAIN, context={"source": "import_sensor"}, data=config
                )
            )
        else:
            _LOGGER.warning("Legacy configuration can be removed.")


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Plex sensor from a config entry."""

    def add_entities(devices, update_before_add=False):
        """Sync version of async add devices."""
        hass.add_job(async_add_entities, devices, update_before_add)

    options = dict(config_entry.options)
    if CONF_ENABLE_SENSOR not in options:
        options[CONF_ENABLE_SENSOR] = True
        hass.config_entries.async_update_entry(config_entry, options=options)

    hass.async_add_executor_job(_setup_platform, hass, config_entry, add_entities)


def _setup_platform(hass, config_entry, add_entities):
    """Set up the Plex sensor."""
    import plexapi.exceptions

    server_config = config_entry.data.get(PLEX_SERVER_CONFIG, {})

    try:
        sensor = PlexSensor(server_config)
    except (
        plexapi.exceptions.BadRequest,
        plexapi.exceptions.Unauthorized,
        plexapi.exceptions.NotFound,
    ) as error:
        _LOGGER.error(error)
        return

    add_entities([sensor], True)

    _LOGGER.info("Connected to: %s (%s)", sensor.server_name, sensor.server_url)


class PlexSensor(Entity):
    """Representation of a Plex now playing sensor."""

    def __init__(self, server_config):
        """Initialize the sensor."""
        self._state = 0
        self._now_playing = []
        self._server = setup_plex_server(server_config)
        self._server_url = self._server._baseurl  # pylint: disable=W0212
        self._server_name = self._server.friendlyName
        self._name = "Plex ({})".format(self._server_name)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def server_name(self):
        """Return the name of the sensor's Plex server."""
        return self._server_name

    @property
    def server_url(self):
        """Return the URL of the sensor's Plex server."""
        return self._server_url

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "Watching"

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {content[0]: content[1] for content in self._now_playing}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update method for Plex sensor."""
        sessions = self._server.sessions()
        now_playing = []
        for sess in sessions:
            user = sess.usernames[0]
            device = sess.players[0].title
            now_playing_user = f"{user} - {device}"
            now_playing_title = ""

            if sess.TYPE == "episode":
                # example:
                # "Supernatural (2005) - S01 · E13 - Route 666"
                season_title = sess.grandparentTitle
                if sess.show().year is not None:
                    season_title += " ({0})".format(sess.show().year)
                season_episode = "S{0}".format(sess.parentIndex)
                if sess.index is not None:
                    season_episode += f" · E{sess.index}"
                episode_title = sess.title
                now_playing_title = "{0} - {1} - {2}".format(
                    season_title, season_episode, episode_title
                )
            elif sess.TYPE == "track":
                # example:
                # "Billy Talent - Afraid of Heights - Afraid of Heights"
                track_artist = sess.grandparentTitle
                track_album = sess.parentTitle
                track_title = sess.title
                now_playing_title = "{0} - {1} - {2}".format(
                    track_artist, track_album, track_title
                )
            else:
                # example:
                # "picture_of_last_summer_camp (2015)"
                # "The Incredible Hulk (2008)"
                now_playing_title = sess.title
                if sess.year is not None:
                    now_playing_title += f" ({sess.year})"

            now_playing.append((now_playing_user, now_playing_title))
        self._state = len(sessions)
        self._now_playing = now_playing
