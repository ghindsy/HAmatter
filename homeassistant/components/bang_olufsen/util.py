"""Various utilities for the Bang & Olufsen integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry


def get_device(hass: HomeAssistant, unique_id: str) -> DeviceEntry:
    """Get the device."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device({(DOMAIN, unique_id)})
    assert device

    return device
