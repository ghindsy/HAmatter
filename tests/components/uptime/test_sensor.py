"""The tests for the uptime sensor platform."""
import asyncio
from datetime import timedelta
import unittest

from homeassistant.components.uptime.sensor import UptimeSensor
from homeassistant.setup import async_setup_component

from tests.async_mock import patch
from tests.common import get_test_home_assistant


async def test_uptime_min_config(hass):
    """Test minimum uptime configuration."""
    config = {"sensor": {"platform": "uptime"}}
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.uptime")
    assert state.attributes.get("unit_of_measurement") == "days"


async def test_uptime_sensor_name_change(hass):
    """Test uptime sensor with different name."""
    config = {"sensor": {"platform": "uptime", "name": "foobar"}}
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.foobar")
    assert state.attributes.get("unit_of_measurement") == "days"


async def test_uptime_sensor_config_hours(hass):
    """Test uptime sensor with hours defined in config."""
    config = {"sensor": {"platform": "uptime", "unit_of_measurement": "hours"}}
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.uptime")
    assert state.attributes.get("unit_of_measurement") == "hours"


async def test_uptime_sensor_config_minutes(hass):
    """Test uptime sensor with minutes defined in config."""
    config = {"sensor": {"platform": "uptime", "unit_of_measurement": "minutes"}}
    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.uptime")
    assert state.attributes.get("unit_of_measurement") == "minutes"


class TestUptimeSensor(unittest.TestCase):
    """Test the uptime sensor."""

    def setUp(self):
        """Set up things to run when tests begin."""
        self.hass = get_test_home_assistant()
        self.addCleanup(self.hass.stop)

    def test_uptime_sensor_days_output(self):
        """Test uptime sensor output data."""
        sensor = UptimeSensor("test", "days")
        assert sensor.unit_of_measurement == "days"
        new_time = sensor.initial + timedelta(days=1)
        with patch("homeassistant.util.dt.now", return_value=new_time):
            asyncio.run_coroutine_threadsafe(
                sensor.async_update(), self.hass.loop
            ).result()
            assert sensor.state == 1.00
        new_time = sensor.initial + timedelta(days=111.499)
        with patch("homeassistant.util.dt.now", return_value=new_time):
            asyncio.run_coroutine_threadsafe(
                sensor.async_update(), self.hass.loop
            ).result()
            assert sensor.state == 111.50

    def test_uptime_sensor_hours_output(self):
        """Test uptime sensor output data."""
        sensor = UptimeSensor("test", "hours")
        assert sensor.unit_of_measurement == "hours"
        new_time = sensor.initial + timedelta(hours=16)
        with patch("homeassistant.util.dt.now", return_value=new_time):
            asyncio.run_coroutine_threadsafe(
                sensor.async_update(), self.hass.loop
            ).result()
            assert sensor.state == 16.00
        new_time = sensor.initial + timedelta(hours=72.499)
        with patch("homeassistant.util.dt.now", return_value=new_time):
            asyncio.run_coroutine_threadsafe(
                sensor.async_update(), self.hass.loop
            ).result()
            assert sensor.state == 72.50

    def test_uptime_sensor_minutes_output(self):
        """Test uptime sensor output data."""
        sensor = UptimeSensor("test", "minutes")
        assert sensor.unit_of_measurement == "minutes"
        new_time = sensor.initial + timedelta(minutes=16)
        with patch("homeassistant.util.dt.now", return_value=new_time):
            asyncio.run_coroutine_threadsafe(
                sensor.async_update(), self.hass.loop
            ).result()
            assert sensor.state == 16.00
        new_time = sensor.initial + timedelta(minutes=12.499)
        with patch("homeassistant.util.dt.now", return_value=new_time):
            asyncio.run_coroutine_threadsafe(
                sensor.async_update(), self.hass.loop
            ).result()
            assert sensor.state == 12.50
