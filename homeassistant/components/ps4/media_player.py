"""Support for PlayStation 4 consoles."""
import logging
import asyncio

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components.media_player import (
    ENTITY_IMAGE_URL, MediaPlayerDevice)
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID, ATTR_MEDIA_CONTENT_TYPE, ATTR_MEDIA_TITLE,
    MEDIA_TYPE_GAME, MEDIA_TYPE_APP, SUPPORT_SELECT_SOURCE, SUPPORT_PAUSE,
    SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_TURN_ON)
from homeassistant.components.ps4 import format_unique_id
from homeassistant.const import (
    ATTR_COMMAND, ATTR_ENTITY_ID, ATTR_LOCKED, CONF_HOST, CONF_NAME,
    CONF_REGION, CONF_TOKEN, STATE_IDLE, STATE_OFF, STATE_PLAYING)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.util.json import load_json, save_json
from homeassistant.exceptions import HomeAssistantError

from .const import (DEFAULT_ALIAS, DOMAIN as PS4_DOMAIN, PS4_DATA,
                    REGIONS as deprecated_regions)

_LOGGER = logging.getLogger(__name__)

SUPPORT_PS4 = SUPPORT_TURN_OFF | SUPPORT_TURN_ON | \
    SUPPORT_PAUSE | SUPPORT_STOP | SUPPORT_SELECT_SOURCE

ICON = 'mdi:playstation'
GAMES_FILE = '.ps4-games.json'
MEDIA_IMAGE_DEFAULT = None

ATTR_MEDIA_IMAGE_URL = 'media_image_url'

COMMANDS = (
    'up',
    'down',
    'right',
    'left',
    'enter',
    'back',
    'option',
    'ps',
)

SERVICE_COMMAND = 'send_command'
SERVICE_LOCK_MEDIA = 'lock_media'
SERVICE_UNLOCK_MEDIA = 'unlock_media'
SERVICE_LOCK_CURRENT_MEDIA = 'lock_current_media'
SERVICE_UNLOCK_CURRENT_MEDIA = 'unlock_current_media'
SERVICE_ADD_MEDIA = 'add_media'
SERVICE_REMOVE_MEDIA = 'remove_media'
SERVICE_EDIT_MEDIA = 'edit_media'

PS4_COMMAND_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_COMMAND): vol.All(cv.ensure_list, [COMMANDS])
})

PS4_LOCK_CURRENT_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id
})

PS4_UNLOCK_CURRENT_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id
})

PS4_LOCK_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_MEDIA_CONTENT_ID): str,
})

PS4_UNLOCK_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_MEDIA_CONTENT_ID): str,
})


PS4_ADD_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_MEDIA_CONTENT_ID): str,
    vol.Required(ATTR_MEDIA_TITLE): str,
    vol.Optional(ATTR_MEDIA_IMAGE_URL, default=''): vol.Any(
        cv.url, str),
    vol.Optional(ATTR_MEDIA_CONTENT_TYPE, default=MEDIA_TYPE_GAME): vol.In(
        [MEDIA_TYPE_GAME, MEDIA_TYPE_APP])

})

PS4_REMOVE_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_MEDIA_CONTENT_ID): str,
})

