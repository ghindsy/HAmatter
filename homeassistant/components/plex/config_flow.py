"""Config flow for Plex."""
import logging
import plexapi.exceptions
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from requests import Session
import requests.exceptions
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)

from .const import (
    CONF_SERVER,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLEX_SERVER_CONFIG,
    TITLE_TEMPLATE,
)
from .errors import ConfigNotReady, NoServersFound

_LOGGER = logging.getLogger(__package__)


@config_entries.HANDLERS.register(DOMAIN)
class PlexFlowHandler(config_entries.ConfigFlow):
    """Handle a Plex config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Plex flow."""
        self.current_login = {}
        self.discovery_info = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        for entry in self._async_current_entries():
            if PLEX_SERVER_CONFIG in entry.data:
                return self.async_abort(reason="already_configured")

        if user_input is not None:
            if user_input.get("manual_setup"):
                data_schema = vol.Schema(
                    {
                        vol.Required(
                            CONF_HOST, default=self.discovery_info.get(CONF_HOST)
                        ): str,
                        vol.Required(
                            CONF_PORT,
                            default=int(
                                self.discovery_info.get(CONF_PORT, DEFAULT_PORT)
                            ),
                        ): int,
                        vol.Optional(CONF_SSL, default=DEFAULT_SSL): bool,
                        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                    }
                )
                return self.async_show_form(
                    step_id="buildurl", data_schema=data_schema, errors={}
                )

            token_schema = vol.Schema({vol.Required(CONF_TOKEN): str})

            try:
                plex_url = user_input.get(CONF_URL)
                token = user_input.get(CONF_TOKEN)
                username = user_input.get(CONF_USERNAME)
                verify_ssl = user_input.get(CONF_VERIFY_SSL)

                if (username is None) and (plex_url is None):
                    raise ConfigNotReady

                data = {}

                if username:
                    if token is None:
                        self.current_login = {CONF_USERNAME: username}
                        return self.async_show_form(
                            step_id="token", data_schema=token_schema, errors={}
                        )

                    account = MyPlexAccount(username=username, token=token)
                    servers = [x for x in account.resources() if "server" in x.provides]
                    data[CONF_USERNAME] = username
                    data[CONF_TOKEN] = token
                    if len(servers) == 1:
                        plex_server = servers[0].name
                        title = TITLE_TEMPLATE.format(plex_server, account.username)
                        data[CONF_SERVER] = plex_server
                    elif len(servers) > 1:
                        """ TODO: Step to select server"""
                        pass
                    else:
                        raise NoServersFound
                elif plex_url:
                    self.current_login = {
                        CONF_URL: plex_url,
                        CONF_VERIFY_SSL: verify_ssl,
                    }

                    cert_session = None
                    if not verify_ssl:
                        cert_session = Session()
                        cert_session.verify = False

                    PlexServer(plex_url, token, cert_session)

                    title = TITLE_TEMPLATE.format(plex_url, "Direct")
                    data[CONF_URL] = plex_url
                    data[CONF_TOKEN] = token
                    data[CONF_VERIFY_SSL] = verify_ssl

                return self.async_create_entry(
                    title=title, data={PLEX_SERVER_CONFIG: data}
                )

            except ConfigNotReady:
                errors["base"] = "config_not_ready"
            except NoServersFound:
                errors["base"] = "no_servers"
            except (plexapi.exceptions.BadRequest, plexapi.exceptions.Unauthorized):
                if token is not None:
                    errors["base"] = "faulty_credentials"
                else:
                    return self.async_show_form(
                        step_id="token", data_schema=token_schema, errors={}
                    )
            except (plexapi.exceptions.NotFound, requests.exceptions.ConnectionError):
                errors["base"] = "not_found"
            except Exception as error:  # pylint: disable=broad-except
                _LOGGER.error("Unknown error connecting to %s: %s", plex_url, error)
                return self.async_abort(reason="unknown")

        data_schema = vol.Schema(
            {vol.Optional(CONF_USERNAME): str, vol.Optional("manual_setup"): bool}
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_token(self, user_input=None):
        """Get auth token from user if needed."""
        if user_input is None:
            return await self.async_step_user()

        config = self.current_login
        config[CONF_TOKEN] = user_input.get(CONF_TOKEN)
        return await self.async_step_user(user_input=config)

    async def async_step_buildurl(self, user_input=None):
        """Build URL from components."""
        if user_input is None:
            return await self.async_step_user()

        host = user_input.pop(CONF_HOST)
        port = user_input.pop(CONF_PORT)
        user_input[CONF_URL] = "{}://{}:{}".format(
            "https" if user_input.get(CONF_SSL) else "http", host, port
        )
        return await self.async_step_user(user_input=user_input)

    async def async_step_discovery(self, discovery_info):
        """Set default host and port from discovery."""
        self.discovery_info = discovery_info
        return await self.async_step_user()

    async def async_step_import(self, import_config):
        """Import from legacy Plex file config."""
        host_and_port, host_config = import_config.popitem()
        prefix = "https" if host_config[CONF_SSL] else "http"
        plex_url = "{}://{}".format(prefix, host_and_port)

        config = {
            CONF_URL: plex_url,
            CONF_TOKEN: host_config[CONF_TOKEN],
            CONF_VERIFY_SSL: host_config["verify"],
        }

        _LOGGER.info("Imported Plex configuration from legacy config file")
        return await self.async_step_user(user_input=config)
