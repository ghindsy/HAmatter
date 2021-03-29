"""Test the Waze Travel Time config flow."""
from unittest.mock import patch

import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.waze_travel_time.const import (
    CONF_AVOID_FERRIES,
    CONF_AVOID_SUBSCRIPTION_ROADS,
    CONF_AVOID_TOLL_ROADS,
    CONF_DESTINATION,
    CONF_EXCL_FILTER,
    CONF_INCL_FILTER,
    CONF_ORIGIN,
    CONF_REALTIME,
    CONF_UNITS,
    CONF_VEHICLE_TYPE,
    DEFAULT_NAME,
    DOMAIN,
)
from homeassistant.const import CONF_REGION, CONF_UNIT_SYSTEM_IMPERIAL
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


async def test_minimum_fields(hass: HomeAssistant):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.waze_travel_time.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.waze_travel_time.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ORIGIN: "location1",
                CONF_DESTINATION: "location2",
                CONF_REGION: "US",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == f"{DEFAULT_NAME}: location1 -> location2"
    assert result2["data"] == {
        CONF_ORIGIN: "location1",
        CONF_DESTINATION: "location2",
        CONF_REGION: "US",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_options(hass: HomeAssistant):
    """Test options flow."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ORIGIN: "location1",
            CONF_DESTINATION: "location2",
            CONF_REGION: "US",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id, data=None)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_AVOID_FERRIES: True,
            CONF_AVOID_SUBSCRIPTION_ROADS: True,
            CONF_AVOID_TOLL_ROADS: True,
            CONF_EXCL_FILTER: "exclude",
            CONF_INCL_FILTER: "include",
            CONF_REALTIME: False,
            CONF_UNITS: CONF_UNIT_SYSTEM_IMPERIAL,
            CONF_VEHICLE_TYPE: "taxi",
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"] == {
        CONF_AVOID_FERRIES: True,
        CONF_AVOID_SUBSCRIPTION_ROADS: True,
        CONF_AVOID_TOLL_ROADS: True,
        CONF_EXCL_FILTER: "exclude",
        CONF_INCL_FILTER: "include",
        CONF_REALTIME: False,
        CONF_UNITS: CONF_UNIT_SYSTEM_IMPERIAL,
        CONF_VEHICLE_TYPE: "taxi",
    }

    assert entry.options == {
        CONF_AVOID_FERRIES: True,
        CONF_AVOID_SUBSCRIPTION_ROADS: True,
        CONF_AVOID_TOLL_ROADS: True,
        CONF_EXCL_FILTER: "exclude",
        CONF_INCL_FILTER: "include",
        CONF_REALTIME: False,
        CONF_UNITS: CONF_UNIT_SYSTEM_IMPERIAL,
        CONF_VEHICLE_TYPE: "taxi",
    }


async def test_import(hass: HomeAssistant):
    """Test import for config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_ORIGIN: "location1",
            CONF_DESTINATION: "location2",
            CONF_REGION: "US",
            CONF_AVOID_FERRIES: True,
            CONF_AVOID_SUBSCRIPTION_ROADS: True,
            CONF_AVOID_TOLL_ROADS: True,
            CONF_EXCL_FILTER: "exclude",
            CONF_INCL_FILTER: "include",
            CONF_REALTIME: False,
            CONF_UNITS: CONF_UNIT_SYSTEM_IMPERIAL,
            CONF_VEHICLE_TYPE: "taxi",
        },
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data == {
        CONF_ORIGIN: "location1",
        CONF_DESTINATION: "location2",
        CONF_REGION: "US",
    }
    assert entry.options == {
        CONF_AVOID_FERRIES: True,
        CONF_AVOID_SUBSCRIPTION_ROADS: True,
        CONF_AVOID_TOLL_ROADS: True,
        CONF_EXCL_FILTER: "exclude",
        CONF_INCL_FILTER: "include",
        CONF_REALTIME: False,
        CONF_UNITS: CONF_UNIT_SYSTEM_IMPERIAL,
        CONF_VEHICLE_TYPE: "taxi",
    }


async def test_dupe_id(hass):
    """Test setting up the same entry twice fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.waze_travel_time.async_setup", return_value=True
    ), patch(
        "homeassistant.components.waze_travel_time.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ORIGIN: "location1",
                CONF_DESTINATION: "location2",
                CONF_REGION: "US",
            },
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] is None

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ORIGIN: "location1",
                CONF_DESTINATION: "location2",
                CONF_REGION: "US",
            },
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result2["reason"] == "already_configured"
