"""Ecovacs constants."""
from deebot_client.events import LifeSpan

from enum import StrEnum

DOMAIN = "ecovacs"

CONF_CONTINENT = "continent"
CONF_OVERRIDE_REST_URL = "override_rest_url"
CONF_OVERRIDE_MQTT_URL = "override_mqtt_url"
CONF_VERIFY_MQTT_CERTIFICATE = "verify_mqtt_certificate"

SUPPORTED_LIFESPANS = (
    LifeSpan.BRUSH,
    LifeSpan.FILTER,
    LifeSpan.SIDE_BRUSH,
)


class InstanceMode(StrEnum):
    """Instance mode."""

    CLOUD = "cloud"
    SELF_HOSTED = "self_hosted"
