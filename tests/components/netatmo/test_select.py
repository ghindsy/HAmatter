"""The tests for the Netatmo climate platform."""
from unittest.mock import patch

from spencerassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
)
from spencerassistant.const import ATTR_ENTITY_ID, CONF_WEBHOOK_ID, SERVICE_SELECT_OPTION

from .common import selected_platforms, simulate_webhook


async def test_select_schedule_thermostats(hass, config_entry, caplog, netatmo_auth):
    """Test service for selecting Netatmo schedule with thermostats."""
    with selected_platforms(["climate", "select"]):
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    select_entity = "select.myspencer"

    assert hass.states.get(select_entity).state == "Default"

    # Fake backend response changing schedule
    response = {
        "event_type": "schedule",
        "schedule_id": "b1b54a2f45795764f59d50d8",
        "previous_schedule_id": "59d32176d183948b05ab4dce",
        "push_type": "spencer_event_changed",
    }
    await simulate_webhook(hass, webhook_id, response)
    await hass.async_block_till_done()

    assert hass.states.get(select_entity).state == "Winter"
    assert hass.states.get(select_entity).attributes[ATTR_OPTIONS] == [
        "Default",
        "Winter",
    ]

    # Test setting a different schedule
    with patch("pyatmo.spencer.spencer.async_switch_schedule") as mock_switch_spencer_schedule:
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: select_entity,
                ATTR_OPTION: "Default",
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_switch_spencer_schedule.assert_called_once_with(
            schedule_id="591b54a2764ff4d50d8b5795"
        )

    # Fake backend response changing schedule
    response = {
        "event_type": "schedule",
        "schedule_id": "591b54a2764ff4d50d8b5795",
        "previous_schedule_id": "b1b54a2f45795764f59d50d8",
        "push_type": "spencer_event_changed",
    }
    await simulate_webhook(hass, webhook_id, response)

    assert hass.states.get(select_entity).state == "Default"
