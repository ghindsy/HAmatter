"""Define test fixtures for Enphase Envoy."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import jwt
from pyenphase import (
    Envoy,
    EnvoyData,
    EnvoyEncharge,
    EnvoyEnchargeAggregate,
    EnvoyEnchargePower,
    EnvoyEnpower,
    EnvoyInverter,
    EnvoySystemConsumption,
    EnvoySystemProduction,
    EnvoyTokenAuth,
)
from pyenphase.const import SupportedFeatures
from pyenphase.models.dry_contacts import EnvoyDryContactSettings, EnvoyDryContactStatus
from pyenphase.models.meters import EnvoyMeterData
from pyenphase.models.tariff import EnvoyStorageSettings, EnvoyTariff
import pytest

from homeassistant.components.enphase_envoy import DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, load_json_object_fixture


@pytest.fixture(name="config_entry")
def config_entry_fixture(
    hass: HomeAssistant, config: dict[str, str], serial_number: str
) -> MockConfigEntry:
    """Define a config entry fixture."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="45a36e55aaddb2007c5f6602e0c38e72",
        title=f"Envoy {serial_number}" if serial_number else "Envoy",
        unique_id=serial_number,
        data=config,
    )


@pytest.fixture(name="config")
def config_fixture() -> dict[str, str]:
    """Define a config entry data fixture."""
    return {
        CONF_HOST: "1.1.1.1",
        CONF_NAME: "Envoy 1234",
        CONF_USERNAME: "test-username",
        CONF_PASSWORD: "test-password",
    }


@pytest.fixture(name="mock_envoy")
async def mock_envoy_fixture(
    mock_auth: EnvoyTokenAuth,
    mock_authenticate: AsyncMock,
    mock_setup: AsyncMock,
    request: pytest.FixtureRequest,
    serial_number: str,
) -> AsyncGenerator[AsyncMock, None]:
    """Define a mocked Envoy fixture."""
    mock_envoy = Mock(spec=Envoy)
    # Add the fixtures specified
    mock_envoy.auth = mock_auth
    mock_envoy.authenticate = mock_authenticate
    mock_envoy.close_dry_contact = AsyncMock(return_value={})
    mock_envoy.disable_charge_from_grid = AsyncMock(return_value={})
    mock_envoy.enable_charge_from_grid = AsyncMock(return_value={})
    mock_envoy.go_off_grid = AsyncMock(return_value={})
    mock_envoy.go_on_grid = AsyncMock(return_value={})
    mock_envoy.open_dry_contact = AsyncMock(return_value={})
    mock_envoy.serial_number = serial_number
    mock_envoy.set_reserve_soc = AsyncMock(return_value={})
    mock_envoy.set_storage_mode = AsyncMock(return_value={})
    mock_envoy.setup = mock_setup
    mock_envoy.update_dry_contact = AsyncMock(return_value={})

    # determine fixture file name, default envoy if no request passed
    fixture_name = "envoy"
    if hasattr(request, "param"):
        fixture_name = request.param

    # Load envoy model from fixture
    load_envoy_fixture(mock_envoy, fixture_name)
    mock_envoy.update = AsyncMock(return_value=mock_envoy.data)

    return mock_envoy


@pytest.fixture(name="setup_enphase_envoy")
async def setup_enphase_envoy_fixture(
    hass: HomeAssistant,
    config: dict[str, str],
    mock_envoy: Mock,
) -> AsyncGenerator[None]:
    """Define a fixture to set up Enphase Envoy."""
    with (
        patch(
            "homeassistant.components.enphase_envoy.config_flow.Envoy",
            return_value=mock_envoy,
        ),
        patch(
            "homeassistant.components.enphase_envoy.Envoy",
            return_value=mock_envoy,
        ),
    ):
        yield


@pytest.fixture(name="mock_authenticate")
def mock_authenticate() -> AsyncMock:
    """Define a mocked Envoy.authenticate fixture."""
    return AsyncMock()


@pytest.fixture(name="mock_auth")
def mock_auth(serial_number: str) -> EnvoyTokenAuth:
    """Define a mocked EnvoyAuth fixture."""
    token = jwt.encode(
        payload={"name": "envoy", "exp": 1907837780}, key="secret", algorithm="HS256"
    )
    return EnvoyTokenAuth("127.0.0.1", token=token, envoy_serial=serial_number)


@pytest.fixture(name="mock_setup")
def mock_setup() -> AsyncMock:
    """Define a mocked Envoy.setup fixture."""
    return AsyncMock()


@pytest.fixture(name="serial_number")
def serial_number_fixture() -> str:
    """Define a serial number fixture."""
    return "1234"


def load_envoy_fixture(mock_envoy: AsyncMock, fixture_name: str) -> None:
    """Load envoy model from fixture."""

    json_fixture: dict[str, Any] = load_json_object_fixture(
        f"{fixture_name}.json", DOMAIN
    )

    mock_envoy.firmware = json_fixture["firmware"]
    mock_envoy.part_number = json_fixture["part_number"]
    mock_envoy.envoy_model = json_fixture["envoy_model"]
    mock_envoy.supported_features = SupportedFeatures(
        json_fixture["supported_features"]
    )
    mock_envoy.phase_mode = json_fixture["phase_mode"]
    mock_envoy.phase_count = json_fixture["phase_count"]
    mock_envoy.active_phase_count = json_fixture["active_phase_count"]
    mock_envoy.ct_meter_count = json_fixture["ct_meter_count"]
    mock_envoy.consumption_meter_type = json_fixture["consumption_meter_type"]
    mock_envoy.production_meter_type = json_fixture["production_meter_type"]
    mock_envoy.storage_meter_type = json_fixture["storage_meter_type"]

    mock_envoy.data = EnvoyData()
    _load_json_2_production_data(mock_envoy.data, json_fixture)
    _load_json_2_meter_data(mock_envoy.data, json_fixture)
    _load_json_2_inverter_data(mock_envoy.data, json_fixture)
    _load_json_2_encharge_enpower_data(mock_envoy.data, json_fixture)
    _load_json_2_raw_data(mock_envoy.data, json_fixture)