PS4_EDIT_MEDIA_SCHEMA = vol.Schema({
    vol.Required(ATTR_MEDIA_CONTENT_ID): str,
    vol.Optional(ATTR_MEDIA_TITLE, default=''): str,
    vol.Optional(ATTR_MEDIA_IMAGE_URL, default=''): vol.Any(
        cv.url, str),
    vol.Optional(ATTR_MEDIA_CONTENT_TYPE, default=MEDIA_TYPE_GAME): vol.In(
        [MEDIA_TYPE_GAME, MEDIA_TYPE_APP])
})


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up PS4 from a config entry."""
    config = config_entry
    await async_setup_platform(
        hass, config, async_add_entities, discovery_info=None)

    async def async_service_handle(hass):
        """Handle for services."""
        async def async_service_command(call):
            """Service for sending commands."""
            entity_ids = call.data[ATTR_ENTITY_ID]
            command = call.data[ATTR_COMMAND]
            for device in hass.data[PS4_DATA].devices:
                if device.entity_id in entity_ids:
                    await device.async_send_command(command)

        def set_media(hass, games, media_content_id, media_title,
                      media_url, media_type):
            """Set media data."""
            data = games[media_content_id]
            data[ATTR_LOCKED] = True
            data[ATTR_MEDIA_TITLE] = media_title
            data[ATTR_MEDIA_IMAGE_URL] = media_url
            data[ATTR_MEDIA_CONTENT_TYPE] = media_type
            games[media_content_id] = data
            save_games(hass, games)

        async def async_service_lock_media(call):
            """Service to lock media data that entity is playing."""
            games = load_games(hass)
            media_content_id = call.data[ATTR_MEDIA_CONTENT_ID]
            data = games.get(media_content_id)
            if data is not None:
                data[ATTR_LOCKED] = True
                games[media_content_id] = data
                save_games(hass, games)
                _LOGGER.debug("Setting Lock to %s", data[ATTR_LOCKED])
            else:
                raise HomeAssistantError(
                    "Title with ID: {} is not in source list".format(
                        media_content_id))

        async def async_service_unlock_media(call):
            """Service to lock media data that entity is playing."""
            games = load_games(hass)
            media_content_id = call.data[ATTR_MEDIA_CONTENT_ID]
            data = games.get(media_content_id)
            if data is not None:
                data[ATTR_LOCKED] = False
                games[media_content_id] = data
                save_games(hass, games)
                _LOGGER.debug("Setting Lock to %s", data[ATTR_LOCKED])
            else:
                raise HomeAssistantError(
                    "Title with ID: {} is not in source list".format(
                        media_content_id))

        async def async_service_lock_current_media(call):
            """Service to lock media data that entity is playing."""
            media_content_id = None
            entity_id = call.data[ATTR_ENTITY_ID]
            games = load_games(hass)
            for device in hass.data[PS4_DATA].devices:
                if device.entity_id == entity_id:
                    entity = device
                    media_id = entity.media_content_id
                    if media_id is not None:
                        media_content_id = media_id

            if media_content_id is not None:
                data = games.get(media_content_id)
                data[ATTR_LOCKED] = True
                games[media_content_id] = data
                save_games(hass, games)
                _LOGGER.debug("Setting Lock to %s", data[ATTR_LOCKED])
            else:
                raise HomeAssistantError(
                    "Entity: {} has no current media data".format(entity_id))

        async def async_service_unlock_current_media(call):
            """Service to unlock media data that entity is playing."""
            media_content_id = None
            entity_id = call.data[ATTR_ENTITY_ID]
            games = load_games(hass)
            for device in hass.data[PS4_DATA].devices:
                if device.entity_id == entity_id:
                    entity = device
                    media_id = entity.media_content_id
                    if media_id is not None:
                        media_content_id = media_id

            if media_content_id is not None:
                data = games.get(media_content_id)
                data[ATTR_LOCKED] = False
                games[media_content_id] = data
                save_games(hass, games)
                _LOGGER.debug("Setting Lock to %s", data[ATTR_LOCKED])
            else:
                raise HomeAssistantError(
                    "Entity: {} has no current media data".format(entity_id))

        async def async_service_add_media(call):
            """Add media data manually."""
            games = load_games(hass)

            media_content_id = call.data[ATTR_MEDIA_CONTENT_ID]
            media_title = call.data[ATTR_MEDIA_TITLE]
            media_url = None if call.data[ATTR_MEDIA_IMAGE_URL] == ''\
                else call.data[ATTR_MEDIA_IMAGE_URL]
            media_type = MEDIA_TYPE_GAME\
                if call.data[ATTR_MEDIA_CONTENT_TYPE] == ''\
                else call.data[ATTR_MEDIA_CONTENT_TYPE]
            set_media(hass, games, media_content_id, media_title,
                      media_url, media_type)

        async def async_service_remove_media(call):
            """Remove media data manually."""
            media_content_id = call.data[ATTR_MEDIA_CONTENT_ID]
            games = load_games(hass)
            if media_content_id in games:
                games.pop(media_content_id)
                save_games(hass, games)

        async def async_service_edit_media(call):
            """Service call for editing existing media data."""
            games = load_games(hass)
            media_content_id = call.data[ATTR_MEDIA_CONTENT_ID]
            data = games.get(media_content_id)
            if data is not None:
                media_title = None if call.data[ATTR_MEDIA_TITLE] == ''\
                    else call.data[ATTR_MEDIA_TITLE]
                media_url = None if call.data[ATTR_MEDIA_IMAGE_URL] == ''\
                    else call.data[ATTR_MEDIA_IMAGE_URL]
                media_type = MEDIA_TYPE_GAME\
                    if call.data[ATTR_MEDIA_CONTENT_TYPE] == ''\
                    else call.data[ATTR_MEDIA_CONTENT_TYPE]

                if media_title is None:
                    stored_title = data.get(ATTR_MEDIA_TITLE)
                    if stored_title is not None:
                        media_title = stored_title

                if media_url is None:
                    stored_url = data.get(ATTR_MEDIA_IMAGE_URL)
                    if stored_url is not None:
                        media_url = stored_url

                if media_type is None:
                    stored_type = data.get(ATTR_MEDIA_CONTENT_TYPE)
                    if stored_type is not None:
                        media_type = stored_type

                set_media(hass, games, media_content_id, media_title,
                          media_url, media_type)

        hass.services.async_register(
            PS4_DOMAIN, SERVICE_COMMAND, async_service_command,
            schema=PS4_COMMAND_SCHEMA)

        hass.services.async_register(
            PS4_DOMAIN, SERVICE_LOCK_MEDIA, async_service_lock_media,
            schema=PS4_LOCK_MEDIA_SCHEMA)
        hass.services.async_register(
            PS4_DOMAIN, SERVICE_UNLOCK_MEDIA,
            async_service_unlock_media,
            schema=PS4_UNLOCK_MEDIA_SCHEMA)
        hass.services.async_register(
            PS4_DOMAIN, SERVICE_LOCK_CURRENT_MEDIA,
            async_service_lock_current_media,
            schema=PS4_LOCK_CURRENT_MEDIA_SCHEMA)
        hass.services.async_register(
            PS4_DOMAIN, SERVICE_UNLOCK_CURRENT_MEDIA,
            async_service_unlock_current_media,
            schema=PS4_UNLOCK_CURRENT_MEDIA_SCHEMA)
        hass.services.async_register(
            PS4_DOMAIN, SERVICE_ADD_MEDIA, async_service_add_media,
            schema=PS4_ADD_MEDIA_SCHEMA)
        hass.services.async_register(
            PS4_DOMAIN, SERVICE_REMOVE_MEDIA,
            async_service_remove_media,
            schema=PS4_REMOVE_MEDIA_SCHEMA)
        hass.services.async_register(
            PS4_DOMAIN, SERVICE_EDIT_MEDIA, async_service_edit_media,
            schema=PS4_EDIT_MEDIA_SCHEMA)

    await async_service_handle(hass)


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """Set up PS4 Platform."""
    import pyps4_homeassistant.ps4 as pyps4
    creds = config.data[CONF_TOKEN]
    device_list = []
    for device in config.data['devices']:
        host = device[CONF_HOST]
        region = device[CONF_REGION]
        name = device[CONF_NAME]
        ps4 = pyps4.Ps4Async(host, creds, device_name=DEFAULT_ALIAS)
        device_list.append(PS4Device(
            config, name, host, region, ps4, creds))
    async_add_entities(device_list, update_before_add=True)


def load_games(hass):
    """Load games for sources."""
    g_file = hass.config.path(GAMES_FILE)
    try:
        games = load_json(g_file)

    # If file does not exist, create empty file.
    except FileNotFoundError:
        games = {}
        save_games(hass, games)

    # Convert str format to dict format if not already.
    if games is not None:
        for game, data in games.items():
            if type(data) is not dict:
                games[game] = {ATTR_MEDIA_TITLE: data,
                               ATTR_MEDIA_IMAGE_URL: None,
                               ATTR_LOCKED: False,
                               ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_GAME}

    return games


def save_games(hass, games):
    """Save games to file."""
    g_file = hass.config.path(GAMES_FILE)
    try:
        save_json(g_file, games)
    except OSError as error:
        _LOGGER.error("Could not save game list, %s", error)

    # Retry loading file
    if games is None:
        load_games()


class PS4Device(MediaPlayerDevice):
    """Representation of a PS4."""

    def __init__(self, config, name, host, region, ps4, creds):
        """Initialize the ps4 device."""
        self._entry_id = config.entry_id
        self._ps4 = ps4
        self._host = host
        self._name = name
        self._region = region
        self._creds = creds
        self._state = None
        self._media_content_id = None
        self._media_title = None
        self._media_image = None
        self._media_type = None
        self._source = None
        self._games = {}
        self._source_list = []
        self._retry = 0
        self._disconnected = False
        self._info = None
        self._unique_id = None

    @callback
    def status_callback(self):
        """Handle status callback. Parse status."""
        self._parse_status()

    @callback
    def schedule_update(self):
        """Schedules update with HA."""
        self.async_schedule_update_ha_state()

    @callback
    def subscribe_to_protocol(self):
        """Notify protocol to callback with update changes."""
        self.hass.data[PS4_DATA].protocol.add_callback(
            self._ps4, self.status_callback)

    @callback
    def unsubscribe_to_protocol(self):
        """Notify protocol to remove callback."""
        self.hass.data[PS4_DATA].protocol.remove_callback(
            self._ps4, self.status_callback)

    def check_region(self):
        """Display logger msg if region is deprecated."""
        # Non-Breaking although data returned may be inaccurate.
        if self._region in deprecated_regions:
            _LOGGER.info("""Region: %s has been deprecated.
                            Please remove PS4 integration
                            and Re-configure again to utilize
                            current regions""", self._region)

    async def async_added_to_hass(self):
        """Subscribe PS4 events."""
        self.hass.data[PS4_DATA].devices.append(self)
        self.check_region()

    async def async_update(self):
        """Retrieve the latest data."""
        if self._ps4.ddp_protocol is not None:
            # Request Status with asyncio transport.
            self._ps4.get_status()
            if not self._ps4.connected and not self._ps4.is_standby:
                await self._ps4.async_connect()

        # Try to ensure correct status is set on startup for device info.
        if self._ps4.ddp_protocol is None:
            # Use socket.socket.
            await self.hass.async_add_executor_job(self._ps4.get_status)
            if self._info is None:
                # Add entity to registry.
                await self.async_get_device_info(self._ps4.status)
            self._ps4.ddp_protocol = self.hass.data[PS4_DATA].protocol
            self.subscribe_to_protocol()

        self._parse_status()

    def _parse_status(self):
        """Parse status."""
        status = self._ps4.status

        if status is not None:
            self._games = load_games(self.hass)
            if self._games is not None:
                games = []
                for data in self._games.values():
                    games.append(data[ATTR_MEDIA_TITLE])
                self._source_list = sorted(games)

            self._retry = 0
            self._disconnected = False
            if status.get('status') == 'Ok':
                title_id = status.get('running-app-titleid')
                name = status.get('running-app-name')

                if title_id and name is not None:
                    self._state = STATE_PLAYING

                    if self._media_content_id != title_id:
                        self._media_content_id = title_id

                        if self._media_content_id in self._games:
                            store = self._games[self._media_content_id]

                            # If locked get attributes from file.
                            locked = store.get(ATTR_LOCKED)
                            if locked:
                                self._media_title = store.get(ATTR_MEDIA_TITLE)
                                self._source = self._media_title
                                self._media_image = store.get(
                                    ATTR_MEDIA_IMAGE_URL)
                                self._media_type = store.get(
                                    ATTR_MEDIA_CONTENT_TYPE)
                                return

                        # Get data from PS Store if not locked.
                        asyncio.ensure_future(
                            self.async_get_title_data(title_id, name))

                else:
                    if self._state != STATE_IDLE:
                        self.idle()
            else:
                if self._state != STATE_OFF:
                    self.state_off()

        elif self._retry > 5:
            self.state_unknown()
        else:
            self._retry += 1

    def idle(self):
        """Set states for state idle."""
        self.reset_title()
        self._state = STATE_IDLE
        self.schedule_update()

    def state_off(self):
        """Set states for state off."""
        self.reset_title()
        self._state = STATE_OFF
        self.schedule_update()

    def state_unknown(self):
        """Set states for state unknown."""
        self.reset_title()
        self._state = None
        if self._disconnected is False:
            _LOGGER.warning("PS4 could not be reached")
        self._disconnected = True
        self._retry = 0

    def reset_title(self):
        """Update if there is no title."""
        self._media_title = None
        self._media_content_id = None
        self._media_type = None
        self._source = None

    async def async_get_title_data(self, title_id, name):
        """Get PS Store Data."""
        from pyps4_homeassistant.errors import PSDataIncomplete
        _LOGGER.debug("Starting PS Store Search, %s: %s", title_id, name)
        app_name = None
        art = None
        media_type = None
        try:
            title = await self._ps4.async_get_ps_store_data(
                name, title_id, self._region)

        except PSDataIncomplete:
            title = None
        except asyncio.TimeoutError:
            title = None
            _LOGGER.error("PS Store Search Timed out")

        else:
            if title is not None:
                app_name = title.name
                art = title.cover_art
                # Assume media type is game if not app.
                if title.game_type != 'App':
                    media_type = MEDIA_TYPE_GAME
                else:
                    media_type = MEDIA_TYPE_APP
            else:
                _LOGGER.error(
                    "Could not find data in region: %s for PS ID: %s",
                    self._region, title_id)

        finally:
            self._media_title = app_name or name
            self._source = self._media_title
            self._media_image = art or None
            self._media_type = media_type

            self.update_list()
            self.schedule_update()

    def update_list(self):
        """Update Game List, Correct data if different."""
        if self._media_content_id in self._games:
            store = self._games[self._media_content_id]

            if store.get(ATTR_MEDIA_TITLE) != self._media_title or\
                    store.get(ATTR_MEDIA_IMAGE_URL) != self._media_image:
                self._games.pop(self._media_content_id)

        if self._media_content_id not in self._games:
            self.add_games(
                self._media_content_id, self._media_title,
                self._media_image, self._media_type)
            self._games = load_games(self.hass)

        self._source_list = list(sorted(self._games))

    def add_games(self, title_id, app_name, image, g_type, is_locked=False):
        """Add games to list."""
        games = self._games
        if title_id is not None and title_id not in games:
            game = {title_id: {
                ATTR_MEDIA_TITLE: app_name, ATTR_MEDIA_IMAGE_URL: image,
                ATTR_MEDIA_CONTENT_TYPE: g_type, ATTR_LOCKED: is_locked}}
            games.update(game)
            save_games(self.hass, games)

    async def async_get_device_info(self, status):
        """Set device info for registry."""
        # If cannot get status on startup, assume info from registry.
        if status is None:
            _LOGGER.info("Assuming info from registry")
            e_registry = await entity_registry.async_get_registry(self.hass)
            d_registry = await device_registry.async_get_registry(self.hass)
            for entity_id, entry in e_registry.entities.items():
                if entry.config_entry_id == self._entry_id:
                    self._unique_id = entry.unique_id
                    self.entity_id = entity_id
                    break
            for device in d_registry.devices.values():
                if self._entry_id in device.config_entries:
                    self._info = {
                        'name': device.name,
                        'model': device.model,
                        'identifiers': device.identifiers,
                        'manufacturer': device.manufacturer,
                        'sw_version': device.sw_version
                    }
                    break

        else:
            _sw_version = status['system-version']
            _sw_version = _sw_version[1:4]
            sw_version = "{}.{}".format(_sw_version[0], _sw_version[1:])
            self._info = {
                'name': status['host-name'],
                'model': 'PlayStation 4',
                'identifiers': {
                    (PS4_DOMAIN, status['host-id'])
                },
                'manufacturer': 'Sony Interactive Entertainment Inc.',
                'sw_version': sw_version
            }

            self._unique_id = format_unique_id(self._creds, status['host-id'])

    async def async_will_remove_from_hass(self):
        """Remove Entity from Hass."""
        # Close TCP Transport.
        if self._ps4.connected:
            await self._ps4.close()
        self.hass.data[PS4_DATA].devices.remove(self)

    @property
    def device_info(self):
        """Return information about the device."""
        return self._info

    @property
    def unique_id(self):
        """Return Unique ID for entity."""
        return self._unique_id

    @property
    def entity_picture(self):
        """Return picture."""
        if self._state == STATE_PLAYING and self._media_content_id is not None:
            image_hash = self.media_image_hash
            if image_hash is not None:
                return ENTITY_IMAGE_URL.format(
                    self.entity_id, self.access_token, image_hash)
        return MEDIA_IMAGE_DEFAULT

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Icon."""
        return ICON

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self._media_content_id

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return self._media_type

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        if self._media_content_id is None:
            return MEDIA_IMAGE_DEFAULT
        return self._media_image

    @property
    def media_title(self):
        """Title of current playing media."""
        return self._media_title

    @property
    def supported_features(self):
        """Media player features that are supported."""
        return SUPPORT_PS4

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    async def async_turn_off(self):
        """Turn off media player."""
        await self._ps4.standby()

    async def async_turn_on(self):
        """Turn on the media player."""
        self._ps4.wakeup()

    async def async_media_pause(self):
        """Send keypress ps to return to menu."""
        await self.async_send_remote_control('ps')

    async def async_media_stop(self):
        """Send keypress ps to return to menu."""
        await self.async_send_remote_control('ps')

    async def async_select_source(self, source):
        """Select input source."""
        for title_id, data in self._games.items():
            game = data[ATTR_MEDIA_TITLE]
            if source.lower().encode(encoding='utf-8') == \
               game.lower().encode(encoding='utf-8') \
               or source == title_id:

                _LOGGER.debug(
                    "Starting PS4 game %s (%s) using source %s",
                    game, title_id, source)

                await self._ps4.start_title(title_id, self._media_content_id)
                return

        _LOGGER.warning(
            "Could not start title. '%s' is not in source list", source)
        return

    async def async_send_command(self, command):
        """Send Button Command."""
        await self.async_send_remote_control(command)

    async def async_send_remote_control(self, command):
        """Send RC command."""
        await self._ps4.remote_control(command)
