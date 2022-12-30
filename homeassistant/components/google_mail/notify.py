"""Notification service for Google Mail integration."""
from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any, cast

from googleapiclient.http import HttpRequest
import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .application_credentials import get_oauth_service
from .const import ATTR_FROM, ATTR_ME, ATTR_SEND


class GMailNotificationService(BaseNotificationService):
    """Define the Google Mail notification logic."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the service."""
        self.data = config

    async def async_send_message(self, message: str, **kwargs: Any) -> None:
        """Send a message."""
        data: dict[str, Any] = kwargs.get(ATTR_DATA) or {}
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        service = await get_oauth_service(self.data)

        email = EmailMessage()
        email.set_content(message)
        if to_addrs := kwargs.get(ATTR_TARGET):
            email["To"] = ", ".join(to_addrs)
        email["From"] = data.get(ATTR_FROM, ATTR_ME)
        email["Subject"] = title

        encoded_message = base64.urlsafe_b64encode(email.as_bytes()).decode()
        users = service.users()  # pylint: disable=no-member
        body = {"raw": encoded_message}
        msg: HttpRequest
        if data.get(ATTR_SEND) is False:
            msg = users.drafts().create(userId=email["From"], body={ATTR_MESSAGE: body})
        else:
            if not to_addrs:
                raise vol.Invalid("recipient address required")
            msg = users.messages().send(userId=email["From"], body=body)
        await self.hass.async_add_executor_job(msg.execute)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> GMailNotificationService:
    """Get the notification service."""
    return GMailNotificationService(cast(DiscoveryInfoType, discovery_info))
