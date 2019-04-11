"""Support for RainMachine devices."""
import logging
from datetime import timedelta
from functools import wraps

import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    ATTR_ATTRIBUTION, CONF_BINARY_SENSORS, CONF_IP_ADDRESS, CONF_PASSWORD,
    CONF_PORT, CONF_SCAN_INTERVAL, CONF_SENSORS, CONF_SSL,
    CONF_MONITORED_CONDITIONS, CONF_SWITCHES)
from homeassistant.exceptions import (
    ConfigEntryNotReady, Unauthorized, UnknownUser)
from homeassistant.helpers import aiohttp_client, config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

from .config_flow import configured_instances
from .const import (
    DATA_CLIENT, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_SSL, DOMAIN)



_LOGGER = logging.getLogger(__name__)

DATA_LISTENER = 'listener'

PROGRAM_UPDATE_TOPIC = '{0}_program_update'.format(DOMAIN)
SENSOR_UPDATE_TOPIC = '{0}_data_update'.format(DOMAIN)
ZONE_UPDATE_TOPIC = '{0}_zone_update'.format(DOMAIN)

CONF_CONTROLLERS = 'controllers'
CONF_PROGRAM_ID = 'program_id'
CONF_SECONDS = 'seconds'
CONF_ZONE_ID = 'zone_id'
CONF_ZONE_RUN_TIME = 'zone_run_time'

DEFAULT_ATTRIBUTION = 'Data provided by Green Electronics LLC'
DEFAULT_ICON = 'mdi:water'
DEFAULT_ZONE_RUN = 60 * 10

TYPE_FREEZE = 'freeze'
TYPE_FREEZE_PROTECTION = 'freeze_protection'
TYPE_FREEZE_TEMP = 'freeze_protect_temp'
TYPE_HOT_DAYS = 'extra_water_on_hot_days'
TYPE_HOURLY = 'hourly'
TYPE_MONTH = 'month'
TYPE_RAINDELAY = 'raindelay'
TYPE_RAINSENSOR = 'rainsensor'
TYPE_WEEKDAY = 'weekday'

BINARY_SENSORS = {
    TYPE_FREEZE: ('Freeze Restrictions', 'mdi:cancel'),
    TYPE_FREEZE_PROTECTION: ('Freeze Protection', 'mdi:weather-snowy'),
    TYPE_HOT_DAYS: ('Extra Water on Hot Days', 'mdi:thermometer-lines'),
    TYPE_HOURLY: ('Hourly Restrictions', 'mdi:cancel'),
    TYPE_MONTH: ('Month Restrictions', 'mdi:cancel'),
    TYPE_RAINDELAY: ('Rain Delay Restrictions', 'mdi:cancel'),
    TYPE_RAINSENSOR: ('Rain Sensor Restrictions', 'mdi:cancel'),
    TYPE_WEEKDAY: ('Weekday Restrictions', 'mdi:cancel'),
}

SENSORS = {
    TYPE_FREEZE_TEMP: ('Freeze Protect Temperature', 'mdi:thermometer', '°C'),
}

BINARY_SENSOR_SCHEMA = vol.Schema({
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(BINARY_SENSORS)):
        vol.All(cv.ensure_list, [vol.In(BINARY_SENSORS)])
})

SENSOR_SCHEMA = vol.Schema({
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSORS)):
        vol.All(cv.ensure_list, [vol.In(SENSORS)])
})

SERVICE_ALTER_PROGRAM = vol.Schema({
    vol.Required(CONF_PROGRAM_ID): cv.positive_int,
})

SERVICE_ALTER_ZONE = vol.Schema({
    vol.Required(CONF_ZONE_ID): cv.positive_int,
})

SERVICE_PAUSE_WATERING = vol.Schema({
    vol.Required(CONF_SECONDS): cv.positive_int,
})

SERVICE_START_PROGRAM_SCHEMA = vol.Schema({
    vol.Required(CONF_PROGRAM_ID): cv.positive_int,
})

SERVICE_START_ZONE_SCHEMA = vol.Schema({
    vol.Required(CONF_ZONE_ID): cv.positive_int,
    vol.Optional(CONF_ZONE_RUN_TIME, default=DEFAULT_ZONE_RUN):
        cv.positive_int,
})

SERVICE_STOP_PROGRAM_SCHEMA = vol.Schema({
    vol.Required(CONF_PROGRAM_ID): cv.positive_int,
})

