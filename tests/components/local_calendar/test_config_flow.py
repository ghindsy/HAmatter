"""Test the Local Calendar config flow."""

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from random import getrandbits
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from homeassistant import config_entries
from homeassistant.components import local_calendar
from homeassistant.components.local_calendar.const import (
    CONF_CALENDAR_NAME,
    CONF_ICS_FILE,
    CONF_IMPORT_ICS,
    CONF_STORAGE_KEY,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.fixture
def mock_process_uploaded_file() -> Generator[MagicMock, None, None]:
    """Mock upload ics file."""
    file_id_ics = str(uuid4())
    tmp_path = f"home-assistant-local_calendar-test-{getrandbits(10):03x}"

    @contextmanager
    def _mock_process_uploaded_file(hass: HomeAssistant) -> Iterator[Path | None]:
        with open(tmp_path / "test.ics", "wb") as icsfile:
            icsfile.write(b"""BEGIN:VCALENDAR
                                VERSION:2.0
                                PRODID:-//hacksw/handcal//NONSGML v1.0//EN
                                END:VCALENDAR
                              """)
        yield tmp_path / "test.ics"

    with patch(
        "homeassistant.components.local_calendar.process_uploaded_file",
        side_effect=_mock_process_uploaded_file,
    ) as mock_upload:
        mock_upload.file_id = {
            local_calendar.CONF_ICS_FILE: file_id_ics,
        }
        yield mock_upload


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.local_calendar.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CALENDAR_NAME: "My Calendar",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "My Calendar"
    assert result2["data"] == {
        CONF_CALENDAR_NAME: "My Calendar",
        CONF_STORAGE_KEY: "my_calendar",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_import_ics(
    hass: HomeAssistant,
    mock_process_uploaded_file: MagicMock,
) -> None:
    """Test we get the import form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.local_calendar.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CALENDAR_NAME: "My Calendar", CONF_IMPORT_ICS: True},
        )
        assert result2["type"] is FlowResultType.FORM

    with patch(
        "homeassistant.components.local_calendar.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        file_id = mock_process_uploaded_file.file_id
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ICS_FILE: file_id[CONF_ICS_FILE]},
        )
        await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_name(
    hass: HomeAssistant, setup_integration: None, config_entry: MockConfigEntry
) -> None:
    """Test two calendars cannot be added with the same name."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result.get("errors")

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            # Pick a name that has the same slugify value as an existing config entry
            CONF_CALENDAR_NAME: "light schedule",
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
