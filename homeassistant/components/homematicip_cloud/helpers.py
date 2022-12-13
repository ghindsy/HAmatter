"""Helper functions for Homematicip Cloud Integration."""

from functools import wraps
import logging

from homeassistant.exceptions import HomeAssistantError

from . import HomematicipGenericEntity

_LOGGER = logging.getLogger(__name__)


def is_error_response(response) -> bool:
    """Response from async call contains errors or not."""
    if isinstance(response, dict):
        return "errorCode" in response and response["errorCode"] != ""

    return False


def handle_errors(func):
    """Handle async errors."""

    @wraps(func)
    async def inner(self: HomematicipGenericEntity) -> None:
        """Handle errors from async call."""
        result = await func(self)
        if is_error_response(result):
            raise HomeAssistantError(
                f"Error while execute function {func.__name__}: {result.get('errorCode')}"
            )

    return inner
