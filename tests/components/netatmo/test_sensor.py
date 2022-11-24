"""The tests for the Netatmo sensor platform."""
from unittest.mock import patch

import pytest

from spencerassistant.components.netatmo import sensor
from spencerassistant.helpers import entity_registry as er

from .common import TEST_TIME, selected_platforms


async def test_weather_sensor(hass, config_entry, netatmo_auth):
    """Test weather sensor setup."""
    with patch("time.time", return_value=TEST_TIME), selected_platforms(["sensor"]):
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

    prefix = "sensor.parents_bedroom_"

    assert hass.states.get(f"{prefix}temperature").state == "20.3"
    assert hass.states.get(f"{prefix}humidity").state == "63"
    assert hass.states.get(f"{prefix}co2").state == "494"
    assert hass.states.get(f"{prefix}pressure").state == "1014.5"


async def test_public_weather_sensor(hass, config_entry, netatmo_auth):
    """Test public weather sensor setup."""
    with patch("time.time", return_value=TEST_TIME), selected_platforms(["sensor"]):
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

    assert len(hass.states.async_all()) > 0

    prefix = "sensor.spencer_max_"

    assert hass.states.get(f"{prefix}temperature").state == "27.4"
    assert hass.states.get(f"{prefix}humidity").state == "76"
    assert hass.states.get(f"{prefix}pressure").state == "1014.4"

    prefix = "sensor.spencer_avg_"

    assert hass.states.get(f"{prefix}temperature").state == "22.7"
    assert hass.states.get(f"{prefix}humidity").state == "63.2"
    assert hass.states.get(f"{prefix}pressure").state == "1010.3"

    entities_before_change = len(hass.states.async_all())

    valid_option = {
        "lat_ne": 32.91336,
        "lon_ne": -117.187429,
        "lat_sw": 32.83336,
        "lon_sw": -117.26743,
        "show_on_map": True,
        "area_name": "spencer avg",
        "mode": "max",
    }

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"new_area": "spencer avg"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=valid_option
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )

    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == entities_before_change
    assert hass.states.get(f"{prefix}temperature").state == "27.4"


@pytest.mark.parametrize(
    "strength, expected",
    [(50, "Full"), (60, "High"), (80, "Medium"), (90, "Low")],
)
async def test_process_wifi(strength, expected):
    """Test wifi strength translation."""
    assert sensor.process_wifi(strength) == expected


@pytest.mark.parametrize(
    "strength, expected",
    [(50, "Full"), (70, "High"), (80, "Medium"), (90, "Low")],
)
async def test_process_rf(strength, expected):
    """Test radio strength translation."""
    assert sensor.process_rf(strength) == expected


@pytest.mark.parametrize(
    "health, expected",
    [(4, "Unhealthy"), (3, "Poor"), (2, "Fair"), (1, "Fine"), (0, "Healthy")],
)
async def test_process_health(health, expected):
    """Test health index translation."""
    assert sensor.process_health(health) == expected


@pytest.mark.parametrize(
    "uid, name, expected",
    [
        ("12:34:56:03:1b:e4-reachable", "villa_garden_reachable", "True"),
        ("12:34:56:03:1b:e4-rf_status", "villa_garden_radio", "Full"),
        (
            "12:34:56:80:bb:26-wifi_status",
            "villa_wifi_strength",
            "High",
        ),
        (
            "12:34:56:80:bb:26-temp_trend",
            "villa_temperature_trend",
            "stable",
        ),
        (
            "12:34:56:80:bb:26-pressure_trend",
            "villa_pressure_trend",
            "up",
        ),
        ("12:34:56:80:c1:ea-sum_rain_1", "villa_rain_rain_last_hour", "0"),
        ("12:34:56:80:c1:ea-sum_rain_24", "villa_rain_rain_today", "6.9"),
        ("12:34:56:03:1b:e4-windangle", "netatmoindoor_garden_direction", "SW"),
        (
            "12:34:56:03:1b:e4-windangle_value",
            "netatmoindoor_garden_angle",
            "217",
        ),
        ("12:34:56:03:1b:e4-gustangle", "mystation_garden_gust_direction", "S"),
        (
            "12:34:56:03:1b:e4-gustangle",
            "netatmoindoor_garden_gust_direction",
            "S",
        ),
        (
            "12:34:56:03:1b:e4-gustangle_value",
            "netatmoindoor_garden_gust_angle",
            "206",
        ),
        (
            "12:34:56:03:1b:e4-guststrength",
            "netatmoindoor_garden_gust_strength",
            "9",
        ),
        (
            "12:34:56:03:1b:e4-rf_status",
            "netatmoindoor_garden_rf_strength",
            "Full",
        ),
        (
            "12:34:56:26:68:92-health_idx",
            "baby_bedroom_health",
            "Fine",
        ),
        (
            "12:34:56:26:68:92-wifi_status",
            "baby_bedroom_wifi",
            "High",
        ),
        ("spencer-max-windangle_value", "spencer_max_wind_angle", "17"),
        ("spencer-max-gustangle_value", "spencer_max_gust_angle", "217"),
        ("spencer-max-guststrength", "spencer_max_gust_strength", "31"),
        ("spencer-max-sum_rain_1", "spencer_max_sum_rain_1", "0.2"),
    ],
)
async def test_weather_sensor_enabling(
    hass, config_entry, uid, name, expected, netatmo_auth
):
    """Test enabling of by default disabled sensors."""
    with patch("time.time", return_value=TEST_TIME), selected_platforms(["sensor"]):
        states_before = len(hass.states.async_all())
        assert hass.states.get(f"sensor.{name}") is None

        registry = er.async_get(hass)
        registry.async_get_or_create(
            "sensor",
            "netatmo",
            uid,
            suggested_object_id=name,
            disabled_by=None,
        )
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

        assert len(hass.states.async_all()) > states_before
        assert hass.states.get(f"sensor.{name}").state == expected


async def test_climate_battery_sensor(hass, config_entry, netatmo_auth):
    """Test climate device battery sensor."""
    with patch("time.time", return_value=TEST_TIME), selected_platforms(
        ["sensor", "climate"]
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

    prefix = "sensor.livingroom_"

    assert hass.states.get(f"{prefix}battery_percent").state == "75"
