"""Test Home Assistant exposed entities helper."""
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.homeassistant.exposed_entities import (
    DATA_EXPOSED_ENTITIES,
    ExposedEntities,
    ExposedEntity,
    async_expose_entity,
    async_get_assistant_settings,
    async_listen_entity_updates,
    async_should_expose,
)
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from tests.common import flush_store
from tests.typing import WebSocketGenerator


async def test_load_preferences(hass: HomeAssistant) -> None:
    """Make sure that we can load/save data correctly."""
    assert await async_setup_component(hass, "homeassistant", {})

    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]
    assert exposed_entities._assistants == {}

    exposed_entities.async_set_expose_new_entities("test1", True)
    exposed_entities.async_set_expose_new_entities("test2", False)

    assert list(exposed_entities._assistants) == ["test1", "test2"]

    await exposed_entities.async_expose_entity("test1", "light.kitchen", True)
    await exposed_entities.async_expose_entity("test1", "light.living_room", True)
    await exposed_entities.async_expose_entity("test2", "light.kitchen", True)
    await exposed_entities.async_expose_entity("test2", "light.kitchen", True)

    await flush_store(exposed_entities.store)

    exposed_entities2 = ExposedEntities(hass)
    await exposed_entities2.async_load()

    assert exposed_entities._assistants == exposed_entities2._assistants
    assert exposed_entities.data == exposed_entities2.data


async def test_expose_entity(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test expose entity."""
    ws_client = await hass_ws_client(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    entry1 = entity_registry.async_get_or_create("test", "test", "unique1")
    entry2 = entity_registry.async_get_or_create("test", "test", "unique2")

    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]
    assert len(exposed_entities.data) == 0

    # Set options
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa"],
            "entity_ids": [entry1.entity_id],
            "should_expose": True,
        }
    )

    response = await ws_client.receive_json()
    assert response["success"]

    entry1 = entity_registry.async_get(entry1.entity_id)
    assert entry1.options == {"cloud.alexa": {"should_expose": True}}
    entry2 = entity_registry.async_get(entry2.entity_id)
    assert entry2.options == {}
    assert len(exposed_entities.data) == 0

    # Update options
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa", "cloud.google_assistant"],
            "entity_ids": [entry1.entity_id, entry2.entity_id],
            "should_expose": False,
        }
    )

    response = await ws_client.receive_json()
    assert response["success"]

    entry1 = entity_registry.async_get(entry1.entity_id)
    assert entry1.options == {
        "cloud.alexa": {"should_expose": False},
        "cloud.google_assistant": {"should_expose": False},
    }
    entry2 = entity_registry.async_get(entry2.entity_id)
    assert entry2.options == {
        "cloud.alexa": {"should_expose": False},
        "cloud.google_assistant": {"should_expose": False},
    }
    assert len(exposed_entities.data) == 0


async def test_expose_entity_unknown(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test behavior when exposing an unknown entity."""
    ws_client = await hass_ws_client(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]
    assert len(exposed_entities.data) == 0

    # Set options
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa"],
            "entity_ids": ["test.test"],
            "should_expose": True,
        }
    )

    response = await ws_client.receive_json()
    assert response["success"]

    assert len(exposed_entities.data) == 1
    assert exposed_entities.data == {
        "test.test": ExposedEntity({"cloud.alexa": {"should_expose": True}})
    }

    # Update options
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa", "cloud.google_assistant"],
            "entity_ids": ["test.test", "test.test2"],
            "should_expose": False,
        }
    )

    response = await ws_client.receive_json()
    assert response["success"]

    assert len(exposed_entities.data) == 2
    assert exposed_entities.data == {
        "test.test": ExposedEntity(
            {
                "cloud.alexa": {"should_expose": False},
                "cloud.google_assistant": {"should_expose": False},
            }
        ),
        "test.test2": ExposedEntity(
            {
                "cloud.alexa": {"should_expose": False},
                "cloud.google_assistant": {"should_expose": False},
            }
        ),
    }


