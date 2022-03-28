"""Test the SQL config flow."""
from __future__ import annotations

from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from homeassistant import config_entries
from homeassistant.components.sql.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from . import (
    ENTRY_CONFIG,
    ENTRY_CONFIG_INVALID_QUERY,
    ENTRY_CONFIG_INVALID_TEMPLATE,
    ENTRY_CONFIG_NO_RESULTS,
)

from tests.common import MockConfigEntry


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.sql.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            ENTRY_CONFIG,
        )
        await hass.async_block_till_done()
    print(ENTRY_CONFIG)

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Select value SQL query"
    assert result2["options"] == {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value",
        "column": "value",
        "unit_of_measurement": "MiB",
        "value_template": None,
        "name": "Select value SQL query",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_import_flow_success(hass: HomeAssistant) -> None:
    """Test a successful import of yaml."""

    with patch(
        "homeassistant.components.sql.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=ENTRY_CONFIG,
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Select value SQL query"
    assert result2["options"] == {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value",
        "column": "value",
        "unit_of_measurement": "MiB",
        "value_template": None,
        "name": "Select value SQL query",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_import_flow_already_exist(hass: HomeAssistant) -> None:
    """Test import of yaml already exist."""

    MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_CONFIG,
    ).add_to_hass(hass)

    with patch(
        "homeassistant.components.sql.async_setup_entry",
        return_value=True,
    ):
        result3 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=ENTRY_CONFIG,
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_ABORT
    assert result3["reason"] == "already_configured"


async def test_flow_fails_db_url(hass: HomeAssistant) -> None:
    """Test config flow fails incorrect db url."""
    result4 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result4["type"] == RESULT_TYPE_FORM
    assert result4["step_id"] == config_entries.SOURCE_USER

    with patch(
        "homeassistant.components.sql.config_flow.sqlalchemy.create_engine",
        side_effect=SQLAlchemyError("error_message"),
    ):
        result4 = await hass.config_entries.flow.async_configure(
            result4["flow_id"],
            user_input=ENTRY_CONFIG,
        )

    assert result4["errors"] == {"db_url": "db_url_invalid"}


async def test_flow_fails_invalid_query_and_template(hass: HomeAssistant) -> None:
    """Test config flow fails incorrect db url."""
    result4 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result4["type"] == RESULT_TYPE_FORM
    assert result4["step_id"] == config_entries.SOURCE_USER

    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        user_input=ENTRY_CONFIG_INVALID_QUERY,
    )

    assert result5["type"] == RESULT_TYPE_FORM
    assert result5["errors"] == {
        "query": "query_invalid",
    }

    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        user_input=ENTRY_CONFIG_INVALID_TEMPLATE,
    )

    assert result5["type"] == RESULT_TYPE_FORM
    assert result5["errors"] == {
        "value_template": "value_template_invalid",
    }

    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        user_input=ENTRY_CONFIG_NO_RESULTS,
    )

    assert result5["type"] == RESULT_TYPE_FORM
    assert result5["errors"] == {
        "query": "query_invalid",
    }

    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        user_input=ENTRY_CONFIG,
    )

    assert result5["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result5["title"] == "Select value SQL query"
    assert result5["options"] == {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value",
        "column": "value",
        "unit_of_measurement": "MiB",
        "value_template": None,
        "name": "Select value SQL query",
    }


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options config flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "db_url": "sqlite://",
            "query": "SELECT 5 as value",
            "column": "value",
            "unit_of_measurement": "MiB",
            "value_template": None,
            "name": "Select value SQL query",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.sql.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "db_url": "sqlite://",
            "query": "SELECT 5 as size",
            "column": "size",
            "unit_of_measurement": "MiB",
        },
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == {
        "db_url": "sqlite://",
        "query": "SELECT 5 as size",
        "column": "size",
        "unit_of_measurement": "MiB",
    }


async def test_options_flow_fails_db_url(hass: HomeAssistant) -> None:
    """Test options flow fails incorrect db url."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "db_url": "sqlite://",
            "query": "SELECT 5 as value",
            "column": "value",
            "unit_of_measurement": "MiB",
            "value_template": None,
            "name": "Select value SQL query",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.sql.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "homeassistant.components.sql.config_flow.sqlalchemy.create_engine",
        side_effect=SQLAlchemyError("error_message"),
    ):
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                "db_url": "sqlite://",
                "query": "SELECT 5 as size",
                "column": "size",
                "unit_of_measurement": "MiB",
            },
        )

    assert result2["errors"] == {"db_url": "db_url_invalid"}


async def test_options_flow_fails_invalid_query_and_template(
    hass: HomeAssistant,
) -> None:
    """Test options flow fails incorrect query and template."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "db_url": "sqlite://",
            "query": "SELECT 5 as value",
            "column": "value",
            "unit_of_measurement": "MiB",
            "value_template": None,
            "name": "Select size SQL query",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.sql.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=ENTRY_CONFIG_INVALID_QUERY,
    )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {
        "query": "query_invalid",
    }

    result3 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=ENTRY_CONFIG_INVALID_TEMPLATE,
    )

    assert result3["type"] == RESULT_TYPE_FORM
    assert result3["errors"] == {
        "value_template": "value_template_invalid",
    }

    result4 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "db_url": "sqlite://",
            "query": "SELECT 5 as size",
            "column": "size",
            "unit_of_measurement": "MiB",
        },
    )

    assert result4["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result4["data"] == {
        "db_url": "sqlite://",
        "query": "SELECT 5 as size",
        "column": "size",
        "unit_of_measurement": "MiB",
    }
