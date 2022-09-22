"""Typing Helpers for Home Assistant."""
from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional, Protocol, Union

import homeassistant.core

GPSType = tuple[float, float]
ConfigType = dict[str, Any]
ContextType = homeassistant.core.Context
DiscoveryInfoType = dict[str, Any]
EventType = homeassistant.core.Event
ServiceDataType = dict[str, Any]
StateType = Union[None, str, int, float]
TemplateVarsType = Optional[Mapping[str, Any]]

# Custom type for recorder Queries
QueryType = Any


class UndefinedType(Enum):
    """Singleton type for use with not set sentinel values."""

    _singleton = 0


UNDEFINED = UndefinedType._singleton  # pylint: disable=protected-access


class UnitConverter(Protocol):
    """Define the format of a conversion utility."""

    VALID_UNITS: tuple[str, ...]
    NORMALIZED_UNIT: str

    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert one unit of measurement to another."""

    def normalize(self, value: float, from_unit: str) -> float:
        """Convert one unit of measurement to the normalized unit."""


# The following types should not used and
# are not present in the core code base.
# They are kept in order not to break custom integrations
# that may rely on them.
# In due time they will be removed.
HomeAssistantType = homeassistant.core.HomeAssistant
ServiceCallType = homeassistant.core.ServiceCall
