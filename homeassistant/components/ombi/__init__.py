"""Support for Ombi."""
import logging

import pyombi
import voluptuous as vol

from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_URLBASE,
    CONF_NAME,
    CONF_SEASON,
    DEFAULT_PORT,
    DEFAULT_SEASON,
    DEFAULT_SSL,
    DEFAULT_URLBASE,
    DOMAIN,
    SERVICE_MOVIE_REQUEST,
    SERVICE_MUSIC_REQUEST,
    SERVICE_TV_REQUEST,
)

_LOGGER = logging.getLogger(__name__)


def urlbase(value) -> str:
    """Validate and transform urlbase."""
    if value is None:
        raise vol.Invalid("string value is None")
    value = str(value)
    return value.strip("/") + "/"


SUBMIT_MOVIE_REQUEST_SERVICE_SCHEME = vol.Schema({vol.Required(CONF_NAME): cv.string})

SUBMIT_MUSIC_REQUEST_SERVICE_SCHEME = vol.Schema({vol.Required(CONF_NAME): cv.string})

SUBMIT_TV_REQUEST_SERVICE_SCHEME = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_SEASON, default=DEFAULT_SEASON): vol.In(
            ["first", "latest", "all"]
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_URLBASE, default=DEFAULT_URLBASE): urlbase,
                vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set up the Ombi component platform."""

    ombi = pyombi.Ombi(
        ssl=config[DOMAIN][CONF_SSL],
        host=config[DOMAIN][CONF_HOST],
        port=config[DOMAIN][CONF_PORT],
        api_key=config[DOMAIN][CONF_API_KEY],
        username=config[DOMAIN][CONF_USERNAME],
        urlbase=config[DOMAIN][CONF_URLBASE],
    )

    try:
        ombi.test_connection()
    except pyombi.OmbiError as err:
        _LOGGER.warning("Unable to setup Ombi: %s", err)
        return

    hass.data[DOMAIN] = {"instance": ombi}

    def submit_movie_request(call):
        """Submit request for movie."""
        name = call.data.get(CONF_NAME)
        movies = ombi.search_movie(name)
        if movies:
            movie = movies[0]
            ombi.request_movie(movie["theMovieDbId"])

    def submit_tv_request(call):
        """Submit request for TV show."""
        name = call.data.get("name")
        tv_shows = ombi.search_tv(name)

        if tv_shows:
            season = call.data.get("season")
            show = tv_shows[0]["id"]
            if season == "first":
                ombi.request_tv(show, request_first=True)
            elif season == "latest":
                ombi.request_tv(show, request_latest=True)
            elif season == "all":
                ombi.request_tv(show, request_all=True)

    def submit_music_request(call):
        """Submit request for music album."""
        name = call.data.get("name")
        music = ombi.search_music_album(name)
        if music:
            ombi.request_music(music[0]["foreignAlbumId"])

    hass.services.register(
        DOMAIN,
        SERVICE_MOVIE_REQUEST,
        submit_movie_request,
        schema=SUBMIT_MOVIE_REQUEST_SERVICE_SCHEME,
    )
    hass.services.register(
        DOMAIN,
        SERVICE_MUSIC_REQUEST,
        submit_music_request,
        schema=SUBMIT_MUSIC_REQUEST_SERVICE_SCHEME,
    )
    hass.services.register(
        DOMAIN,
        SERVICE_TV_REQUEST,
        submit_tv_request,
        schema=SUBMIT_TV_REQUEST_SERVICE_SCHEME,
    )
    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)

    return True
