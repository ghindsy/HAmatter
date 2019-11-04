"""Support for azure service bus notification."""
import json

from azure.servicebus.aio import Message, ServiceBusClient
import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.const import CONTENT_TYPE_JSON
import homeassistant.helpers.config_validation as cv

CONF_CONNECTION_STRING = "connection_string"
CONF_QUEUE_NAME = "queue"
CONF_TOPIC_NAME = "topic"

ATTR_ASB_MESSAGE = "message"
ATTR_ASB_TITLE = "title"
ATTR_ASB_TARGET = "target"

PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_QUEUE_NAME, CONF_TOPIC_NAME),
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_CONNECTION_STRING): cv.string,
            vol.Exclusive(
                CONF_QUEUE_NAME, "output", "Can only send to a queue or a topic."
            ): cv.string,
            vol.Exclusive(
                CONF_TOPIC_NAME, "output", "Can only send to a queue or a topic."
            ): cv.string,
        }
    ),
)


async def async_get_service(hass, config, discovery_info=None):
    """Get the notification service."""
    connection_string = config[CONF_CONNECTION_STRING]
    queue_name = config.get(CONF_QUEUE_NAME)
    topic_name = config.get(CONF_TOPIC_NAME)

    servicebus = ServiceBusClient.from_connection_string(
        connection_string, loop=hass.loop
    )

    if queue_name:
        client = servicebus.get_queue(queue_name)
    elif topic_name:
        client = servicebus.get_topic(topic_name)
    else:
        return None

    return ServiceBusNotificationService(client)


class ServiceBusNotificationService(BaseNotificationService):
    """Implement the notification service for the service bus service."""

    def __init__(self, client):
        """Initialize the service."""
        self._client = client

    async def async_send_message(self, message, **kwargs):
        """Send a message."""
        dto = {ATTR_ASB_MESSAGE: message}

        if ATTR_TITLE in kwargs:
            dto[ATTR_ASB_TITLE] = kwargs[ATTR_TITLE]
        if ATTR_TARGET in kwargs:
            dto[ATTR_ASB_TARGET] = kwargs[ATTR_TARGET]

        data = kwargs.get(ATTR_DATA)
        if data:
            dto.update(data)

        queue_message = Message(json.dumps(dto))
        queue_message.properties.content_type = CONTENT_TYPE_JSON
        await self._client.send(queue_message)
