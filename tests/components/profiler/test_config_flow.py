"""Test the Profiler config flow."""
from unittest.mock import patch

from spencerassistant import config_entries
from spencerassistant.components.profiler.const import DOMAIN

from tests.common import MockConfigEntry


async def test_form_user(hass):
    """Test we can setup by the user."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] is None

    with patch(
        "spencerassistant.components.profiler.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Profiler"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_user_only_once(hass):
    """Test we can setup by the user only once."""
    MockConfigEntry(domain=DOMAIN).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"
