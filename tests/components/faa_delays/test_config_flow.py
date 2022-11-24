"""Test the FAA Delays config flow."""
from unittest.mock import patch

from aiohttp import ClientConnectionError
import faadelays

from spencerassistant import config_entries, data_entry_flow
from spencerassistant.components.faa_delays.const import DOMAIN
from spencerassistant.const import CONF_ID
from spencerassistant.exceptions import spencerAssistantError

from tests.common import MockConfigEntry


async def mock_valid_airport(self, *args, **kwargs):
    """Return a valid airport."""
    self.name = "Test airport"


async def test_form(hass):
    """Test we get the form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch.object(faadelays.Airport, "update", new=mock_valid_airport), patch(
        "spencerassistant.components.faa_delays.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Test airport"
    assert result2["data"] == {
        "id": "test",
    }
    await hass.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_error(hass):
    """Test that we handle a duplicate configuration."""
    conf = {CONF_ID: "test"}

    MockConfigEntry(domain=DOMAIN, unique_id="test", data=conf).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=conf
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_form_invalid_airport(hass):
    """Test we handle invalid airport."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "faadelays.Airport.update",
        side_effect=faadelays.InvalidAirport,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {CONF_ID: "invalid_airport"}


async def test_form_cannot_connect(hass):
    """Test we handle a connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("faadelays.Airport.update", side_effect=ClientConnectionError):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unexpected_exception(hass):
    """Test we handle an unexpected exception."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("faadelays.Airport.update", side_effect=spencerAssistantError):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "id": "test",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}
