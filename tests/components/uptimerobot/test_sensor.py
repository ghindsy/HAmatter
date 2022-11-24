"""Test UptimeRobot sensor."""

from unittest.mock import patch

from pyuptimerobot import UptimeRobotAuthenticationException

from spencerassistant.components.uptimerobot.const import COORDINATOR_UPDATE_INTERVAL
from spencerassistant.const import STATE_UNAVAILABLE
from spencerassistant.core import spencerAssistant
from spencerassistant.util import dt

from .common import (
    MOCK_UPTIMEROBOT_MONITOR,
    STATE_UP,
    UPTIMEROBOT_SENSOR_TEST_ENTITY,
    setup_uptimerobot_integration,
)

from tests.common import async_fire_time_changed

SENSOR_ICON = "mdi:television-shimmer"


async def test_presentation(hass: spencerAssistant) -> None:
    """Test the presenstation of UptimeRobot sensors."""
    await setup_uptimerobot_integration(hass)

    entity = hass.states.get(UPTIMEROBOT_SENSOR_TEST_ENTITY)

    assert entity.state == STATE_UP
    assert entity.attributes["icon"] == SENSOR_ICON
    assert entity.attributes["target"] == MOCK_UPTIMEROBOT_MONITOR["url"]


async def test_unaviable_on_update_failure(hass: spencerAssistant) -> None:
    """Test entity unaviable on update failure."""
    await setup_uptimerobot_integration(hass)

    entity = hass.states.get(UPTIMEROBOT_SENSOR_TEST_ENTITY)
    assert entity.state == STATE_UP

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        side_effect=UptimeRobotAuthenticationException,
    ):
        async_fire_time_changed(hass, dt.utcnow() + COORDINATOR_UPDATE_INTERVAL)
        await hass.async_block_till_done()

    entity = hass.states.get(UPTIMEROBOT_SENSOR_TEST_ENTITY)
    assert entity.state == STATE_UNAVAILABLE
