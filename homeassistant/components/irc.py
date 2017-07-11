"""
Support for IRC.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/irc/
"""
import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.const import (
    CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    CONF_SSL, CONF_VERIFY_SSL)

REQUIREMENTS = ['irc3==1.0.0']
DOMAIN = 'irc'

_LOGGER = logging.getLogger(__name__)

CONF_CHANNEL = 'channel'
CONF_NICK = 'nick'
CONF_NETWORK = 'network'
CONF_AUTOJOIN = 'autojoin'
CONF_ZNC = 'znc'
CONF_IGNORE_USERS = 'ignore_users'
CONF_REAL_NAME = 'real_name'

DATA_IRC = 'data_irc'

ATTR_MESSAGE_COUNT = 'message_count'

DEFAULT_USERNAME = 'hass'
DEFAULT_REAL_NAME = 'Home Assistant'
DEFAULT_PORT = 6667

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_NICK): cv.string,
        vol.Required(CONF_NETWORK): cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Optional(CONF_REAL_NAME, default=DEFAULT_REAL_NAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
        vol.Optional(CONF_SSL, default=False): cv.boolean,
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_AUTOJOIN, default=[]):
            vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_ZNC, default=False): cv.boolean,
        vol.Optional(CONF_IGNORE_USERS, default=[]):
            vol.All(cv.ensure_list, [cv.string]),
    })])
}, extra=vol.ALLOW_EXTRA)


class Observable(object):
    """Wrapper that allows observation of attributes."""

    def __init__(self):
        """Initialize a new Observable instance."""
        self._observers = []
        self._do_notify = True

    def enable(self):
        """Send notification updates."""
        self._do_notify = True

    def disable(self):
        """Do not send notification updates."""
        self._do_notify = False

    def observe(self, observer):
        """Add observer that receives attribute updates."""
        if observer not in self._observers:
            self._observers.append(observer)

    def manual_update(self, attr):
        """Force notify observers of an attribute update."""
        if self._do_notify:
            for observer in self._observers:
                observer.attr_updated(attr, getattr(self, attr))

    def update(self, **kwargs):
        """Make updates to attributes and notify observers."""
        # Update all properties first...
        for attr, value in kwargs.items():
            setattr(self, str(attr), value)

        # ...then notify observers to make sure state is consistent
        if self._do_notify:
            for observer in self._observers:
                for attr, value in kwargs.items():
                    observer.attr_updated(attr, value)


class IRCChannel(Observable):
    """Representation of an IRC channel."""

    def __init__(self, channel):
        """Initialize a new IRC channel."""
        super().__init__()
        self.channel = channel
        self.topic = None
        self.last_speaker = None
        self.last_message = None
        self.message_count = 0
        self.users = set()


