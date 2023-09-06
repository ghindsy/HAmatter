"""Tests for the withings component."""
from collections.abc import Iterable
import json
from typing import Any, Optional
from urllib.parse import urlparse

import arrow
from withings_api import DateType
from withings_api.common import (
    GetSleepSummaryField,
    MeasureGetMeasGroupCategory,
    MeasureGetMeasResponse,
    MeasureType,
    SleepGetSummaryResponse,
    UserGetDeviceResponse,
)

from homeassistant.components.webhook import async_generate_url
from homeassistant.core import HomeAssistant

from .common import WebhookResponse

from tests.common import load_fixture


async def call_webhook(
    hass: HomeAssistant, webhook_id: str, data: dict[str, Any], client
) -> WebhookResponse:
    """Call the webhook."""
    webhook_url = async_generate_url(hass, webhook_id)

    resp = await client.post(
        urlparse(webhook_url).path,
        data=data,
    )

    # Wait for remaining tasks to complete.
    await hass.async_block_till_done()

    data: dict[str, Any] = await resp.json()
    resp.close()

    return WebhookResponse(message=data["message"], message_code=data["code"])


class MockWithings:
    """Mock object for Withings."""

    def __init__(
        self,
        device_fixture: str = "person0_get_device.json",
        measurement_fixture: str = "person0_get_meas.json",
        sleep_fixture: str = "person0_get_sleep.json",
    ):
        """Initialize mock."""
        self.device_fixture = device_fixture
        self.measurement_fixture = measurement_fixture
        self.sleep_fixture = sleep_fixture

    def user_get_device(self) -> UserGetDeviceResponse:
        """Get devices."""
        fixture = json.loads(load_fixture(f"withings/{self.device_fixture}"))
        return UserGetDeviceResponse(**fixture)

    def measure_get_meas(
        self,
        meastype: MeasureType | None = None,
        category: MeasureGetMeasGroupCategory | None = None,
        startdate: DateType | None = None,
        enddate: DateType | None = None,
        offset: int | None = None,
        lastupdate: DateType | None = None,
    ) -> MeasureGetMeasResponse:
        """Get measurements."""
        fixture = json.loads(load_fixture(f"withings/{self.measurement_fixture}"))
        return MeasureGetMeasResponse(**fixture)

    def sleep_get_summary(
        self,
        data_fields: Iterable[GetSleepSummaryField],
        startdateymd: Optional[DateType] = arrow.utcnow(),
        enddateymd: Optional[DateType] = arrow.utcnow(),
        offset: Optional[int] = None,
        lastupdate: Optional[DateType] = arrow.utcnow(),
    ) -> SleepGetSummaryResponse:
        """Get sleep."""
        fixture = json.loads(load_fixture(f"withings/{self.sleep_fixture}"))
        return SleepGetSummaryResponse(**fixture)
