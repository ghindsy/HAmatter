"""The tests for time_date sensor platform."""

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.components.time_date.const import DOMAIN
import homeassistant.components.time_date.sensor as time_date
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util


async def test_intervals(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Test timing intervals of sensors."""
    device = time_date.TimeDateSensor(hass, "time")
    now = dt_util.utc_from_timestamp(45.5)
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time == dt_util.utc_from_timestamp(60)

    device = time_date.TimeDateSensor(hass, "beat")
    now = dt_util.parse_datetime("2020-11-13 00:00:29+01:00")
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time == dt_util.parse_datetime("2020-11-13 00:01:26.4+01:00")

    device = time_date.TimeDateSensor(hass, "date_time")
    now = dt_util.utc_from_timestamp(1495068899)
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time == dt_util.utc_from_timestamp(1495068900)

    now = dt_util.utcnow()
    device = time_date.TimeDateSensor(hass, "time_date")
    next_time = device.get_next_interval()
    assert next_time > now


async def test_states(hass: HomeAssistant) -> None:
    """Test states of sensors."""
    hass.config.set_time_zone("UTC")

    now = dt_util.utc_from_timestamp(1495068856)
    device = time_date.TimeDateSensor(hass, "time")
    device._update_internal_state(now)
    assert device.state == "00:54"

    device = time_date.TimeDateSensor(hass, "date")
    device._update_internal_state(now)
    assert device.state == "2017-05-18"

    device = time_date.TimeDateSensor(hass, "time_utc")
    device._update_internal_state(now)
    assert device.state == "00:54"

    device = time_date.TimeDateSensor(hass, "date_time")
    device._update_internal_state(now)
    assert device.state == "2017-05-18, 00:54"

    device = time_date.TimeDateSensor(hass, "date_time_utc")
    device._update_internal_state(now)
    assert device.state == "2017-05-18, 00:54"

    device = time_date.TimeDateSensor(hass, "beat")
    device._update_internal_state(now)
    assert device.state == "@079"
    device._update_internal_state(dt_util.utc_from_timestamp(1602952963.2))
    assert device.state == "@738"

    device = time_date.TimeDateSensor(hass, "date_time_iso")
    device._update_internal_state(now)
    assert device.state == "2017-05-18T00:54:00"


async def test_states_non_default_timezone(hass: HomeAssistant) -> None:
    """Test states of sensors in a timezone other than UTC."""
    hass.config.set_time_zone("America/New_York")

    now = dt_util.utc_from_timestamp(1495068856)
    device = time_date.TimeDateSensor(hass, "time")
    device._update_internal_state(now)
    assert device.state == "20:54"

    device = time_date.TimeDateSensor(hass, "date")
    device._update_internal_state(now)
    assert device.state == "2017-05-17"

    device = time_date.TimeDateSensor(hass, "time_utc")
    device._update_internal_state(now)
    assert device.state == "00:54"

    device = time_date.TimeDateSensor(hass, "date_time")
    device._update_internal_state(now)
    assert device.state == "2017-05-17, 20:54"

    device = time_date.TimeDateSensor(hass, "date_time_utc")
    device._update_internal_state(now)
    assert device.state == "2017-05-18, 00:54"

    device = time_date.TimeDateSensor(hass, "beat")
    device._update_internal_state(now)
    assert device.state == "@079"

    device = time_date.TimeDateSensor(hass, "date_time_iso")
    device._update_internal_state(now)
    assert device.state == "2017-05-17T20:54:00"


async def test_timezone_intervals(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Test date sensor behavior in a timezone besides UTC."""
    hass.config.set_time_zone("America/New_York")

    device = time_date.TimeDateSensor(hass, "date")
    now = dt_util.utc_from_timestamp(50000)
    freezer.move_to(now)
    next_time = device.get_next_interval()
    # start of local day in EST was 18000.0
    # so the second day was 18000 + 86400
    assert next_time.timestamp() == 104400

    hass.config.set_time_zone("America/Edmonton")
    now = dt_util.parse_datetime("2017-11-13 19:47:19-07:00")
    device = time_date.TimeDateSensor(hass, "date")
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time.timestamp() == dt_util.as_timestamp("2017-11-14 00:00:00-07:00")

    # Entering DST
    hass.config.set_time_zone("Europe/Prague")

    now = dt_util.parse_datetime("2020-03-29 00:00+01:00")
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time.timestamp() == dt_util.as_timestamp("2020-03-30 00:00+02:00")

    now = dt_util.parse_datetime("2020-03-29 03:00+02:00")
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time.timestamp() == dt_util.as_timestamp("2020-03-30 00:00+02:00")

    # Leaving DST
    now = dt_util.parse_datetime("2020-10-25 00:00+02:00")
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time.timestamp() == dt_util.as_timestamp("2020-10-26 00:00:00+01:00")

    now = dt_util.parse_datetime("2020-10-25 23:59+01:00")
    freezer.move_to(now)
    next_time = device.get_next_interval()
    assert next_time.timestamp() == dt_util.as_timestamp("2020-10-26 00:00:00+01:00")


async def test_timezone_intervals_empty_parameter(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Test get_interval() without parameters."""
    freezer.move_to(dt_util.parse_datetime("2017-11-14 02:47:19-00:00"))
    hass.config.set_time_zone("America/Edmonton")
    device = time_date.TimeDateSensor(hass, "date")
    next_time = device.get_next_interval()
    assert next_time.timestamp() == dt_util.as_timestamp("2017-11-14 00:00:00-07:00")


async def test_icons(hass: HomeAssistant) -> None:
    """Test attributes of sensors."""
    device = time_date.TimeDateSensor(hass, "time")
    assert device.icon == "mdi:clock"
    device = time_date.TimeDateSensor(hass, "date")
    assert device.icon == "mdi:calendar"
    device = time_date.TimeDateSensor(hass, "date_time")
    assert device.icon == "mdi:calendar-clock"
    device = time_date.TimeDateSensor(hass, "date_time_utc")
    assert device.icon == "mdi:calendar-clock"
    device = time_date.TimeDateSensor(hass, "date_time_iso")
    assert device.icon == "mdi:calendar-clock"


@pytest.mark.parametrize(
    (
        "display_options",
        "expected_warnings",
        "expected_issues",
    ),
    [
        (["time", "date"], [], []),
        (["beat"], ["'beat': is deprecated"], ["deprecated_beat"]),
        (["time", "beat"], ["'beat': is deprecated"], ["deprecated_beat"]),
    ],
)
async def test_deprecation_warning(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    display_options: list[str],
    expected_warnings: list[str],
    expected_issues: list[str],
) -> None:
    """Test deprecation warning for swatch beat."""
    config = {"sensor": {"platform": "time_date", "display_options": display_options}}

    await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()

    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warnings) == len(expected_warnings)
    for expected_warning in expected_warnings:
        assert any(expected_warning in warning.message for warning in warnings)

    issue_registry = ir.async_get(hass)
    assert len(issue_registry.issues) == len(expected_issues)
    for expected_issue in expected_issues:
        assert (DOMAIN, expected_issue) in issue_registry.issues
