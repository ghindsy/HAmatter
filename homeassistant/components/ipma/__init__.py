"""
Component for the Portuguese weather service - IPMA.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/ipma/
"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant

DEFAULT_NAME = 'ipma'


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured IPMA."""
    # We allow setup only through config flow type of config
    return True


async def async_setup_entry(hass, config_entry):
    """Set up IPMA station as config entry."""
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(
        config_entry, 'weather'))
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(
        config_entry, 'weather')
    return True
