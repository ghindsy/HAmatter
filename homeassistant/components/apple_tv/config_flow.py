"""Config flow for Apple TV integration."""
import asyncio
from collections import deque
from ipaddress import ip_address
import logging
from random import randrange

from pyatv import exceptions, pair, scan
from pyatv.const import DeviceModel, PairingRequirement, Protocol
from pyatv.convert import model_str, protocol_str
from pyatv.helpers import get_unique_id
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import zeroconf
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_PIN
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_CREDENTIALS, CONF_IDENTIFIERS, CONF_START_OFF, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_INPUT = "device_input"

INPUT_PIN_SCHEMA = vol.Schema({vol.Required(CONF_PIN, default=None): int})

DEFAULT_START_OFF = False

DISCOVERY_AGGREGATION_TIME = 15  # seconds


async def device_scan(identifier, loop):
    """Scan for a specific device using identifier as filter."""

    def _filter_device(dev):
        if identifier is None:
            return True
        if identifier == str(dev.address):
            return True
        if identifier == dev.name:
            return True
        return any(service.identifier == identifier for service in dev.services)

    def _host_filter():
        try:
            return [ip_address(identifier)]
        except ValueError:
            return None

    # If we have an address, only probe that address to avoid
    # broadcast traffic on the network
    scan_result = await scan(loop, timeout=3, hosts=_host_filter())
    matches = [atv for atv in scan_result if _filter_device(atv)]

    if matches:
        return matches[0], matches[0].all_identifiers

    return None, None


class AppleTVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apple TV."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return AppleTVOptionsFlow(config_entry)

    def __init__(self):
        """Initialize a new AppleTVConfigFlow."""
        self.scan_filter = None
        self.atv = None
        self.atv_identifiers = None
        self.protocol = None
        self.pairing = None
        self.credentials = {}  # Protocol -> credentials
        self.protocols_to_pair = deque()

    @property
    def device_identifier(self):
        """Return a identifier for the config entry.

        A device has multiple unique identifiers, but Home Assistant only supports one
        per config entry. Normally, a "main identifier" is determined by pyatv by
        first collecting all identifiers and then picking one in a pre-determine order.
        Under normal circumstances, this works fine but if a service is missing or
        removed due to deprecation (which happened with MRP), then another identifier
        will be calculated instead. To fix this, all identifiers belonging to a device
        is stored with the config entry and one of them (could be random) is used as
        unique_id for said entry. When a new (zeroconf) service or device is
        discovered, the identifier is first used to look up if it belongs to an
        existing config entry. If that's the case, the unique_id from that entry is
        re-used, otherwise the newly discovered identifier is used instead.
        """
        for entry in self._async_current_entries():
            for identifier in self.atv.all_identifiers:
                if identifier in entry.data.get(CONF_IDENTIFIERS, [entry.unique_id]):
                    return entry.unique_id
        return self.atv.identifier

    async def async_step_reauth(self, user_input=None):
        """Handle initial step when updating invalid credentials."""
        self.context["title_placeholders"] = {
            "name": user_input[CONF_NAME],
            "type": "Apple TV",
        }
        self.scan_filter = self.unique_id
        self.context["identifier"] = self.unique_id
        return await self.async_step_reconfigure()

    async def async_step_reconfigure(self, user_input=None):
        """Inform user that reconfiguration is about to start."""
        if user_input is not None:
            return await self.async_find_device_wrapper(
                self.async_pair_next_protocol, allow_exist=True
            )

        return self.async_show_form(step_id="reconfigure")

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self.scan_filter = user_input[DEVICE_INPUT]
            try:
                await self.async_find_device()
            except DeviceNotFound:
                errors["base"] = "no_devices_found"
            except DeviceAlreadyConfigured:
                errors["base"] = "already_configured"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    self.device_identifier, raise_on_progress=False
                )
                self.context["all_identifiers"] = self.atv.all_identifiers
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(DEVICE_INPUT): str}),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> data_entry_flow.FlowResult:
        """Handle device found via zeroconf."""
        host = discovery_info.host
        self._async_abort_entries_match({CONF_ADDRESS: host})
        service_type = discovery_info.type[:-1]  # Remove leading .
        name = discovery_info.name.replace(f".{service_type}.", "")
        properties = discovery_info.properties

        # Extract unique identifier from service
        unique_id = get_unique_id(service_type, name, properties)
        if unique_id is None:
            return self.async_abort(reason="unknown")
        self.scan_filter = host

        await self._async_aggregate_discoveries(host, unique_id, service_type)
        # Scan for the device in order to extract _all_ unique identifiers assigned to
        # it. Not doing it like this will yield multiple config flows for the same
        # device, one per protocol, which is undesired.
        return await self.async_find_device_wrapper(self.async_found_zeroconf_device)

    async def _async_aggregate_discoveries(
        self, host: str, unique_id: str, service_type: str
    ) -> None:
        """Aggregate discoveries for the same host that happen inside of DISCOVERY_AGGREGATION_TIME."""
        # Wait DISCOVERY_AGGREGATION_TIME for multiple services to be
        # discovered via zeroconf.  Once the first service is discovered
        # this allows other services to be discovered inside the time
        # window before triggering a scan of the device. This prevents
        # a multiple scans of the device at the same time since each
        # apple_tv device has multiple services that are discovered by
        # zeroconf.
        #
        # Suppose we have a device with three services: A, B and C. Let's assume
        # service A is discovered by Zeroconf, triggering a device scan that also finds
        # service B but *not* C. An identifier is picked from one of the services and
        # used as unique_id. The select process is deterministic (let's say in order A,
        # B and C) but in practice that doesn't matter. So, a flow is set up for the
        # device with unique_id set to "A" for services A and B.
        #
        # Now, service C is found and the same thing happens again but only service B
        # is found. In this case, unique_id will be set to "B" which is problematic
        # since both flows really represent the same device. They will however end up
        # as two separate flows.
        #
        # To solve this, all identifiers found during a device scan is stored as
        # "all_identifiers" in the flow context. When a new service is discovered, the
        # code below will check these identifiers for all active flows and abort if a
        # match is found. Before aborting, the original flow is updated with any
        # potentially new identifiers. In the example above, when service C is
        # discovered, the identifier of service C will be inserted into
        # "all_identifiers" of the original flow (making the device complete).
        #
        await asyncio.sleep(DISCOVERY_AGGREGATION_TIME)
        #
        # Must not await until self.context[CONF_ADDRESS] is set or other flows may
        # see it to soon and all flows will lose the race and nothing moves forward
        #
        for flow in self._async_in_progress(include_uninitialized=True):
            context = flow["context"]
            if (
                context.get("source") != config_entries.SOURCE_ZEROCONF
                or context.get(CONF_ADDRESS) != host
            ):
                continue
            if unique_id not in context.get("all_identifiers", []):
                # Add potentially new identifiers from this device to the existing flow
                context["all_identifiers"].append(unique_id)
            raise data_entry_flow.AbortFlow("already_in_progress")
        self.context[CONF_ADDRESS] = host
        #
        # Safe to await again after self.context[CONF_ADDRESS] is set
        #

    async def async_found_zeroconf_device(self, user_input=None):
        """Handle device found after Zeroconf discovery."""
        self.context["all_identifiers"] = self.atv.all_identifiers
        # Also abort if an integration with this identifier already exists
        await self.async_set_unique_id(self.device_identifier)
        # but be sure to update the address if its changed so the scanner
        # will probe the new address
        self._abort_if_unique_id_configured(updates={CONF_ADDRESS: self.atv.address})
        self.context["identifier"] = self.unique_id
        return await self.async_step_confirm()

    async def async_find_device_wrapper(self, next_func, allow_exist=False):
        """Find a specific device and call another function when done.

        This function will do error handling and bail out when an error
        occurs.
        """
        try:
            await self.async_find_device(allow_exist)
        except DeviceNotFound:
            return self.async_abort(reason="no_devices_found")
        except DeviceAlreadyConfigured:
            return self.async_abort(reason="already_configured")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        return await next_func()

    async def async_find_device(self, allow_exist=False):
        """Scan for the selected device to discover services."""
        self.atv, self.atv_identifiers = await device_scan(
            self.scan_filter, self.hass.loop
        )
        if not self.atv:
            raise DeviceNotFound()

        # Protocols supported by the device are prospects for pairing
        self.protocols_to_pair = deque(
            service.protocol for service in self.atv.services if service.enabled
        )

        dev_info = self.atv.device_info
        self.context["title_placeholders"] = {
            "name": self.atv.name,
            "type": (
                dev_info.raw_model
                if dev_info.model == DeviceModel.Unknown and dev_info.raw_model
                else model_str(dev_info.model)
            ),
        }
        all_identifiers = set(self.atv.all_identifiers)
        for entry in self._async_current_entries():
            if not all_identifiers.intersection(
                entry.data.get(CONF_IDENTIFIERS, [entry.unique_id])
            ):
                continue
            if entry.data.get(CONF_ADDRESS) != self.atv.address:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_ADDRESS: self.atv.address},
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
            if not allow_exist:
                raise DeviceAlreadyConfigured()

    async def async_step_confirm(self, user_input=None):
        """Handle user-confirmation of discovered node."""
        if user_input is not None:
            expected_identifier_count = len(self.context["all_identifiers"])
            # If number of services found during device scan mismatch number of
            # identifiers collected during Zeroconf discovery, then trigger a new scan
            # with hopes of finding all services.
            import pprint

            pprint.pprint([self.context["all_identifiers"], self.atv.all_identifiers])
            if len(self.atv.all_identifiers) != expected_identifier_count:
                try:
                    await self.async_find_device()
                except DeviceNotFound:
                    return self.async_abort(reason="device_not_found")

            # If all services still were not found, bail out with an error
            if len(self.atv.all_identifiers) != expected_identifier_count:
                return self.async_abort(reason="inconsistent_device")

            return await self.async_pair_next_protocol()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self.atv.name,
                "type": model_str(self.atv.device_info.model),
            },
        )

    async def async_pair_next_protocol(self):
        """Start pairing process for the next available protocol."""
        await self._async_cleanup()

        # Any more protocols to pair? Else bail out here
        if not self.protocols_to_pair:
            return await self._async_get_entry()

        self.protocol = self.protocols_to_pair.popleft()
        service = self.atv.get_service(self.protocol)

        # Service requires a password
        if service.requires_password:
            return await self.async_step_password()

        # Figure out, depending on protocol, what kind of pairing is needed
        if service.pairing == PairingRequirement.Unsupported:
            _LOGGER.debug("%s does not support pairing", self.protocol)
            return await self.async_pair_next_protocol()
        if service.pairing == PairingRequirement.Disabled:
            return await self.async_step_protocol_disabled()
        if service.pairing == PairingRequirement.NotNeeded:
            _LOGGER.debug("%s does not require pairing", self.protocol)
            self.credentials[self.protocol.value] = None
            return await self.async_pair_next_protocol()

        _LOGGER.debug("%s requires pairing", self.protocol)

        # Protocol specific arguments
        pair_args = {}
        if self.protocol == Protocol.DMAP:
            pair_args["name"] = "Home Assistant"
            pair_args["zeroconf"] = await zeroconf.async_get_instance(self.hass)

        # Initiate the pairing process
        abort_reason = None
        session = async_get_clientsession(self.hass)
        self.pairing = await pair(
            self.atv, self.protocol, self.hass.loop, session=session, **pair_args
        )
        try:
            await self.pairing.begin()
        except exceptions.ConnectionFailedError:
            return await self.async_step_service_problem()
        except exceptions.BackOffError:
            abort_reason = "backoff"
        except exceptions.PairingError:
            _LOGGER.exception("Authentication problem")
            abort_reason = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            abort_reason = "unknown"

        if abort_reason:
            await self._async_cleanup()
            return self.async_abort(reason=abort_reason)

        # Choose step depending on if PIN is required from user or not
        if self.pairing.device_provides_pin:
            return await self.async_step_pair_with_pin()

        return await self.async_step_pair_no_pin()

    async def async_step_protocol_disabled(self, user_input=None):
        """Inform user that a protocol is disabled and cannot be paired."""
        if user_input is not None:
            return await self.async_pair_next_protocol()
        return self.async_show_form(
            step_id="protocol_disabled",
            description_placeholders={"protocol": protocol_str(self.protocol)},
        )

    async def async_step_pair_with_pin(self, user_input=None):
        """Handle pairing step where a PIN is required from the user."""
        errors = {}
        if user_input is not None:
            try:
                self.pairing.pin(user_input[CONF_PIN])
                await self.pairing.finish()
                self.credentials[self.protocol.value] = self.pairing.service.credentials
                return await self.async_pair_next_protocol()
            except exceptions.PairingError:
                _LOGGER.exception("Authentication problem")
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="pair_with_pin",
            data_schema=INPUT_PIN_SCHEMA,
            errors=errors,
            description_placeholders={"protocol": protocol_str(self.protocol)},
        )

    async def async_step_pair_no_pin(self, user_input=None):
        """Handle step where user has to enter a PIN on the device."""
        if user_input is not None:
            await self.pairing.finish()
            if self.pairing.has_paired:
                self.credentials[self.protocol.value] = self.pairing.service.credentials
                return await self.async_pair_next_protocol()

            await self.pairing.close()
            return self.async_abort(reason="device_did_not_pair")

        pin = randrange(1000, stop=10000)
        self.pairing.pin(pin)
        return self.async_show_form(
            step_id="pair_no_pin",
            description_placeholders={
                "protocol": protocol_str(self.protocol),
                "pin": pin,
            },
        )

    async def async_step_service_problem(self, user_input=None):
        """Inform user that a service will not be added."""
        if user_input is not None:
            return await self.async_pair_next_protocol()

        return self.async_show_form(
            step_id="service_problem",
            description_placeholders={"protocol": protocol_str(self.protocol)},
        )

    async def async_step_password(self, user_input=None):
        """Inform user that password is not supported."""
        if user_input is not None:
            return await self.async_pair_next_protocol()

        return self.async_show_form(
            step_id="password",
            description_placeholders={"protocol": protocol_str(self.protocol)},
        )

    async def _async_cleanup(self):
        """Clean up allocated resources."""
        if self.pairing is not None:
            await self.pairing.close()
            self.pairing = None

    async def _async_get_entry(self):
        """Return config entry or update existing config entry."""
        # Abort if no protocols were paired
        if not self.credentials:
            return self.async_abort(reason="setup_failed")

        data = {
            CONF_NAME: self.atv.name,
            CONF_CREDENTIALS: self.credentials,
            CONF_ADDRESS: str(self.atv.address),
            CONF_IDENTIFIERS: self.atv_identifiers,
        }

        existing_entry = await self.async_set_unique_id(
            self.device_identifier, raise_on_progress=False
        )

        # If an existing config entry is updated, then this was a re-auth
        if existing_entry:
            self.hass.config_entries.async_update_entry(
                existing_entry, data=data, unique_id=self.unique_id
            )
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(existing_entry.entry_id)
            )
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(title=self.atv.name, data=data)


class AppleTVOptionsFlow(config_entries.OptionsFlow):
    """Handle Apple TV options."""

    def __init__(self, config_entry):
        """Initialize Apple TV options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the Apple TV options."""
        if user_input is not None:
            self.options[CONF_START_OFF] = user_input[CONF_START_OFF]
            return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_START_OFF,
                        default=self.config_entry.options.get(
                            CONF_START_OFF, DEFAULT_START_OFF
                        ),
                    ): bool,
                }
            ),
        )


class DeviceNotFound(HomeAssistantError):
    """Error to indicate device could not be found."""


class DeviceAlreadyConfigured(HomeAssistantError):
    """Error to indicate device is already configured."""