SERVICE_STOP_ZONE_SCHEMA = vol.Schema({
    vol.Required(CONF_ZONE_ID): cv.positive_int,
})

SWITCH_SCHEMA = vol.Schema({vol.Optional(CONF_ZONE_RUN_TIME): cv.positive_int})


CONTROLLER_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
        cv.time_period,
    vol.Optional(CONF_BINARY_SENSORS, default={}): BINARY_SENSOR_SCHEMA,
    vol.Optional(CONF_SENSORS, default={}): SENSOR_SCHEMA,
    vol.Optional(CONF_SWITCHES, default={}): SWITCH_SCHEMA,
})


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_CONTROLLERS):
            vol.All(cv.ensure_list, [CONTROLLER_SCHEMA]),
    }),
}, extra=vol.ALLOW_EXTRA)


def _check_valid_user(hass):
    """Ensure the user of a service call has proper permissions."""
    def decorator(service):
        """Decorate."""
        @wraps(service)
        async def check_permissions(call):
            """Check user permission and raise before call if unauthorized."""
            if not call.context.user_id:
                return

            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None:
                raise UnknownUser(
                    context=call.context,
                    permission=POLICY_CONTROL
                )

            # RainMachine services don't interact with specific entities.
            # Therefore, we examine _all_ RainMachine entities and if the user
            # has permission to control _any_ of them, the user has permission
            # to call the service:
            en_reg = await hass.helpers.entity_registry.async_get_registry()
            rainmachine_entities = [
                entity.entity_id for entity in en_reg.entities.values()
                if entity.platform == DOMAIN
            ]
            for entity_id in rainmachine_entities:
                if user.permissions.check_entity(entity_id, POLICY_CONTROL):
                    return await service(call)

            raise Unauthorized(
                context=call.context,
                permission=POLICY_CONTROL,
            )
        return check_permissions
    return decorator


