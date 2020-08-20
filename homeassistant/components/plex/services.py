"""Services for the Plex integration."""
import logging

from plexapi.exceptions import NotFound
import voluptuous as vol

from .const import DOMAIN, SERVERS, SERVICE_REFRESH_LIBRARY

REFRESH_LIBRARY_SCHEMA = vol.Schema(
    {vol.Optional("server_name"): str, vol.Required("library_name"): str}
)

_LOGGER = logging.getLogger(__package__)


async def async_setup_services(hass):
    """Set up the Plex component."""

    async def async_refresh_library_service(service_call):
        await hass.async_add_executor_job(refresh_library, hass, service_call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_LIBRARY,
        async_refresh_library_service,
        schema=REFRESH_LIBRARY_SCHEMA,
    )

    return True


def refresh_library(hass, service_call):
    """Scan a Plex library for new and updated media."""
    plex_server_name = service_call.data.get("server_name")
    library_name = service_call.data.get("library_name")

    plex_server = get_plex_server(hass, plex_server_name)
    if not plex_server:
        return

    try:
        library = plex_server.library.section(title=library_name)
    except NotFound:
        _LOGGER.error(
            "Library with name '%s' not found in %s",
            library_name,
            list(map(lambda x: x.title, plex_server.library.sections())),
        )
        return

    _LOGGER.info("Scanning %s for new and updated media", library_name)
    library.update()


def get_plex_server(hass, plex_server_name=None):
    """Retrieve a configured Plex server by name."""
    plex_servers = hass.data[DOMAIN][SERVERS].values()

    if plex_server_name:
        plex_server = [x for x in plex_servers if x.friendly_name == plex_server_name]
        if not plex_server:
            _LOGGER.error(
                "Requested Plex server '%s' not found in %s",
                plex_server_name,
                list(map(lambda x: x.friendly_name, plex_servers)),
            )
            return None
    elif len(plex_servers) == 1:
        return next(iter(plex_servers))

    _LOGGER.error(
        "Multiple Plex servers configured and no selection made: %s",
        list(map(lambda x: x.friendly_name, plex_servers)),
    )
    return None
