"""Common libraries for test setup."""

import time

from google_nest_sdm.device_manager import DeviceManager
from google_nest_sdm.event import EventCallback, EventMessage
from google_nest_sdm.google_nest_subscriber import GoogleNestSubscriber

from homeassistant.components.nest import DOMAIN
from homeassistant.setup import async_setup_component

from tests.async_mock import patch
from tests.common import MockConfigEntry

SERVICE_ACCOUNT_INFO = """
{
  "type": "service_account_info",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_email": "example@service.iam.gserviceaccount.com",
  "client_id": "some-client-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAKYscIlwm7soDsHAz6L6YvUkCvkrX19rS6yeYOmovvhoK5WeYGWUsd8V72zmsyHB7XO94YgJVjvxfzn5K8bLePjFzwoSJjZvhBJ/ZQ05d8VmbvgyWUoPdG9oEa4fZ/lCYrXoaFdTot2xcJvrb/ZuiRl4s4eZpNeFYvVK/Am7UeFPAgMBAAECgYAUetOfzLYUudofvPCaKHu7tKZ5kQPfEa0w6BAPnBF1Mfl1JiDBRDMryFtKs6AOIAVwx00dY/Ex0BCbB3+Cr58H7t4NaPTJxCpmR09pK7o17B7xAdQv8+SynFNud9/5vQ5AEXMOLNwKiU7wpXT6Z7ZIibUBOR7ewsWgsHCDpN1iqQJBAOMODPTPSiQMwRAUHIc6GPleFSJnIz2PAoG3JOG9KFAL6RtIc19lob2ZXdbQdzKtjSkWo+O5W20WDNAl1k32h6MCQQC7W4ZCIY67mPbL6CxXfHjpSGF4Dr9VWJ7ZrKHr6XUoOIcEvsn/pHvWonjMdy93rQMSfOE8BKd/I1+GHRmNVgplAkAnSo4paxmsZVyfeKt7Jy2dMY+8tVZe17maUuQaAE7Sk00SgJYegwrbMYgQnWCTL39HBfj0dmYA2Zj8CCAuu6O7AkEAryFiYjaUAO9+4iNoL27+ZrFtypeeadyov7gKs0ZKaQpNyzW8A+Zwi7TbTeSqzic/E+z/bOa82q7p/6b7141xsQJBANCAcIwMcVb6KVCHlQbOtKspo5Eh4ZQi8bGl+IcwbQ6JSxeTx915IfAldgbuU047wOB04dYCFB2yLDiUGVXTifU=\\n-----END PRIVATE KEY-----\\n"
}
"""

CONFIG = {
    "nest": {
        "client_id": "some-client-id",
        "client_secret": "some-client-secret",
        # Required fields for using SDM API
        "project_id": "some-project-id",
        "subscriber_id": "some-subscriber-id",
        "subscriber_service_account": SERVICE_ACCOUNT_INFO,
    },
}

CONFIG_ENTRY_ID = "config-entry-id"
CONFIG_ENTRY_DATA = {
    "sdm": {},  # Indicates new SDM API, not legacy API
    "auth_implementation": DOMAIN,
    "token": {
        "expires_at": time.time() + 86400,
        "access_token": "some-token",
        "refresh_token": "some-refresh-token",
    },
}


class FakeDeviceManager(DeviceManager):
    """Fake DeviceManager that can supply a list of devices and structures."""

    def __init__(self, devices: dict, structures: dict):
        """Initialize FakeDeviceManager."""
        super().__init__()
        self._devices = devices

    @property
    def structures(self) -> dict:
        """Override structures with fake result."""
        return self._structures

    @property
    def devices(self) -> dict:
        """Override devices with fake result."""
        return self._devices


class FakeSubscriber(GoogleNestSubscriber):
    """Fake subscriber that supplies a FakeDeviceManager."""

    def __init__(self, device_manager: FakeDeviceManager):
        """Initialize Fake Subscriber."""
        self._device_manager = device_manager
        self._callback = None

    def set_update_callback(self, callback: EventCallback):
        """Capture the callback set by Home Assistant."""
        self._callback = callback

    async def start_async(self) -> DeviceManager:
        """Return the fake device manager."""
        return self._device_manager

    async def async_get_device_manager(self) -> DeviceManager:
        """Return the fake device manager."""
        return self._device_manager

    def stop_async(self):
        """No-op to stop the subscriber."""
        return None

    def receive_event(self, event_message: EventMessage):
        """Simulate a received pubsub message, invoked by tests."""
        # Update device state, then invoke HomeAssistant to refresh
        self._device_manager.handle_event(event_message)
        self._callback.handle_event(event_message)


async def async_setup_sdm_platform(hass, platform=None, devices={}, structures={}):
    """Set up the platform and prerequisites."""
    MockConfigEntry(
        entry_id=CONFIG_ENTRY_ID, domain=DOMAIN, data=CONFIG_ENTRY_DATA
    ).add_to_hass(hass)
    device_manager = FakeDeviceManager(devices=devices, structures=structures)
    subscriber = FakeSubscriber(device_manager)
    platforms = []
    if platform:
        platforms.append(platform)
    with patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation"
    ), patch("homeassistant.components.nest.PLATFORMS", platforms), patch(
        "homeassistant.components.nest.GoogleNestSubscriber", return_value=subscriber
    ):
        assert await async_setup_component(hass, DOMAIN, CONFIG)
        await hass.async_block_till_done()
    return subscriber
