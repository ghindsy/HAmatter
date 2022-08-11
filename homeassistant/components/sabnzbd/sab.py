"""Support for the Sabnzbd service."""
import logging

from pysabnzbd import SabnzbdApi, SabnzbdApiException

from homeassistant.const import CONF_API_KEY, CONF_PATH, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


async def get_client(hass: HomeAssistant, data):
    """Get Sabnzbd client."""
    web_root = data.get(CONF_PATH)
    api_key = data[CONF_API_KEY]
    url = data[CONF_URL]

    sab_api = SabnzbdApi(
        url,
        api_key,
        web_root=web_root,
        session=async_get_clientsession(hass, False),
    )
    try:
        await sab_api.check_available()
    except SabnzbdApiException as exception:
        _LOGGER.error("Connection to SABnzbd API failed: %s", exception.message)
        return False

    return sab_api
