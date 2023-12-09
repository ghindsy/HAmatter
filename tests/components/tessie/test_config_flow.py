"""Test the Tessie config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.tessie.const import DOMAIN
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .common import (
    ERROR_AUTH,
    ERROR_CONNECTION,
    ERROR_UNKNOWN,
    TEST_CONFIG,
    TEST_STATE_OF_ALL_VEHICLES,
    setup_platform,
)

from tests.common import MockConfigEntry


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""

    result1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result1["type"] == FlowResultType.FORM
    assert not result1["errors"]

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        return_value=TEST_STATE_OF_ALL_VEHICLES,
    ) as mock_get_state_of_all_vehicles, patch(
        "homeassistant.components.tessie.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result1["flow_id"],
            TEST_CONFIG,
        )
        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1
        assert len(mock_get_state_of_all_vehicles.mock_calls) == 1

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Tessie"
    assert result2["data"] == TEST_CONFIG


async def test_form_invalid_access_token(hass: HomeAssistant) -> None:
    """Test invalid auth is handled."""

    result1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        side_effect=ERROR_AUTH,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result1["flow_id"],
            TEST_CONFIG,
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {CONF_ACCESS_TOKEN: "invalid_access_token"}

    # Complete the flow
    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        return_value=TEST_STATE_OF_ALL_VEHICLES,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            TEST_CONFIG,
        )
    assert result3["type"] == FlowResultType.CREATE_ENTRY


async def test_form_invalid_response(hass: HomeAssistant) -> None:
    """Test invalid auth is handled."""

    result1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        side_effect=ERROR_UNKNOWN,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result1["flow_id"],
            TEST_CONFIG,
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}

    # Complete the flow
    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        return_value=TEST_STATE_OF_ALL_VEHICLES,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            TEST_CONFIG,
        )
    assert result3["type"] == FlowResultType.CREATE_ENTRY


async def test_form_network_issue(hass: HomeAssistant) -> None:
    """Test network issues are handled."""

    result1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        side_effect=ERROR_CONNECTION,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result1["flow_id"],
            TEST_CONFIG,
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}

    # Complete the flow
    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        return_value=TEST_STATE_OF_ALL_VEHICLES,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            TEST_CONFIG,
        )
    assert result3["type"] == FlowResultType.CREATE_ENTRY


async def test_reauth(hass: HomeAssistant) -> None:
    """Test reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CONFIG,
        unique_id="abc",
    )
    mock_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": mock_entry.unique_id,
            "entry_id": mock_entry.entry_id,
        },
        data=TEST_CONFIG,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert not result["errors"]

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        return_value=TEST_STATE_OF_ALL_VEHICLES,
    ) as mock_get_state_of_all_vehicles, patch(
        "homeassistant.components.tessie.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONFIG,
        )
        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1
        assert len(mock_get_state_of_all_vehicles.mock_calls) == 1

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_entry.data == TEST_CONFIG


async def test_reauth_error_auth(hass: HomeAssistant) -> None:
    """Test reauth flow that fails."""
    mock_entry = await setup_platform(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": mock_entry.unique_id,
            "entry_id": mock_entry.entry_id,
        },
        data=TEST_CONFIG,
    )

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        side_effect=ERROR_AUTH,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONFIG,
        )
        await hass.async_block_till_done()

        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "invalid_access_token"}


async def test_reauth_error_unknown(hass: HomeAssistant) -> None:
    """Test reauth flow that fails."""
    mock_entry = await setup_platform(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": mock_entry.unique_id,
            "entry_id": mock_entry.entry_id,
        },
        data=TEST_CONFIG,
    )

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        side_effect=ERROR_UNKNOWN,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONFIG,
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_reauth_error_connection(hass: HomeAssistant) -> None:
    """Test reauth flow that fails."""
    mock_entry = await setup_platform(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": mock_entry.unique_id,
            "entry_id": mock_entry.entry_id,
        },
        data=TEST_CONFIG,
    )

    with patch(
        "homeassistant.components.tessie.config_flow.get_state_of_all_vehicles",
        side_effect=ERROR_CONNECTION,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_CONFIG,
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
