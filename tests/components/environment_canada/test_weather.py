"""Test weather."""

import json

from freezegun import freeze_time
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.weather import (
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from homeassistant.core import HomeAssistant

from . import init_integration

from tests.common import load_fixture


@freeze_time("2022-10-04 06:00:00-04:00")
async def test_forecast_daily(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test basic forecast."""
    await hass.config.async_set_time_zone("America/New_York")

    ec_data = json.loads(
        load_fixture("environment_canada/current_conditions_data.json")
    )
    del ec_data["daily_forecasts"][0]
    await init_integration(hass, ec_data)

    response = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {
            "entity_id": "weather.home_forecast",
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@freeze_time("2022-10-04 06:00:00-04:00")
async def test_forecast_daily_with_some_previous_days_data(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test basic forecast."""
    await hass.config.async_set_time_zone("America/New_York")

    ec_data = json.loads(
        load_fixture("environment_canada/current_conditions_data.json")
    )
    await init_integration(hass, ec_data)

    response = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {
            "entity_id": "weather.home_forecast",
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
