"""Test Hydrawise binary_sensor."""

from datetime import timedelta
from unittest.mock import Mock

from homeassistant.components.hydrawise.const import SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_states(
    hass: HomeAssistant, mock_added_config_entry: MockConfigEntry
) -> None:
    """Test binary_sensor states."""
    # Make the coordinator refresh data.
    async_fire_time_changed(hass, utcnow() + SCAN_INTERVAL + timedelta(seconds=30))
    await hass.async_block_till_done()

    connectivity = hass.states.get("binary_sensor.home_controller_connectivity")
    assert connectivity is not None
    assert connectivity.state == "on"

    watering1 = hass.states.get("binary_sensor.zone_one_watering")
    assert watering1 is not None
    assert watering1.state == "off"

    watering2 = hass.states.get("binary_sensor.zone_two_watering")
    assert watering2 is not None
    assert watering2.state == "on"


async def test_update_data_fails(
    hass: HomeAssistant, mock_added_config_entry: MockConfigEntry, mock_pydrawise: Mock
) -> None:
    """Test that no data from the API sets the correct connectivity."""
    # Make the coordinator refresh data.
    mock_pydrawise.update_controller_info.return_value = None
    async_fire_time_changed(hass, utcnow() + SCAN_INTERVAL + timedelta(seconds=30))
    await hass.async_block_till_done()

    connectivity = hass.states.get("binary_sensor.home_controller_connectivity")
    assert connectivity is not None
    assert connectivity.state == "unavailable"
