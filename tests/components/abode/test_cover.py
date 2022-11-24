"""Tests for the Abode cover device."""
from unittest.mock import patch

from spencerassistant.components.abode import ATTR_DEVICE_ID
from spencerassistant.components.cover import DOMAIN as COVER_DOMAIN
from spencerassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    STATE_CLOSED,
)
from spencerassistant.core import spencerAssistant
from spencerassistant.helpers import entity_registry as er

from .common import setup_platform

DEVICE_ID = "cover.garage_door"


async def test_entity_registry(hass: spencerAssistant) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(hass, COVER_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get(DEVICE_ID)
    assert entry.unique_id == "61cbz3b542d2o33ed2fz02721bda3324"


async def test_attributes(hass: spencerAssistant) -> None:
    """Test the cover attributes are correct."""
    await setup_platform(hass, COVER_DOMAIN)

    state = hass.states.get(DEVICE_ID)
    assert state.state == STATE_CLOSED
    assert state.attributes.get(ATTR_DEVICE_ID) == "ZW:00000007"
    assert not state.attributes.get("battery_low")
    assert not state.attributes.get("no_response")
    assert state.attributes.get("device_type") == "Secure Barrier"
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Garage Door"


async def test_open(hass: spencerAssistant) -> None:
    """Test the cover can be opened."""
    await setup_platform(hass, COVER_DOMAIN)

    with patch("abodepy.AbodeCover.open_cover") as mock_open:
        await hass.services.async_call(
            COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await hass.async_block_till_done()
        mock_open.assert_called_once()


async def test_close(hass: spencerAssistant) -> None:
    """Test the cover can be closed."""
    await setup_platform(hass, COVER_DOMAIN)

    with patch("abodepy.AbodeCover.close_cover") as mock_close:
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: DEVICE_ID},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_close.assert_called_once()
