"""Test the Bryant Evolution config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.components.bryant_evolution.const import (
    CONF_SYSTEM_ID,
    CONF_ZONE_ID,
    DOMAIN,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "evolutionhttp.BryantEvolutionClient.read_hvac_mode",
        return_value="COOL",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_SYSTEM_ID: 1,
                CONF_ZONE_ID: 2,
            },
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "System 1 Zone 2"
    assert result["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_SYSTEM_ID: 1,
        CONF_ZONE_ID: 2,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "evolutionhttp.BryantEvolutionClient.read_hvac_mode",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_SYSTEM_ID: 1,
                CONF_ZONE_ID: 2,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    # Make sure the config flow tests finish with either an
    # FlowResultType.CREATE_ENTRY or FlowResultType.ABORT so
    # we can show the config flow is able to recover from an error.

    with patch(
        "evolutionhttp.BryantEvolutionClient.read_hvac_mode",
        return_value="COOL",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_SYSTEM_ID: 1,
                CONF_ZONE_ID: 2,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "System 1 Zone 2"
    assert result["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_SYSTEM_ID: 1,
        CONF_ZONE_ID: 2,
    }
    assert len(mock_setup_entry.mock_calls) == 1
