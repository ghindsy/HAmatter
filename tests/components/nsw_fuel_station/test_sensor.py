"""The tests for the NSW Fuel Station sensor platform."""
from homeassistant.components import sensor
from homeassistant.components.nsw_fuel_station import DOMAIN
from homeassistant.setup import async_setup_component

from tests.async_mock import patch
from tests.common import assert_setup_component

VALID_CONFIG = {
    "platform": "nsw_fuel_station",
    "station_id": 350,
    "fuel_types": ["E10", "P95"],
}


class MockPrice:
    """Mock Price implementation."""

    def __init__(self, price, fuel_type, last_updated, price_unit, station_code):
        """Initialize a mock price instance."""
        self.price = price
        self.fuel_type = fuel_type
        self.last_updated = last_updated
        self.price_unit = price_unit
        self.station_code = station_code


class MockStation:
    """Mock Station implementation."""

    def __init__(self, name, code):
        """Initialize a mock Station instance."""
        self.name = name
        self.code = code


class MockGetFuelPricesResponse:
    """Mock GetFuelPricesResponse implementation."""

    def __init__(self, prices, stations):
        """Initialize a mock GetFuelPricesResponse instance."""
        self.prices = prices
        self.stations = stations


class FuelCheckClientMock:
    """Mock FuelCheckClient implementation."""

    def get_fuel_prices(self):
        """Return a mock fuel prices response."""
        return MockGetFuelPricesResponse(
            prices=[
                MockPrice(
                    price=150.0,
                    fuel_type="P95",
                    last_updated=None,
                    price_unit=None,
                    station_code=350,
                ),
                MockPrice(
                    price=140.0,
                    fuel_type="E10",
                    last_updated=None,
                    price_unit=None,
                    station_code=350,
                ),
            ],
            stations=[MockStation(code=350, name="My Fake Station")],
        )


@patch(
    "homeassistant.components.nsw_fuel_station.FuelCheckClient",
    new=FuelCheckClientMock,
)
async def test_setup(hass):
    """Test the setup with custom settings."""
    assert await async_setup_component(hass, DOMAIN, {})
    with assert_setup_component(1, sensor.DOMAIN):
        assert await async_setup_component(
            hass, sensor.DOMAIN, {"sensor": VALID_CONFIG}
        )
        await hass.async_block_till_done()

    fake_entities = ["my_fake_station_p95", "my_fake_station_e10"]

    for entity_id in fake_entities:
        state = hass.states.get(f"sensor.{entity_id}")
        assert state is not None


@patch(
    "homeassistant.components.nsw_fuel_station.FuelCheckClient",
    new=FuelCheckClientMock,
)
async def test_sensor_values(hass):
    """Test retrieval of sensor values."""
    assert await async_setup_component(hass, DOMAIN, {})
    assert await async_setup_component(hass, sensor.DOMAIN, {"sensor": VALID_CONFIG})
    await hass.async_block_till_done()

    assert "140.0" == hass.states.get("sensor.my_fake_station_e10").state
    assert "150.0" == hass.states.get("sensor.my_fake_station_p95").state
