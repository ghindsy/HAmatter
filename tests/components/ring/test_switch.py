"""The tests for the Ring switch platform."""

from unittest.mock import PropertyMock, patch

import pytest
import requests_mock
import ring_doorbell

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .common import setup_platform

from tests.common import load_fixture


async def test_entity_registry(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    requests_mock: requests_mock.Mocker,
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(hass, Platform.SWITCH)

    entry = entity_registry.async_get("switch.front_siren")
    assert entry.unique_id == "765432-siren"

    entry = entity_registry.async_get("switch.internal_siren")
    assert entry.unique_id == "345678-siren"


async def test_siren_off_reports_correctly(
    hass: HomeAssistant, requests_mock: requests_mock.Mocker
) -> None:
    """Tests that the initial state of a device that should be off is correct."""
    await setup_platform(hass, Platform.SWITCH)

    state = hass.states.get("switch.front_siren")
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "Front Siren"


async def test_siren_on_reports_correctly(
    hass: HomeAssistant, requests_mock: requests_mock.Mocker
) -> None:
    """Tests that the initial state of a device that should be on is correct."""
    await setup_platform(hass, Platform.SWITCH)

    state = hass.states.get("switch.internal_siren")
    assert state.state == "on"
    assert state.attributes.get("friendly_name") == "Internal Siren"


async def test_siren_can_be_turned_on(
    hass: HomeAssistant, requests_mock: requests_mock.Mocker
) -> None:
    """Tests the siren turns on correctly."""
    await setup_platform(hass, Platform.SWITCH)

    # Mocks the response for turning a siren on
    requests_mock.put(
        "https://api.ring.com/clients_api/doorbots/765432/siren_on",
        text=load_fixture("doorbot_siren_on_response.json", "ring"),
    )

    state = hass.states.get("switch.front_siren")
    assert state.state == "off"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.front_siren"}, blocking=True
    )

    await hass.async_block_till_done()
    state = hass.states.get("switch.front_siren")
    assert state.state == "on"


async def test_updates_work(
    hass: HomeAssistant, requests_mock: requests_mock.Mocker
) -> None:
    """Tests the update service works correctly."""
    await setup_platform(hass, Platform.SWITCH)
    state = hass.states.get("switch.front_siren")
    assert state.state == "off"
    # Changes the return to indicate that the siren is now on.
    requests_mock.get(
        "https://api.ring.com/clients_api/ring_devices",
        text=load_fixture("devices_updated.json", "ring"),
    )

    await async_setup_component(hass, "homeassistant", {})
    await hass.services.async_call(
        "homeassistant",
        "update_entity",
        {ATTR_ENTITY_ID: ["switch.front_siren"]},
        blocking=True,
    )

    await hass.async_block_till_done()

    state = hass.states.get("switch.front_siren")
    assert state.state == "on"


@pytest.mark.parametrize(
    ("exception_type", "reauth_expected"),
    [
        (ring_doorbell.AuthenticationError, True),
        (ring_doorbell.RingTimeout, False),
        (ring_doorbell.RingError, False),
    ],
    ids=["Authentication", "Timeout", "Other"],
)
async def test_switch_errors_when_turned_on(
    hass: HomeAssistant,
    requests_mock: requests_mock.Mocker,
    exception_type,
    reauth_expected,
) -> None:
    """Tests the switch turns on correctly."""
    await setup_platform(hass, Platform.SWITCH)
    config_entry = hass.config_entries.async_entries("ring")[0]

    assert not any(config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))

    with patch.object(
        ring_doorbell.RingStickUpCam, "siren", new_callable=PropertyMock
    ) as mock_switch:
        mock_switch.side_effect = exception_type
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "switch", "turn_on", {"entity_id": "switch.front_siren"}, blocking=True
            )
        await hass.async_block_till_done()
    assert mock_switch.call_count == 1
    assert (
        any(
            flow
            for flow in config_entry.async_get_active_flows(hass, {SOURCE_REAUTH})
            if flow["handler"] == "ring"
        )
        == reauth_expected
    )
