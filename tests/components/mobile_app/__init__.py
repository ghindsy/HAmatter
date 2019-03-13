"""Tests for mobile_app component."""
# pylint: disable=redefined-outer-name,unused-import
import pytest

from homeassistant.setup import async_setup_component

from homeassistant.components.mobile_app.const import (ATTR_DEVICE_NAME,
                                                       ATTR_MANUFACTURER,
                                                       ATTR_MODEL,
                                                       ATTR_OS_VERSION,
                                                       CONF_SECRET,
                                                       CONF_USER_ID,
                                                       DATA_DELETED_IDS,
                                                       DATA_REGISTRATIONS,
                                                       DOMAIN,
                                                       STORAGE_KEY,
                                                       STORAGE_VERSION)
from homeassistant.const import CONF_WEBHOOK_ID


@pytest.fixture
def webhook_client(hass, aiohttp_client, hass_storage, hass_admin_user):
    """mobile_app mock client."""
    hass_storage[STORAGE_KEY] = {
        'version': STORAGE_VERSION,
        'data': {
            DATA_REGISTRATIONS: {
                'mobile_app_test': {
                    CONF_SECRET: '58eb127991594dad934d1584bdee5f27',
                    'supports_encryption': True,
                    CONF_WEBHOOK_ID: 'mobile_app_test',
                    ATTR_DEVICE_NAME: 'Test Device',
                    CONF_USER_ID: hass_admin_user.id,
                    ATTR_MANUFACTURER: 'Home Assistant',
                    ATTR_MODEL: 'Tests',
                    ATTR_OS_VERSION: '1.0.0'
                },
                'mobile_app_test_cleartext': {
                    'supports_encryption': False,
                    CONF_WEBHOOK_ID: 'mobile_app_test_cleartext',
                    'device_name': 'Test Device (Cleartext)',
                    CONF_USER_ID: hass_admin_user.id,
                    ATTR_MANUFACTURER: 'Home Assistant',
                    ATTR_MODEL: 'Cleartext Tests',
                    ATTR_OS_VERSION: '1.0.1'
                }
            },
            DATA_DELETED_IDS: [],
        }
    }

    assert hass.loop.run_until_complete(async_setup_component(
        hass, DOMAIN, {
            DOMAIN: {}
        }))

    return hass.loop.run_until_complete(aiohttp_client(hass.http.app))


@pytest.fixture
async def authed_api_client(hass, hass_client):
    """Provide an authenticated client for mobile_app to use."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    return await hass_client()


@pytest.fixture(autouse=True)
async def setup_ws(hass):
    """Configure the websocket_api component."""
    assert await async_setup_component(hass, 'websocket_api', {})
