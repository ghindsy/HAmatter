"""The onkyo component."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.hass_dict import HassKey

from .receiver import Receiver

DOMAIN = "onkyo"

DATA_ONKYO: HassKey[dict[str, Receiver]] = HassKey(DOMAIN)

CONFIG_SCHEMA = cv.platform_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _: ConfigType) -> bool:
    """Set up Onkyo component."""
    hass.data.setdefault(DATA_ONKYO, {})

    # pylint: disable-next=import-outside-toplevel
    from .media_player import async_register_services

    await async_register_services(hass)
    return True
