"""Common tradfri test fixtures."""
from unittest import mock

import pytest

from . import GATEWAY_ID, TRADFRI_DIR

from tests.components.light.conftest import mock_light_profiles  # noqa: F401

# pylint: disable=protected-access


@pytest.fixture
def mock_gateway_info():
    """Mock get_gateway_info."""
    with mock.patch(TRADFRI_DIR + ".config_flow.get_gateway_info") as gateway_info:
        yield gateway_info


@pytest.fixture
def mock_entry_setup():
    """Mock entry setup."""
    with mock.patch(TRADFRI_DIR + ".async_setup_entry") as mock_setup:
        mock_setup.return_value = True
        yield mock_setup


@pytest.fixture
def mock_gateway():
    """Mock a Tradfri gateway."""

    def get_devices():
        """Return mock devices."""
        return gateway.mock_devices

    def get_groups():
        """Return mock groups."""
        return gateway.mock_groups

    gateway_info = mock.Mock(id=GATEWAY_ID, firmware_version="1.2.1234")

    def get_gateway_info():
        """Return mock gateway info."""
        return gateway_info

    gateway = mock.Mock(
        get_devices=get_devices,
        get_groups=get_groups,
        get_gateway_info=get_gateway_info,
        mock_devices=[],
        mock_groups=[],
        mock_responses=[],
    )
    with mock.patch(TRADFRI_DIR + ".Gateway", return_value=gateway), mock.patch(
        TRADFRI_DIR + ".config_flow.Gateway", return_value=gateway
    ):
        yield gateway


@pytest.fixture
def mock_api(mock_gateway):
    """Mock api."""

    async def api(command):
        """Mock api function."""
        # Store the data for "real" command objects.
        if hasattr(command, "_data") and not isinstance(command, mock.Mock):
            mock_gateway.mock_responses.append(command._data)
        return command

    return api


@pytest.fixture
def mock_api_factory(mock_api):
    """Mock pytradfri api factory."""
    with mock.patch(TRADFRI_DIR + ".APIFactory", autospec=True) as factory:
        factory.init.return_value = factory.return_value
        factory.return_value.request = mock_api
        yield factory.return_value