def _load_json_2_production_data(
    mocked_data: EnvoyData, json_fixture: dict[str, Any]
) -> None:
    """Fill envoy production data from fixture."""
    if item := json_fixture["data"].get("system_consumption"):
        mocked_data.system_consumption = EnvoySystemConsumption(**item)
    if item := json_fixture["data"].get("system_production"):
        mocked_data.system_production = EnvoySystemProduction(**item)
    if item := json_fixture["data"].get("system_consumption_phases"):
        mocked_data.system_consumption_phases = {}
        for sub_item, item_data in item.items():
            mocked_data.system_consumption_phases[sub_item] = EnvoySystemConsumption(
                **item_data
            )
    if item := json_fixture["data"].get("system_production_phases"):
        mocked_data.system_production_phases = {}
        for sub_item, item_data in item.items():
            mocked_data.system_production_phases[sub_item] = EnvoySystemProduction(
                **item_data
            )


def _load_json_2_meter_data(
    mocked_data: EnvoyData, json_fixture: dict[str, Any]
) -> None:
    """Fill envoy meter data from fixture."""
    if item := json_fixture["data"].get("ctmeter_production"):
        mocked_data.ctmeter_production = EnvoyMeterData(**item)
    if item := json_fixture["data"].get("ctmeter_consumption"):
        mocked_data.ctmeter_consumption = EnvoyMeterData(**item)
    if item := json_fixture["data"].get("ctmeter_storage"):
        mocked_data.ctmeter_storage = EnvoyMeterData(**item)
    if item := json_fixture["data"].get("ctmeter_production_phases"):
        mocked_data.ctmeter_production_phases = {}
        for sub_item, item_data in item.items():
            mocked_data.ctmeter_production_phases[sub_item] = EnvoyMeterData(
                **item_data
            )
    if item := json_fixture["data"].get("ctmeter_consumption_phases"):
        mocked_data.ctmeter_consumption_phases = {}
        for sub_item, item_data in item.items():
            mocked_data.ctmeter_consumption_phases[sub_item] = EnvoyMeterData(
                **item_data
            )
    if item := json_fixture["data"].get("ctmeter_storage_phases"):
        mocked_data.ctmeter_storage_phases = {}
        for sub_item, item_data in item.items():
            mocked_data.ctmeter_storage_phases[sub_item] = EnvoyMeterData(**item_data)


def _load_json_2_inverter_data(
    mocked_data: EnvoyData, json_fixture: dict[str, Any]
) -> None:
    """Fill envoy inverter data from fixture."""
    if item := json_fixture["data"].get("inverters"):
        mocked_data.inverters = {}
        for sub_item, item_data in item.items():
            mocked_data.inverters[sub_item] = EnvoyInverter(**item_data)


def _load_json_2_encharge_enpower_data(
    mocked_data: EnvoyData, json_fixture: dict[str, Any]
) -> None:
    """Fill envoy encharge/enpower data from fixture."""
    if item := json_fixture["data"].get("encharge_inventory"):
        mocked_data.encharge_inventory = {}
        for sub_item, item_data in item.items():
            mocked_data.encharge_inventory[sub_item] = EnvoyEncharge(**item_data)
    if item := json_fixture["data"].get("enpower"):
        mocked_data.enpower = EnvoyEnpower(**item)
    if item := json_fixture["data"].get("encharge_aggregate"):
        mocked_data.encharge_aggregate = EnvoyEnchargeAggregate(**item)
    if item := json_fixture["data"].get("encharge_power"):
        mocked_data.encharge_power = {}
        for sub_item, item_data in item.items():
            mocked_data.encharge_power[sub_item] = EnvoyEnchargePower(**item_data)
    if item := json_fixture["data"].get("tariff"):
        mocked_data.tariff = EnvoyTariff(**item)
        mocked_data.tariff.storage_settings = EnvoyStorageSettings(
            **item["storage_settings"]
        )
    if item := json_fixture["data"].get("dry_contact_status"):
        mocked_data.dry_contact_status = {}
        for sub_item, item_data in item.items():
            mocked_data.dry_contact_status[sub_item] = EnvoyDryContactStatus(
                **item_data
            )
    if item := json_fixture["data"].get("dry_contact_settings"):
        mocked_data.dry_contact_settings = {}
        for sub_item, item_data in item.items():
            mocked_data.dry_contact_settings[sub_item] = EnvoyDryContactSettings(
                **item_data
            )


def _load_json_2_raw_data(mocked_data: EnvoyData, json_fixture: dict[str, Any]) -> None:
    """Fill envoy raw data from fixture."""
    if item := json_fixture["data"].get("raw"):
        mocked_data.raw = item
