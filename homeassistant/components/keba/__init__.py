"""Support for KEBA charging stations."""
import asyncio
import logging

from keba_kecontact.connection import KebaKeContact
import voluptuous as vol

from homeassistant.const import CONF_HOST
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'keba'
SUPPORTED_COMPONENTS = ['binary_sensor', 'sensor', "lock"]

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional('rfid', default='00845500'): cv.string,
        vol.Optional('failsafe', default=False): cv.boolean,
        vol.Optional('failsafe_timeout', default=30): cv.positive_int,
        vol.Optional('failsafe_fallback', default=6): cv.positive_int,
        vol.Optional('failsafe_persist', default=0): cv.positive_int,
        vol.Optional('refresh_interval', default=5): cv.positive_int,
    }),
}, extra=vol.ALLOW_EXTRA)

_SERVICE_MAP = {
    'request_data': 'request_data',
    'set_energy': 'async_set_energy',
    'set_current': 'async_set_current',
    'authorize': 'async_start',
    'deauthorize': 'async_stop',
    'enable': 'async_enable_ev',
    'disable': 'async_disable_ev',
    'set_failsafe': 'async_set_failsafe'
}


async def async_setup(hass, config):
    """Check connectivity and version of KEBA charging station."""
    host = config[DOMAIN][CONF_HOST]
    rfid = config[DOMAIN]['rfid']
    refresh_interval = config[DOMAIN]['refresh_interval']
    keba = KebaHandler(hass, host, rfid, refresh_interval)
    hass.data[DOMAIN] = keba

    # Wait for KebaHandler setup complete (initial values loaded)
    await keba.setup()

    # Set failsafe mode at start up of home assistant
    failsafe = config[DOMAIN]['failsafe']
    timeout = config[DOMAIN]['failsafe_timeout'] if failsafe else 0
    fallback = config[DOMAIN]['failsafe_fallback'] if failsafe else 0
    persist = config[DOMAIN]['failsafe_persist'] if failsafe else 0
    try:
        hass.loop.create_task(keba.set_failsafe(timeout, fallback, persist))
    except ValueError as ex:
        _LOGGER.warning("Could not set failsafe mode %s", ex)

    # Register services to hass
    async def async_execute_service(call):
        """Execute a service to KEBA charging station.

        This must be a member function as we need access to the hass
        object here.
        """
        function_name = _SERVICE_MAP[call.service]
        function_call = getattr(keba, function_name)
        hass.async_create_task(function_call(call.data))

    for service in _SERVICE_MAP:
        hass.services.async_register(DOMAIN, service, async_execute_service)

    # Load components
    for domain in SUPPORTED_COMPONENTS:
        hass.async_create_task(
            discovery.async_load_platform(hass, domain, DOMAIN, {}, config))

    # Start periodic polling of charging station data
    keba.start_periodic_request()

    return True


class KebaHandler(KebaKeContact):
    """Representation of a KEBA charging station connection."""

    def __init__(self, hass, host, rfid, refresh_interval):
        """Constructor."""
        super().__init__(host, self.hass_callback)

        self._update_listeners = []
        self._hass = hass
        self.rfid = rfid
        self.device_name = "keba_wallbox_"

        # Ensure at least 5 seconds delay
        self._refresh_interval = max(5, refresh_interval)
        self._fast_polling_count = 9
        self._polling_task = None

    def start_periodic_request(self):
        """Start periodic data polling."""
        self._polling_task = self._hass.loop.create_task(
            self._periodic_request()
        )

    async def _periodic_request(self):
        """Send update requests asyncio style."""
        self._hass.async_create_task(self.request_data())

        if self._fast_polling_count < 4:
            self._fast_polling_count += 1
            _LOGGER.debug("Periodic data request executed, now wait for "
                          "2 seconds.")
            await asyncio.sleep(2)
        else:
            _LOGGER.debug("Periodic data request executed, now wait for "
                          "%s seconds.", str(self._refresh_interval))
            await asyncio.sleep(self._refresh_interval)

        _LOGGER.debug("Periodic data request rescheduled.")
        self._polling_task = self._hass.loop.create_task(
            self._periodic_request()
        )

    async def setup(self, loop=None):
        await super().setup(loop)

        # Request initial values and extract serial number
        await self.request_data()
        if self.get_value('Serial') is not None:
            self.device_name = "keba_wallbox_" + str(self.get_value('Serial'))
        else:
            _LOGGER.warning("Could not load the serial number of the "
                            "charging station, unique id will be wrong")

    def hass_callback(self, data):
        """Handle component notification via callback."""

        # Inform entities about updated values
        for listener in self._update_listeners:
            listener()

        _LOGGER.debug("Notifying %d listeners", len(self._update_listeners))

    def _set_fast_polling(self):
        _LOGGER.debug("Fast polling enabled")
        self._fast_polling_count = 0
        self._polling_task.cancel()
        self._polling_task = self._hass.loop.create_task(
            self._periodic_request()
        )

    def add_update_listener(self, listener):
        """Add a listener for update notifications."""
        self._update_listeners.append(listener)

        # initial data is already loaded, thus update the component
        listener()

    async def async_set_energy(self, param):
        """Set energy target in async way."""
        try:
            energy = param['energy']
            await self.set_energy(energy)
            self._set_fast_polling()
        except (KeyError, ValueError) as ex:
            _LOGGER.warning("Energy value is not correct %s", ex)

    async def async_set_current(self, param):
        """Set current maximum in async way."""
        try:
            current = param['current']
            await self.set_current(current)
            # No fast polling as this function might be called regularly
        except (KeyError, ValueError) as ex:
            _LOGGER.warning("Current value is not correct %s", ex)

    async def async_start(self, param=None):
        """Authorize EV in async way."""
        await self.start(self.rfid)
        self._set_fast_polling()

    async def async_stop(self, param=None):
        """De-authorize EV in async way."""
        await self.stop(self.rfid)
        self._set_fast_polling()

    async def async_enable_ev(self, param=None):
        """Enable EV in async way."""
        await self.enable(True)
        self._set_fast_polling()

    async def async_disable_ev(self, param=None):
        """Disable EV in async way."""
        await self.enable(False)
        self._set_fast_polling()

    async def async_set_failsafe(self, param=None):
        """Set failsafe mode in async way."""
        try:
            timout = param['failsafe_timeout']
            fallback = param['failsafe_fallback']
            persist = param['failsafe_persist']
            await self.set_failsafe(timout, fallback, persist)
            self._set_fast_polling()
        except (KeyError, ValueError) as ex:
            _LOGGER.warning("failsafe_timeout, failsafe_fallback and/or "
                            "failsafe_persist value are not correct %s", ex)
