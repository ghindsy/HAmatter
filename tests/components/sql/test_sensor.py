"""The test for the sql sensor platform."""
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from spencerassistant.components.sql.const import DOMAIN
from spencerassistant.config_entries import SOURCE_USER
from spencerassistant.const import CONF_NAME, STATE_UNKNOWN
from spencerassistant.core import spencerAssistant
from spencerassistant.helpers.entity_component import async_update_entity
from spencerassistant.setup import async_setup_component

from . import init_integration

from tests.common import MockConfigEntry


async def test_query(hass: spencerAssistant) -> None:
    """Test the SQL sensor."""
    config = {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value",
        "column": "value",
        "name": "Select value SQL query",
    }
    await init_integration(hass, config)

    state = hass.states.get("sensor.select_value_sql_query")
    assert state.state == "5"
    assert state.attributes["value"] == 5


async def test_import_query(hass: spencerAssistant) -> None:
    """Test the SQL sensor."""
    config = {
        "sensor": {
            "platform": "sql",
            "db_url": "sqlite://",
            "queries": [
                {
                    "name": "count_tables",
                    "query": "SELECT 5 as value",
                    "column": "value",
                }
            ],
        }
    }

    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN)
    options = hass.config_entries.async_entries(DOMAIN)[0].options
    assert options[CONF_NAME] == "count_tables"


async def test_query_value_template(hass: spencerAssistant) -> None:
    """Test the SQL sensor."""
    config = {
        "db_url": "sqlite://",
        "query": "SELECT 5.01 as value",
        "column": "value",
        "name": "count_tables",
        "value_template": "{{ value | int }}",
    }
    await init_integration(hass, config)

    state = hass.states.get("sensor.count_tables")
    assert state.state == "5"


async def test_query_value_template_invalid(hass: spencerAssistant) -> None:
    """Test the SQL sensor."""
    config = {
        "db_url": "sqlite://",
        "query": "SELECT 5.01 as value",
        "column": "value",
        "name": "count_tables",
        "value_template": "{{ value | dontwork }}",
    }
    await init_integration(hass, config)

    state = hass.states.get("sensor.count_tables")
    assert state.state == "5.01"


async def test_query_limit(hass: spencerAssistant) -> None:
    """Test the SQL sensor with a query containing 'LIMIT' in lowercase."""
    config = {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value limit 1",
        "column": "value",
        "name": "Select value SQL query",
    }
    await init_integration(hass, config)

    state = hass.states.get("sensor.select_value_sql_query")
    assert state.state == "5"
    assert state.attributes["value"] == 5


async def test_query_no_value(
    hass: spencerAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the SQL sensor with a query that returns no value."""
    config = {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value where 1=2",
        "column": "value",
        "name": "count_tables",
    }
    await init_integration(hass, config)

    state = hass.states.get("sensor.count_tables")
    assert state.state == STATE_UNKNOWN

    text = "SELECT 5 as value where 1=2 LIMIT 1; returned no results"
    assert text in caplog.text


async def test_query_mssql_no_result(
    hass: spencerAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the SQL sensor with a query that returns no value."""
    config = {
        "db_url": "mssql://",
        "query": "SELECT 5 as value where 1=2",
        "column": "value",
        "name": "count_tables",
    }
    with patch("spencerassistant.components.sql.sensor.sqlalchemy"), patch(
        "spencerassistant.components.sql.sensor.sqlalchemy.text",
        return_value="SELECT TOP 1 5 as value where 1=2",
    ):
        await init_integration(hass, config)

    state = hass.states.get("sensor.count_tables")
    assert state.state == STATE_UNKNOWN

    text = "SELECT TOP 1 5 AS VALUE WHERE 1=2 returned no results"
    assert text in caplog.text


@pytest.mark.parametrize(
    "url,expected_patterns,not_expected_patterns",
    [
        (
            "sqlite://spencerassistant:hunter2@spencerassistant.local",
            ["sqlite://****:****@spencerassistant.local"],
            ["sqlite://spencerassistant:hunter2@spencerassistant.local"],
        ),
        (
            "sqlite://spencerassistant.local",
            ["sqlite://spencerassistant.local"],
            [],
        ),
    ],
)
async def test_invalid_url_setup(
    hass: spencerAssistant,
    caplog: pytest.LogCaptureFixture,
    url: str,
    expected_patterns: str,
    not_expected_patterns: str,
):
    """Test invalid db url with redacted credentials."""
    config = {
        "db_url": url,
        "query": "SELECT 5 as value",
        "column": "value",
        "name": "count_tables",
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data={},
        options=config,
        entry_id="1",
    )

    entry.add_to_hass(hass)

    with patch(
        "spencerassistant.components.sql.sensor.sqlalchemy.create_engine",
        side_effect=SQLAlchemyError(url),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    for pattern in not_expected_patterns:
        assert pattern not in caplog.text
    for pattern in expected_patterns:
        assert pattern in caplog.text


async def test_invalid_url_on_update(
    hass: spencerAssistant,
    caplog: pytest.LogCaptureFixture,
):
    """Test invalid db url with redacted credentials on retry."""
    config = {
        "db_url": "sqlite://",
        "query": "SELECT 5 as value",
        "column": "value",
        "name": "count_tables",
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data={},
        options=config,
        entry_id="1",
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "spencerassistant.components.sql.sensor.sqlalchemy.engine.cursor.CursorResult",
        side_effect=SQLAlchemyError(
            "sqlite://spencerassistant:hunter2@spencerassistant.local"
        ),
    ):
        await async_update_entity(hass, "sensor.count_tables")

    assert "sqlite://spencerassistant:hunter2@spencerassistant.local" not in caplog.text
    assert "sqlite://****:****@spencerassistant.local" in caplog.text
