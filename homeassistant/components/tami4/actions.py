"""Actions for Tami 4 Edge."""

import Tami4EdgeAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)

from .const import API, DOMAIN, SERVICE_FETCH_DRINKS, SERVICE_PREPARE_DRINK
from .exceptions import NoSuchDrink


def async_register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register all Tami4 services."""

    api: Tami4EdgeAPI = hass.data[DOMAIN][entry.entry_id][API]

    async def handle_prepare_drink(call: ServiceCall) -> None:
        drink_id = call.data.get("drink_id")
        device = await hass.async_add_executor_job(api.get_device)
        drink = [drink for drink in device.drinks if drink.id == drink_id]
        if len(drink) > 0:
            await hass.async_add_executor_job(api.prepare_drink, drink[0])
        else:
            raise NoSuchDrink("No such drink")

    async def handle_fetch_drinks(call: ServiceCall) -> ServiceResponse:
        device = await hass.async_add_executor_job(api.get_device)
        drinks = device.drinks
        return {drink.name: vars(drink) for drink in drinks}

    # Init Services
    hass.services.async_register(DOMAIN, SERVICE_PREPARE_DRINK, handle_prepare_drink)
    hass.services.async_register(
        DOMAIN,
        SERVICE_FETCH_DRINKS,
        handle_fetch_drinks,
        supports_response=SupportsResponse.ONLY,
    )
