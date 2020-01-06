"""Support to keep track of user controlled booleans for within automation."""
import logging
import typing

import voluptuous as vol

from homeassistant.const import (
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    SERVICE_RELOAD,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.helpers import collection, entity_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.helpers.service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceCallType
from homeassistant.loader import bind_hass

DOMAIN = "input_boolean"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

_LOGGER = logging.getLogger(__name__)

CONF_INITIAL = "initial"

CREATE_FIELDS = {
    vol.Required(CONF_NAME): vol.All(str, vol.Length(min=1)),
    vol.Optional(CONF_INITIAL): cv.boolean,
    vol.Optional(CONF_ICON): cv.icon,
}

UPDATE_FIELDS = {
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_INITIAL): cv.boolean,
    vol.Optional(CONF_ICON): cv.icon,
}

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: cv.schema_with_slug_keys(vol.Any(UPDATE_FIELDS, None))},
    extra=vol.ALLOW_EXTRA,
)

RELOAD_SERVICE_SCHEMA = vol.Schema({})
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


class InputBooleanStorageCollection(collection.StorageCollection):
    """Input boolean collection stored in storage."""

    CREATE_SCHEMA = vol.Schema(CREATE_FIELDS)
    UPDATE_SCHEMA = vol.Schema(UPDATE_FIELDS)

    async def _process_create_data(self, data: typing.Dict) -> typing.Dict:
        """Validate the config is valid."""
        return self.CREATE_SCHEMA(data)

    @callback
    def _get_suggested_id(self, info: typing.Dict) -> str:
        """Suggest an ID based on the config."""
        return info[CONF_NAME]

    async def _update_data(self, data: dict, update_data: typing.Dict) -> typing.Dict:
        """Return a new updated data object."""
        return self.UPDATE_SCHEMA(update_data)

    async def _collection_changed(
        self, change_type: str, item_id: str, config: typing.Optional[typing.Dict]
    ) -> None:
        """Handle a collection change."""
        if change_type != collection.CHANGE_REMOVED:
            return

        ent_reg = await entity_registry.async_get_registry(self.hass)
        ent_reg.async_remove(ent_reg.async_get_entity_id(DOMAIN, DOMAIN, item_id))


@bind_hass
def is_on(hass, entity_id):
    """Test if input_boolean is True."""
    return hass.states.is_state(entity_id, STATE_ON)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up an input boolean."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    id_manager = collection.IDManager()

    yaml_collection = collection.YamlCollection(
        logging.getLogger(f"{__name__}.yaml_collection"), id_manager
    )
    collection.attach_entity_component_collection(
        component, yaml_collection, lambda conf: InputBoolean(conf, from_yaml=True)
    )

    storage_collection = InputBooleanStorageCollection(
        Store(hass, STORAGE_VERSION, STORAGE_KEY),
        logging.getLogger(f"{__name__}_storage_collection"),
        id_manager,
    )
    collection.attach_entity_component_collection(
        component, storage_collection, InputBoolean
    )

    await yaml_collection.async_load(_filter_yaml(config))
    await storage_collection.async_load()

    collection.StorageCollectionWebsocket(
        storage_collection, DOMAIN, DOMAIN, CREATE_FIELDS, UPDATE_FIELDS
    ).async_setup(hass)

    async def reload_service_handler(service_call: ServiceCallType) -> None:
        """Remove all input booleans and load new ones from config."""
        conf = await component.async_prepare_reload(skip_reset=True)
        if conf is None:
            return
        await yaml_collection.async_load(_filter_yaml(conf))

    homeassistant.helpers.service.async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")

    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")

    component.async_register_entity_service(SERVICE_TOGGLE, {}, "async_toggle")

    return True


def _filter_yaml(config):
    """Process config and create list suitable for collection consumption."""
    return [{CONF_ID: id_, **(conf or {})} for id_, conf in config[DOMAIN].items()]


class InputBoolean(ToggleEntity, RestoreEntity):
    """Representation of a boolean input."""

    def __init__(self, config: typing.Optional[dict], from_yaml: bool = False):
        """Initialize a boolean input."""
        self._unique_id = config[CONF_ID]
        self._name = config.get(CONF_NAME)
        self._state = config.get(CONF_INITIAL)
        self._icon = config.get(CONF_ICON)
        if from_yaml:
            # unless we want to make a breaking change
            self.entity_id = ENTITY_ID_FORMAT.format(self._unique_id)

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return name of the boolean input."""
        return self._name

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def is_on(self):
        """Return true if entity is on."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID for the person."""
        return self._unique_id

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        # If not None, we got an initial value.
        await super().async_added_to_hass()
        if self._state is not None:
            return

        state = await self.async_get_last_state()
        self._state = state and state.state == STATE_ON

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        self._state = True
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        self._state = False
        await self.async_update_ha_state()

    async def async_update_config(self, config: typing.Dict) -> None:
        """Handle when the config is updated."""
        self._unique_id = config[CONF_ID]
        self._name = config.get(CONF_NAME)
        self._state = config.get(CONF_INITIAL)
        self._icon = config.get(CONF_ICON)
        self.async_schedule_update_ha_state()
