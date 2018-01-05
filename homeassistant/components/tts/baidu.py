"""
Support for Baidu speech service.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/tts.baidu/
"""

import logging
import voluptuous as vol

from homeassistant.const import CONF_API_KEY
from homeassistant.components.tts import Provider, PLATFORM_SCHEMA, CONF_LANG
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ["baidu-aip==1.6.6"]

_LOGGER = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ['zh']
DEFAULT_LANG = 'zh'

CONF_APP_ID = 'app_id'
CONF_SECRET_KEY = 'secret_key'
CONF_SPEED = 'speed'
CONF_PITCH = 'pitch'
CONF_VOLUME = 'volume'
CONF_PERSON = 'person'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_LANG, default=DEFAULT_LANG): vol.In(SUPPORTED_LANGUAGES),
    vol.Required(CONF_APP_ID): cv.string,
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_SECRET_KEY): cv.string,
    vol.Optional(CONF_SPEED, default=5): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=9)
    ),
    vol.Optional(CONF_PITCH, default=5): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=9)
    ),
    vol.Optional(CONF_VOLUME, default=5): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=15)
    ),
    vol.Optional(CONF_PERSON, default=0): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=4)
    ),
})

# Keys are options in the config file, and Values are options
# required by Baidu TTS API.
_options = {
    CONF_SPEED: 'spd',
    CONF_PITCH: 'pit',
    CONF_VOLUME: 'vol',
    CONF_PERSON: 'per',
}
SUPPORTED_OPTIONS = [
    CONF_SPEED,
    CONF_PITCH,
    CONF_VOLUME,
    CONF_PERSON,
]


def get_engine(hass, config):
    """Set up Baidu TTS component."""
    return BaiduTTSProvider(hass, config)


class BaiduTTSProvider(Provider):
    """Baidu TTS speech api provider."""

    def __init__(self, hass, conf):
        """Init Baidu TTS service."""
        self.hass = hass
        self._lang = conf.get(CONF_LANG)
        self._codec = 'mp3'
        self.name = 'BaiduTTS'

        self._app_data = {
            'appid': conf.get(CONF_APP_ID),
            'apikey': conf.get(CONF_API_KEY),
            'secretkey': conf.get(CONF_SECRET_KEY),
        }

        self._speech_conf_data = {
            _options[CONF_SPEED]: conf.get(CONF_SPEED),
            _options[CONF_PITCH]: conf.get(CONF_PITCH),
            _options[CONF_VOLUME]: conf.get(CONF_VOLUME),
            _options[CONF_PERSON]: conf.get(CONF_PERSON),
        }

    @property
    def default_language(self):
        """Return the default language."""
        return self._lang

    @property
    def supported_languages(self):
        """Return list of supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def default_options(self):
        """Return a dict include default options."""
        return {
            CONF_SPEED: self._speech_conf_data[_options[CONF_SPEED]],
            CONF_PITCH: self._speech_conf_data[_options[CONF_PITCH]],
            CONF_VOLUME: self._speech_conf_data[_options[CONF_VOLUME]],
            CONF_PERSON: self._speech_conf_data[_options[CONF_PERSON]],
        }

    @property
    def supported_options(self):
        """Return a list of supported options."""
        return SUPPORTED_OPTIONS

    def get_tts_audio(self, message, language, options=None):
        """Load TTS from BaiduTTS."""
        from aip import AipSpeech
        aip_speech = AipSpeech(
            self._app_data['appid'],
            self._app_data['apikey'],
            self._app_data['secretkey']
        )

        if options is None:
            result = aip_speech.synthesis(
                message, language, 1, self._speech_conf_data
            )
        else:
            speech_data = self._speech_conf_data.copy()
            for k, v in options.items():
                speech_data[_options[k]] = v

            result = aip_speech.synthesis(
                message, language, 1, speech_data
            )

        if isinstance(result, dict):
            _LOGGER.error(
                "Baidu TTS error-- err_no:%d; err_msg:%s; err_detail:%s",
                result['err_no'],
                result['err_msg'],
                result['err_detail'])
            return (None, None)

        return (self._codec, result)
