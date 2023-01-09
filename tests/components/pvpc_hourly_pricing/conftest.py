"""Tests for the pvpc_hourly_pricing integration."""
from http import HTTPStatus

import pytest

from homeassistant.components.pvpc_hourly_pricing import ATTR_TARIFF, DOMAIN
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CURRENCY_EURO,
    ENERGY_KILO_WATT_HOUR,
)

from tests.common import load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

FIXTURE_JSON_PUBLIC_DATA_2023_01_06 = "PVPC_DATA_2023_01_06.json"
FIXTURE_JSON_ESIOS_DATA_PVPC_2023_01_06 = "PRICES_ESIOS_1001_2023_01_06.json"
FIXTURE_JSON_ESIOS_DATA_INYECTION_2023_01_06 = "PRICES_ESIOS_1739_2023_01_06.json"
FIXTURE_JSON_ESIOS_DATA_MAG_2023_01_06 = "PRICES_ESIOS_1900_2023_01_06.json"
FIXTURE_JSON_ESIOS_DATA_OMIE_2023_01_06 = "PRICES_ESIOS_10211_2023_01_06.json"


def check_valid_state(state, tariff: str, value=None, key_attr=None):
    """Ensure that sensor has a valid state and attributes."""
    assert state
    assert (
        state.attributes[ATTR_UNIT_OF_MEASUREMENT]
        == f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}"
    )
    try:
        _ = float(state.state)
        # safety margins for current electricity price (it shouldn't be out of [0, 0.2])
        assert -0.1 < float(state.state) < 0.5
        assert state.attributes[ATTR_TARIFF] == tariff
    except ValueError:
        pass

    if value is not None and isinstance(value, str):
        assert state.state == value
    elif value is not None:
        assert abs(float(state.state) - value) < 1e-6
    if key_attr is not None:
        assert abs(float(state.state) - state.attributes[key_attr]) < 1e-6


@pytest.fixture
def pvpc_aioclient_mock(aioclient_mock: AiohttpClientMocker):
    """Create a mock config entry."""
    mask_url_public = (
        "https://api.esios.ree.es/archives/70/download_json?locale=es&date={0}"
    )
    mask_url_esios = "https://api.esios.ree.es/indicators/{0}?start_date={1}T00:00&end_date={1}T23:59"

    # set daily data examples
    example_day = "2023-01-06"
    aioclient_mock.get(
        mask_url_public.format(example_day),
        text=load_fixture(f"{DOMAIN}/{FIXTURE_JSON_PUBLIC_DATA_2023_01_06}"),
    )
    aioclient_mock.get(
        mask_url_esios.format("1001", example_day),
        text=load_fixture(f"{DOMAIN}/{FIXTURE_JSON_ESIOS_DATA_PVPC_2023_01_06}"),
    )
    aioclient_mock.get(
        mask_url_esios.format("1739", example_day),
        text=load_fixture(f"{DOMAIN}/{FIXTURE_JSON_ESIOS_DATA_INYECTION_2023_01_06}"),
    )
    aioclient_mock.get(
        mask_url_esios.format("1900", example_day),
        text=load_fixture(f"{DOMAIN}/{FIXTURE_JSON_ESIOS_DATA_MAG_2023_01_06}"),
    )
    aioclient_mock.get(
        mask_url_esios.format("10211", example_day),
        text=load_fixture(f"{DOMAIN}/{FIXTURE_JSON_ESIOS_DATA_OMIE_2023_01_06}"),
    )
    # simulate missing days
    aioclient_mock.get(
        mask_url_public.format("2023-01-07"),
        status=HTTPStatus.BAD_GATEWAY,
        text=(
            '{"errors":[{"code":502,"status":"502","title":"Bad response from ESIOS",'
            '"detail":"There are no data for the selected filters."}]}'
        ),
    )
    # simulate bad authentication
    for esios_ind in ("1001", "1739", "1900", "10211"):
        aioclient_mock.get(
            mask_url_esios.format(esios_ind, "2023-01-09"),
            status=HTTPStatus.UNAUTHORIZED,
            text="HTTP Token: Access denied.",
        )

    return aioclient_mock
