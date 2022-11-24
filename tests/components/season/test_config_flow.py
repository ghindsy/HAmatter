"""Tests for the Season config flow."""
from unittest.mock import MagicMock

import pytest

from spencerassistant.components.season.const import (
    DOMAIN,
    TYPE_ASTRONOMICAL,
    TYPE_METEOROLOGICAL,
)
from spencerassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from spencerassistant.const import CONF_NAME, CONF_TYPE
from spencerassistant.core import spencerAssistant
from spencerassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(
    hass: spencerAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test the full user configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == SOURCE_USER
    assert "flow_id" in result

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_TYPE: TYPE_ASTRONOMICAL},
    )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "Season"
    assert result2.get("data") == {CONF_TYPE: TYPE_ASTRONOMICAL}


@pytest.mark.parametrize("source", [SOURCE_USER, SOURCE_IMPORT])
async def test_single_instance_allowed(
    hass: spencerAssistant,
    mock_config_entry: MockConfigEntry,
    source: str,
) -> None:
    """Test we abort if already setup."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": source}, data={CONF_TYPE: TYPE_ASTRONOMICAL}
    )

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_import_flow(
    hass: spencerAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test the import configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_NAME: "My Seasons", CONF_TYPE: TYPE_METEOROLOGICAL},
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "My Seasons"
    assert result.get("data") == {CONF_TYPE: TYPE_METEOROLOGICAL}
