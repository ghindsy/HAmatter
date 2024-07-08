"""Sensoterra models."""

from enum import StrEnum, auto


class ProbeSensorType(StrEnum):
    """Generic sensors within a Sensoterra probe."""

    MOISTURE = auto()
    SI = auto()
    TEMPERATURE = auto()
    BATTERY = auto()
    RSSI = auto()
