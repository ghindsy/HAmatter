"""Exceptions for Tami 4 integration."""

from homeassistant import exceptions


class NoSuchDrink(exceptions.HomeAssistantError):
    """Error to indicate drink does not exist."""