async def async_setup(hass, config):
    """Set up the RainMachine component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CLIENT] = {}
    hass.data[DOMAIN][DATA_LISTENER] = {}

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    for controller in conf[CONF_CONTROLLERS]:
        if controller[CONF_IP_ADDRESS] in configured_instances(hass):
            continue

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={'source': SOURCE_IMPORT},
                data=controller))

    return True


async def async_setup_entry(hass, config_entry):
    """Set up RainMachine as config entry."""
    from regenmaschine import login
    from regenmaschine.errors import RainMachineError

    websession = aiohttp_client.async_get_clientsession(hass)

    try:
        client = await login(
            config_entry.data[CONF_IP_ADDRESS],
            config_entry.data[CONF_PASSWORD],
            websession,
            port=config_entry.data[CONF_PORT],
            ssl=config_entry.data[CONF_SSL])
        rainmachine = RainMachine(
            client,
            config_entry.data.get(CONF_BINARY_SENSORS, {}).get(
                CONF_MONITORED_CONDITIONS, list(BINARY_SENSORS)),
            config_entry.data.get(CONF_SENSORS, {}).get(
                CONF_MONITORED_CONDITIONS, list(SENSORS)),
            config_entry.data.get(CONF_ZONE_RUN_TIME, DEFAULT_ZONE_RUN))
        await rainmachine.async_update()
    except RainMachineError as err:
        _LOGGER.error('An error occurred: %s', err)
        raise ConfigEntryNotReady

    hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id] = rainmachine

    for component in ('binary_sensor', 'sensor', 'switch'):
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                config_entry, component))

    async def refresh(event_time):
        """Refresh RainMachine sensor data."""
        _LOGGER.debug('Updating RainMachine sensor data')
        await rainmachine.async_update()
        async_dispatcher_send(hass, SENSOR_UPDATE_TOPIC)

    hass.data[DOMAIN][DATA_LISTENER][
        config_entry.entry_id] = async_track_time_interval(
            hass,
            refresh,
            timedelta(seconds=config_entry.data[CONF_SCAN_INTERVAL]))

    @_check_valid_user(hass)
    async def disable_program(call):
        """Disable a program."""
        await rainmachine.client.programs.disable(
            call.data[CONF_PROGRAM_ID])
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def disable_zone(call):
        """Disable a zone."""
        await rainmachine.client.zones.disable(call.data[CONF_ZONE_ID])
        async_dispatcher_send(hass, ZONE_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def enable_program(call):
        """Enable a program."""
        await rainmachine.client.programs.enable(call.data[CONF_PROGRAM_ID])
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def enable_zone(call):
        """Enable a zone."""
        await rainmachine.client.zones.enable(call.data[CONF_ZONE_ID])
        async_dispatcher_send(hass, ZONE_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def pause_watering(call):
        """Pause watering for a set number of seconds."""
        await rainmachine.client.watering.pause_all(call.data[CONF_SECONDS])
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def start_program(call):
        """Start a particular program."""
        await rainmachine.client.programs.start(call.data[CONF_PROGRAM_ID])
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def start_zone(call):
        """Start a particular zone for a certain amount of time."""
        await rainmachine.client.zones.start(
            call.data[CONF_ZONE_ID], call.data[CONF_ZONE_RUN_TIME])
        async_dispatcher_send(hass, ZONE_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def stop_all(call):
        """Stop all watering."""
        await rainmachine.client.watering.stop_all()
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def stop_program(call):
        """Stop a program."""
        await rainmachine.client.programs.stop(call.data[CONF_PROGRAM_ID])
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def stop_zone(call):
        """Stop a zone."""
        await rainmachine.client.zones.stop(call.data[CONF_ZONE_ID])
        async_dispatcher_send(hass, ZONE_UPDATE_TOPIC)

    @_check_valid_user(hass)
    async def unpause_watering(call):
        """Unpause watering."""
        await rainmachine.client.watering.unpause_all()
        async_dispatcher_send(hass, PROGRAM_UPDATE_TOPIC)

    for service, method, schema in [
            ('disable_program', disable_program, SERVICE_ALTER_PROGRAM),
            ('disable_zone', disable_zone, SERVICE_ALTER_ZONE),
            ('enable_program', enable_program, SERVICE_ALTER_PROGRAM),
            ('enable_zone', enable_zone, SERVICE_ALTER_ZONE),
            ('pause_watering', pause_watering, SERVICE_PAUSE_WATERING),
            ('start_program', start_program, SERVICE_START_PROGRAM_SCHEMA),
            ('start_zone', start_zone, SERVICE_START_ZONE_SCHEMA),
            ('stop_all', stop_all, {}),
            ('stop_program', stop_program, SERVICE_STOP_PROGRAM_SCHEMA),
            ('stop_zone', stop_zone, SERVICE_STOP_ZONE_SCHEMA),
            ('unpause_watering', unpause_watering, {}),
    ]:
        hass.services.async_register(DOMAIN, service, method, schema=schema)

    return True


async def async_unload_entry(hass, config_entry):
    """Unload an OpenUV config entry."""
    hass.data[DOMAIN][DATA_CLIENT].pop(config_entry.entry_id)

    remove_listener = hass.data[DOMAIN][DATA_LISTENER].pop(
        config_entry.entry_id)
    remove_listener()

    for component in ('binary_sensor', 'sensor', 'switch'):
        await hass.config_entries.async_forward_entry_unload(
            config_entry, component)

    return True


class RainMachine:
    """Define a generic RainMachine object."""

    def __init__(
            self, client, binary_sensor_conditions, sensor_conditions,
            default_zone_runtime):
        """Initialize."""
        self.binary_sensor_conditions = binary_sensor_conditions
        self.client = client
        self.default_zone_runtime = default_zone_runtime
        self.device_mac = self.client.mac
        self.restrictions = {}
        self.sensor_conditions = sensor_conditions

    async def async_update(self):
        """Update sensor/binary sensor data."""
        self.restrictions.update({
            'current': await self.client.restrictions.current(),
            'global': await self.client.restrictions.universal()
        })


class RainMachineEntity(Entity):
    """Define a generic RainMachine entity."""

    def __init__(self, rainmachine):
        """Initialize."""
        self._attrs = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        self._dispatcher_handlers = []
        self._name = None
        self.rainmachine = rainmachine

    @property
    def device_info(self):
        """Return device registry information for this entity."""
        return {
            'identifiers': {
                (DOMAIN, self.rainmachine.client.mac)
            },
            'name': self.rainmachine.client.name,
            'manufacturer': 'RainMachine',
            'model': 'Version {0} (API: {1})'.format(
                self.rainmachine.client.hardware_version,
                self.rainmachine.client.api_version),
            'sw_version': self.rainmachine.client.software_version,
        }

    @property
    def device_state_attributes(self) -> dict:
        """Return the state attributes."""
        return self._attrs

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        for handler in self._dispatcher_handlers:
            handler()