async def test_expose_entity_blocked(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test behavior when exposing a blocked entity."""
    ws_client = await hass_ws_client(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    # Set options
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa"],
            "entity_ids": ["group.all_locks"],
            "should_expose": True,
        }
    )

    response = await ws_client.receive_json()
    assert not response["success"]
    assert response["error"] == {
        "code": "not_allowed",
        "message": "can't expose 'group.all_locks'",
    }


@pytest.mark.parametrize("expose_new", [True, False])
async def test_expose_new_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    expose_new,
) -> None:
    """Test expose entity."""
    ws_client = await hass_ws_client(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    entry1 = entity_registry.async_get_or_create("climate", "test", "unique1")
    entry2 = entity_registry.async_get_or_create("climate", "test", "unique2")

    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_new_entities/get",
            "assistant": "cloud.alexa",
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]
    assert response["result"] == {"expose_new": False}

    # Check if exposed - should be False
    assert await async_should_expose(hass, "cloud.alexa", entry1.entity_id) is False

    # Expose new entities to Alexa
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_new_entities/set",
            "assistant": "cloud.alexa",
            "expose_new": expose_new,
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_new_entities/get",
            "assistant": "cloud.alexa",
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]
    assert response["result"] == {"expose_new": expose_new}

    # Check again if exposed - should still be False
    assert await async_should_expose(hass, "cloud.alexa", entry1.entity_id) is False

    # Check if exposed - should be True
    assert (
        await async_should_expose(hass, "cloud.alexa", entry2.entity_id) == expose_new
    )


async def test_listen_updates(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test listen to updates."""
    calls = []

    def listener():
        calls.append(None)

    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]
    async_listen_entity_updates(hass, "cloud.alexa", listener)

    entry = entity_registry.async_get_or_create("climate", "test", "unique1")

    # Call for another assistant - listener not called
    await exposed_entities.async_expose_entity(
        "cloud.google_assistant", entry.entity_id, True
    )
    assert len(calls) == 0

    # Call for our assistant - listener called
    await exposed_entities.async_expose_entity("cloud.alexa", entry.entity_id, True)
    assert len(calls) == 1

    # Settings not changed - listener not called
    await exposed_entities.async_expose_entity("cloud.alexa", entry.entity_id, True)
    assert len(calls) == 1

    # Settings changed - listener called
    await exposed_entities.async_expose_entity("cloud.alexa", entry.entity_id, False)
    assert len(calls) == 2


