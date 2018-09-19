"""
Support for IKEA Tradfri.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/ikea_tradfri/
"""
import logging

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.util.json import load_json

from .const import CONF_IMPORT_GROUPS, CONF_IDENTITY, CONF_HOST, CONF_KEY

from . import config_flow  # noqa  pylint_disable=unused-import

REQUIREMENTS = ['pytradfri[async]==5.5.1']

DOMAIN = 'tradfri'
CONFIG_FILE = '.tradfri_psk.conf'
KEY_GATEWAY = 'tradfri_gateway'
KEY_API = 'tradfri_api'
CONF_ALLOW_TRADFRI_GROUPS = 'allow_tradfri_groups'
DEFAULT_ALLOW_TRADFRI_GROUPS = True

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Inclusive(CONF_HOST, 'gateway'): cv.string,
        vol.Optional(CONF_ALLOW_TRADFRI_GROUPS,
                     default=DEFAULT_ALLOW_TRADFRI_GROUPS): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the Tradfri component."""
    conf = config.get(DOMAIN)

    if conf is None:
        return True

    known_hosts = await hass.async_add_executor_job(
        load_json, hass.config.path(CONFIG_FILE))

    for host, info in known_hosts.items():
        info[CONF_HOST] = host
        info[CONF_IMPORT_GROUPS] = conf[CONF_ALLOW_TRADFRI_GROUPS]

        hass.async_create_task(hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_IMPORT},
            data=info
        ))

    host = conf.get(CONF_HOST)

    if host is None or host in known_hosts:
        return True

    hass.async_create_task(hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_IMPORT},
        data={'host': host}
    ))

    return True


async def async_setup_entry(hass, entry):
    """Create a gateway."""
    # host, identity, key, allow_tradfri_groups
    from pytradfri import Gateway, RequestError  # pylint: disable=import-error
    from pytradfri.api.aiocoap_api import APIFactory

    try:
        factory = APIFactory(
            entry.data[CONF_HOST],
            psk_id=entry.data[CONF_IDENTITY],
            psk=entry.data[CONF_KEY],
            loop=hass.loop
        )
        api = factory.request
        gateway = Gateway()
        gateway_info_result = await api(gateway.get_gateway_info())
    except RequestError:
        _LOGGER.error("Tradfri setup failed.")
        return False

    gateway_id = gateway_info_result.id
    gateways = hass.data.setdefault(KEY_GATEWAY, {})
    hass.data.setdefault(KEY_API, {})[entry.entry_id] = api

    # Check if already set up
    if gateway_id in gateways:
        return True

    gateways[entry.entry_id] = gateway

    hass.async_create_task(hass.config_entries.async_forward_entry_setup(
        entry, 'light'
    ))
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(
        entry, 'sensor'
    ))

    return True
