"""
The hangouts bot component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/matrix/
"""
import logging

from homeassistant import config_entries
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from .const import (DOMAIN,
                    CONF_CONVERSATIONS, CONF_WORD, CONF_EXPRESSION,
                    CONF_REFRESH_TOKEN, CONF_BOT, CONF_COMMANDS,
                    CONFIG_SCHEMA, MESSAGE_SCHEMA,
                    EVENT_HANGOUTS_CONNECTED, EVENT_HANGOUTS_COMMAND,
                    EVENT_HANGOUTS_USERS_CHANGED,
                    EVENT_HANGOUTS_CONVERSATIONS_CHANGED,
                    SERVICE_SEND_MESSAGE,
                    SERVICE_UPDATE_USERS_AND_CONVERSATIONS)

from .config_flow import configured_hangouts

REQUIREMENTS = ['hangups==0.4.5']

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the Hangouts bot component."""

    config = config.get(DOMAIN, [])
    hass.data[DOMAIN] = {CONF_COMMANDS: config[CONF_COMMANDS]}

    if configured_hangouts(hass) is None:
        hass.async_add_job(hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_IMPORT}
        ))

    return True


async def async_setup_entry(hass, config):
    """Set up a config entry."""
    from hangups.auth import GoogleAuthError

    try:
        from .hangouts_bot import HangoutsBot

        bot = HangoutsBot(
            hass,
            config.data.get(CONF_REFRESH_TOKEN),
            hass.data[DOMAIN][CONF_COMMANDS])
        hass.data[DOMAIN][CONF_BOT] = bot
    except GoogleAuthError as exception:
        _LOGGER.error("Hangouts failed to log in: %s", str(exception))
        return False

    bot.hass.bus.async_listen(EVENT_HANGOUTS_CONNECTED,
                              bot.async_handle_update_users_and_conversations)
    bot.hass.bus.async_listen(EVENT_HANGOUTS_CONVERSATIONS_CHANGED,
                              bot.update_conversaition_commands)
    bot.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,
                                   bot.async_handle_hass_stop)

    await bot.async_connect()

    hass.services.async_register(DOMAIN, SERVICE_SEND_MESSAGE,
                                 bot.async_handle_send_message,
                                 schema=MESSAGE_SCHEMA)
    hass.services.async_register(DOMAIN,
                                 SERVICE_UPDATE_USERS_AND_CONVERSATIONS,
                                 bot.
                                 async_handle_update_users_and_conversations,
                                 schema=None)

    return True


async def async_unload_entry(hass, _):
    """Unload a config entry."""

    bot = hass.data[DOMAIN][CONF_BOT]
    del hass.data[DOMAIN][CONF_BOT]
    await bot.async_disconnect()
    return True