async def test_get_assistant_settings(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test get assistant settings."""
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]

    entry = entity_registry.async_get_or_create("climate", "test", "unique1")

    assert async_get_assistant_settings(hass, "cloud.alexa") == {}

    await exposed_entities.async_expose_entity("cloud.alexa", entry.entity_id, True)
    await exposed_entities.async_expose_entity(
        "cloud.alexa", "light.not_in_registry", True
    )
    assert async_get_assistant_settings(hass, "cloud.alexa") == snapshot
    assert async_get_assistant_settings(hass, "cloud.google_assistant") == snapshot

    with pytest.raises(HomeAssistantError):
        exposed_entities.async_get_entity_settings("light.unknown")


@pytest.mark.parametrize("use_registry", [True, False])
async def test_should_expose(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
    use_registry: bool,
) -> None:
    """Test expose entity."""
    ws_client = await hass_ws_client(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    # Expose new entities to Alexa
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_new_entities/set",
            "assistant": "cloud.alexa",
            "expose_new": True,
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]

    # Unknown entity is not exposed
    assert await async_should_expose(hass, "test.test", "test.test") is False

    # Blocked entity is not exposed
    if use_registry:
        entry_blocked = entity_registry.async_get_or_create(
            "group", "test", "unique", suggested_object_id="all_locks"
        )
        assert entry_blocked.entity_id == "group.all_locks"
    assert CLOUD_NEVER_EXPOSED_ENTITIES[0] == "group.all_locks"
    assert await async_should_expose(hass, "cloud.alexa", "group.all_locks") is False

    # Lock is exposed
    if use_registry:
        entity_registry.async_get_or_create("lock", "test", "unique1")
    assert await async_should_expose(hass, "cloud.alexa", "lock.test_unique1") is True

    # Hidden entity is not exposed
    if use_registry:
        entity_registry.async_get_or_create(
            "lock", "test", "unique2", hidden_by=er.RegistryEntryHider.USER
        )
        assert (
            await async_should_expose(hass, "cloud.alexa", "lock.test_unique2") is False
        )

        # Entity with category is not exposed
        entity_registry.async_get_or_create(
            "lock", "test", "unique3", entity_category=EntityCategory.CONFIG
        )
        assert (
            await async_should_expose(hass, "cloud.alexa", "lock.test_unique3") is False
        )

    # Binary sensor without device class is not exposed
    if use_registry:
        entity_registry.async_get_or_create("binary_sensor", "test", "unique1")
    else:
        hass.states.async_set("binary_sensor.test_unique1", "on", {})
    assert (
        await async_should_expose(hass, "cloud.alexa", "binary_sensor.test_unique1")
        is False
    )

    # Binary sensor with certain device class is exposed
    if use_registry:
        entity_registry.async_get_or_create(
            "binary_sensor",
            "test",
            "unique2",
            original_device_class="door",
        )
    else:
        hass.states.async_set(
            "binary_sensor.test_unique2", "on", {"device_class": "door"}
        )
    assert (
        await async_should_expose(hass, "cloud.alexa", "binary_sensor.test_unique2")
        is True
    )

    # Sensor without device class is not exposed
    if use_registry:
        entity_registry.async_get_or_create("sensor", "test", "unique1")
    else:
        hass.states.async_set("sensor.test_unique1", "on", {})
    assert (
        await async_should_expose(hass, "cloud.alexa", "sensor.test_unique1") is False
    )

    # Sensor with certain device class is exposed
    if use_registry:
        entity_registry.async_get_or_create(
            "sensor",
            "test",
            "unique2",
            original_device_class="temperature",
        )
    else:
        hass.states.async_set(
            "sensor.test_unique2", "on", {"device_class": "temperature"}
        )
    assert await async_should_expose(hass, "cloud.alexa", "sensor.test_unique2") is True
    # The second time we check, it should load it from storage
    assert await async_should_expose(hass, "cloud.alexa", "sensor.test_unique2") is True
    # Check with a different assistant
    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]
    exposed_entities.async_set_expose_new_entities("cloud.no_default_expose", False)
    assert (
        await async_should_expose(
            hass, "cloud.no_default_expose", "sensor.test_unique2"
        )
        is False
    )


async def test_list_exposed_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test list exposed entities."""
    ws_client = await hass_ws_client(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    entry1 = entity_registry.async_get_or_create("test", "test", "unique1")
    entry2 = entity_registry.async_get_or_create("test", "test", "unique2")

    # Set options for registered entities
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa", "cloud.google_assistant"],
            "entity_ids": [entry1.entity_id, entry2.entity_id],
            "should_expose": True,
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]

    # Set options for entities not in the entity registry
    await ws_client.send_json_auto_id(
        {
            "type": "homeassistant/expose_entity",
            "assistants": ["cloud.alexa", "cloud.google_assistant"],
            "entity_ids": [
                "test.test",
                "test.test2",
            ],
            "should_expose": False,
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]

    # List exposed entities
    await ws_client.send_json_auto_id({"type": "homeassistant/expose_entity/list"})
    response = await ws_client.receive_json()
    assert response["success"]
    assert response["result"] == {
        "exposed_entities": {
            "test.test": {"cloud.alexa": False, "cloud.google_assistant": False},
            "test.test2": {"cloud.alexa": False, "cloud.google_assistant": False},
            "test.test_unique1": {"cloud.alexa": True, "cloud.google_assistant": True},
            "test.test_unique2": {"cloud.alexa": True, "cloud.google_assistant": True},
        },
    }


async def test_listeners(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Make sure we call entity listeners."""
    assert await async_setup_component(hass, "homeassistant", {})

    exposed_entities: ExposedEntities = hass.data[DATA_EXPOSED_ENTITIES]

    callbacks = []
    exposed_entities.async_listen_entity_updates("test1", lambda: callbacks.append(1))

    await async_expose_entity(hass, "test1", "light.kitchen", True)
    assert len(callbacks) == 1

    entry1 = entity_registry.async_get_or_create("switch", "test", "unique1")
    await async_expose_entity(hass, "test1", entry1.entity_id, True)
