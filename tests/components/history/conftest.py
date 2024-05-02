"""Fixtures for history tests."""

import pytest

from homeassistant.components import history
from homeassistant.const import CONF_DOMAINS, CONF_ENTITIES, CONF_EXCLUDE, CONF_INCLUDE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.typing import RecorderInstanceGenerator


@pytest.fixture
async def setup_recorder_before_hass(
    async_setup_recorder_instance: RecorderInstanceGenerator,
) -> RecorderInstanceGenerator | None:
    """Set up recorder."""
    return async_setup_recorder_instance


@pytest.fixture
async def hass_history(hass: HomeAssistant) -> None:
    """Home Assistant fixture with history."""
    config = history.CONFIG_SCHEMA(
        {
            history.DOMAIN: {
                CONF_INCLUDE: {
                    CONF_DOMAINS: ["media_player"],
                    CONF_ENTITIES: ["thermostat.test"],
                },
                CONF_EXCLUDE: {
                    CONF_DOMAINS: ["thermostat"],
                    CONF_ENTITIES: ["media_player.test"],
                },
            }
        }
    )
    assert await async_setup_component(hass, history.DOMAIN, config)
