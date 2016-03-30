"""
Support for text to speech in Home Assistant.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/tts/
"""

import sys
import logging
import re
import hashlib
import os.path
from functools import partial

import homeassistant.bootstrap as bootstrap
from homeassistant.helpers import config_per_platform
from homeassistant.const import (ATTR_ENTITY_ID, CONF_NAME)
from homeassistant.config import load_yaml_config_file
from homeassistant.components import media_player

DEPENDENCIES = ['http']

DOMAIN = "tts"

SERVICE_TTS = "tts"

ATTR_TEXT = "text"
ATTR_ALLOW_CACHE = "allow_cached_file"
ATTR_DELETE_AFTER_USE = "delete_after_use"
ATTR_PLAY = "play"
ATTR_LANGUAGE = "language"
ATTR_RATE = "rate"
ATTR_CODEC = "codec"
ATTR_FORMAT = "format"
ATTR_MEDIA_CONTENT_ID = "media_content_id"
ATTR_MEDIA_CONTENT_TYPE = "media_content_type"

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Setup the tts service."""
    success = False

    descriptions = load_yaml_config_file(
        os.path.join(os.path.dirname(__file__), 'services.yaml'))

    tts_dir = hass.config.path(DOMAIN)

    if not os.path.exists(tts_dir):
        os.makedirs(tts_dir)

    for platform, p_config in config_per_platform(config, DOMAIN, _LOGGER):
        tts_implementation = bootstrap.prepare_setup_platform(
            hass, config, DOMAIN, platform)

        if tts_implementation is None:
            _LOGGER.error("Unknown tts service specified.")
            continue

        tts_engine = tts_implementation.get_engine(hass, p_config)

        if tts_engine is None:
            _LOGGER.error("Failed to initialize tts service %s",
                          platform)
            continue

        # pylint: disable=too-many-locals
        def generate_speech(tts_service, platform_name, call):
            """Handle sending tts message service calls."""
            text = call.data.get(ATTR_TEXT)
            entity_id = call.data.get(ATTR_ENTITY_ID)
            allow_cached_file = call.data.get(ATTR_ALLOW_CACHE, True)
            delete_after_use = call.data.get(ATTR_DELETE_AFTER_USE, False)
            play_file = call.data.get(ATTR_PLAY, True)
            language = call.data.get(ATTR_LANGUAGE, config.get(ATTR_LANGUAGE,
                                                               "en-us"))
            rate = call.data.get(ATTR_RATE, config.get(ATTR_RATE))
            codec = call.data.get(ATTR_CODEC, config.get(ATTR_CODEC, "MP3"))
            audio_format = call.data.get(ATTR_FORMAT, config.get(ATTR_FORMAT))

            hashed_text = hashlib.sha1(text.encode('utf-8')).hexdigest()

            full_filename = "{}-{}-{}.{}".format(hashed_text, language,
                                                 platform_name,
                                                 codec.lower())

            file_path = os.path.join(tts_dir, full_filename)

            if text is None:
                _LOGGER.error(
                    'Received call to %s without attribute %s',
                    call.service, ATTR_TEXT)
                return

            if (os.path.isfile(file_path)) is False or \
               (allow_cached_file is False):
                try:
                    tts_service.get_speech(file_path, text, language,
                                           rate, codec, audio_format)
                # pylint: disable=bare-except
                except:
                    # _LOGGER.error("get_speech error:", sys.exc_info()[0])
                    _LOGGER.error('Error trying to get_speech using %s',
                                  platform_name)
                    return

            if play_file is True or entity_id is None:
                content_url = "{}/api/tts/{}".format(hass.config.api.base_url,
                                                     full_filename)
                media_player.play_media(hass, media_player.MEDIA_TYPE_MUSIC,
                                        content_url, entity_id)

            if delete_after_use:
                os.remove(file_path)

        service_tts = p_config.get(CONF_NAME, platform)
        service_call_handler = partial(generate_speech, tts_engine,
                                       service_tts)
        hass.services.register(DOMAIN, service_tts, service_call_handler,
                               descriptions.get(SERVICE_TTS))
        success = True

    hass.http.register_path(
        'GET', re.compile(r'/api/tts/(?P<tts_filename>.*)'),
        _handle_get_tts_file)

    return success


def _handle_get_tts_file(handler, path_match, data):
    """Return a TTS file."""
    handler.write_file(os.path.join(handler.server.hass.config.path(DOMAIN),
                                    path_match.group('tts_filename')))

# pylint: disable=too-few-public-methods


class BaseTTSService(object):
    """An abstract class for TTS services."""

    # pylint: disable=too-many-arguments
    def get_speech(self, file_path, text, language=None, rate=None,
                   codec=None, audio_format=None):
        """Speak something."""
        raise NotImplementedError
