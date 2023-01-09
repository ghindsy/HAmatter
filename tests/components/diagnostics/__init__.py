"""Tests for the Diagnostics integration."""
from http import HTTPStatus
from typing import Any

from aiohttp.test_utils import TestClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.setup import async_setup_component

from tests.conftest import TestClientGenerator


async def _get_diagnostics_for_config_entry(
    hass: HomeAssistant,
    hass_client: TestClientGenerator,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return the diagnostics config entry for the specified domain."""
    assert await async_setup_component(hass, "diagnostics", {})

    client: TestClient = await hass_client()
    response = await client.get(
        f"/api/diagnostics/config_entry/{config_entry.entry_id}"
    )
    assert response.status == HTTPStatus.OK
    return await response.json()


async def get_diagnostics_for_config_entry(
    hass: HomeAssistant,
    hass_client: TestClientGenerator,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return the diagnostics config entry for the specified domain."""
    data = await _get_diagnostics_for_config_entry(hass, hass_client, config_entry)
    return data["data"]


async def _get_diagnostics_for_device(
    hass: HomeAssistant,
    hass_client: TestClientGenerator,
    config_entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return the diagnostics for the specified device."""
    assert await async_setup_component(hass, "diagnostics", {})

    client = await hass_client()
    response = await client.get(
        f"/api/diagnostics/config_entry/{config_entry.entry_id}/device/{device.id}"
    )
    assert response.status == HTTPStatus.OK
    return await response.json()


async def get_diagnostics_for_device(
    hass: HomeAssistant,
    hass_client: TestClientGenerator,
    config_entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return the diagnostics for the specified device."""
    data = await _get_diagnostics_for_device(hass, hass_client, config_entry, device)
    return data["data"]
