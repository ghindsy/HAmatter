"""Types for the ViCare integration."""
from collections.abc import Callable
from dataclasses import dataclass

from PyViCare.PyViCareDevice import Device as PyViCareDevice


@dataclass()
class ViCareRequiredKeysMixin:
    """Mixin for required keys."""

    value_getter: Callable[[PyViCareDevice], bool]


@dataclass()
class ViCareRequiredKeysMixinWithSet(ViCareRequiredKeysMixin):
    """Mixin for required keys with setter."""

    value_setter: Callable[[PyViCareDevice], bool]