class HAPlugin(object):
    """Plugin to IRC3 that handles IRC commands."""

    import irc3

    # Matches topics when re-connecting to active ZNC session
    TOPIC_BNC_REPLAY = irc3.rfc.raw.new(
        'TOPIC_BNC_REPLAY',
        (r'^(@(?P<tags>\S+) )?:(?P<mask>\S+) 332 '
         r'(?P<nick>\S+) (?P<channel>\S+) :(?P<data>.+)'))

    # All users currently in a channel (matches NAMES command)
    NAME_LIST = irc3.rfc.raw.new(
        'NAME_LIST',
        (r'^(@(?P<tags>\S+) )?:(?P<mask>\S+) 353 '
         r'(?P<nick>\S+) @ (?P<channel>\S+) :(?P<users>.+)'))

    def __init__(self, context):
        """Initialize a new HAPlugin instance."""
        self.context = context
        self.config = context.config.get('hass_config')
        self._channels = {}

    def server_ready(self):
        """Triggered after the server sent the MOTD."""
        _LOGGER.info('Connected IRC network %s', self.config.get(CONF_NETWORK))

    @staticmethod
    def connection_lost():
        """Triggered when connection is lost."""
        _LOGGER.error('Failed to connect to IRC server')

    def get_channel(self, channel):
        """Return internal channel object."""
        if channel not in self._channels:
            self._channels[channel] = IRCChannel(channel)
        return self._channels[channel]

    @irc3.event(irc3.rfc.PRIVMSG)
    def on_privmsg(self, mask=None, target=None, data=None, **kw):
        """Handle PRIVMSG commands."""
        # Do not trigger updates for znc playback
        self._znc_toggle(mask, target, data)

        nick = mask.split('!')[0]

        # Ignore messages from blacklisted users
        if nick in self.config.get(CONF_IGNORE_USERS):
            return

        self._update_channel(target, last_speaker=nick, last_message=data)

    def _znc_toggle(self, mask, channel, data):
        if channel not in self._channels:
            return

        if self.config.get(CONF_ZNC) and mask == '***!znc@znc.in':
            if data == 'Buffer Playback...':
                self._channels[channel].disable()
            elif data == 'Playback Complete.':
                self._channels[channel].enable()

    @irc3.event(irc3.rfc.TOPIC)
    @irc3.event(TOPIC_BNC_REPLAY)
    def on_topic(self, channel=None, data=None, **kw):
        """Handle TOPIC commands."""
        self._update_channel(channel, update_counter=False, topic=data)

    def _update_channel(self, channel, update_counter=True, **kwargs):
        if channel in self._channels:
            obj = self._channels[channel]
            if update_counter:
                obj.message_count += 1
            obj.update(**kwargs)

    @irc3.event(NAME_LIST)
    def on_names(self, channel=None, users=None, **kwargs):
        """Handle NAMES commands."""
        if channel not in self._channels:
            return

        chan = self._channels[channel]
        chan.users.clear()
        for user in users.split(' '):
            if user.startswith('@') or user.startswith('+'):
                user = user[1:]
            chan.users.add(user)
        chan.manual_update('users')

    # These two should update user list for channel
    @irc3.event(irc3.rfc.JOIN_PART_QUIT)
    def on_user_event(self, mask=None, event=None, channel=None, **kwargs):
        """Handle JOIN, PART and QUIT commands."""
        if channel not in self._channels:
            return

        nick = mask.split('!')[0]
        chan = self._channels[channel]
        if event == 'JOIN':
            chan.users.add(nick)
        else:
            chan.users.remove(nick)
        chan.manual_update('users')

    @irc3.event(irc3.rfc.KICK)
    def on_user_kick(self, channel, target, **kwargs):
        """Handle KICK commands."""
        if channel not in self._channels:
            return

        chan = self._channels[channel]
        chan.users.remove(target)
        chan.manual_update('users')


@asyncio.coroutine
def async_setup(hass, config):
    """Setup the IRC component."""
    import irc3

    hass.data[DATA_IRC] = {}

    @asyncio.coroutine
    def async_setup_irc_server(hass, config):
        """Setup a new IRC server."""
        irc_config = {
            'loop': hass.loop,
            'nick': config.get(CONF_NICK),
            'host': config.get(CONF_HOST),
            'port': config.get(CONF_PORT),
            'username': config.get(CONF_USERNAME),
            'realname': config.get(CONF_REAL_NAME),
            'hass_config': config,
            'autojoins': config.get(CONF_AUTOJOIN),
            'ssl': config.get(CONF_SSL),
            'includes': ['irc3.plugins.core', __name__]
        }

        if CONF_PASSWORD in config:
            irc_config.update({'password': config.get(CONF_PASSWORD)})

        if not config.get(CONF_VERIFY_SSL):
            irc_config.update({'ssl_verify': 'CERT_NONE'})

        import irc3
        bot = irc3.IrcBot.from_config(irc_config)
        network = config.get(CONF_NETWORK)
        plugin_path = '{0}.{1}'.format(__name__, HAPlugin.__name__)
        hass.data[DATA_IRC][network] = bot.get_plugin(plugin_path)
        bot.run(forever=False)

        hass.async_add_job(discovery.async_load_platform(
            hass, 'notify', DOMAIN, {
                CONF_NETWORK: network
            }, config))

    # Plugins must have an attribute which is not possible to add globally
    # since Home Assistant installs dependencies on-the-fly. This adds it in
    # runtime instead (sort of a hack).
    global HAPlugin  # pylint: disable=invalid-name,global-variable-undefined
    HAPlugin = irc3.plugin(HAPlugin)

    tasks = [async_setup_irc_server(hass, conf) for conf in config[DOMAIN]]
    if tasks:
        yield from asyncio.wait(tasks, loop=hass.loop)

    return True
