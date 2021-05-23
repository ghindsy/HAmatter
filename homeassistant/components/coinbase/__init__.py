"""Support for Coinbase."""
from datetime import timedelta
import logging

from coinbase.wallet.client import Client
from coinbase.wallet.error import AuthenticationError
import voluptuous as vol

from homeassistant.const import CONF_API_KEY
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DOMAIN = "coinbase"

CONF_API_SECRET = "api_secret"
CONF_ACCOUNT_CURRENCIES = "account_balance_currencies"
CONF_EXCHANGE_CURRENCIES = "exchange_rate_currencies"
CONF_NATIVE_CURRENCY = "native_currency"

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

DATA_COINBASE = "coinbase_cache"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_API_SECRET): cv.string,
                vol.Optional(CONF_NATIVE_CURRENCY, default="USD"): cv.string,
                vol.Optional(CONF_ACCOUNT_CURRENCIES): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_EXCHANGE_CURRENCIES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set up the Coinbase component.

    Will automatically setup sensors to support
    wallets discovered on the network.
    """
    api_key = config[DOMAIN][CONF_API_KEY]
    api_secret = config[DOMAIN][CONF_API_SECRET]
    account_currencies = config[DOMAIN].get(CONF_ACCOUNT_CURRENCIES)
    exchange_currencies = config[DOMAIN][CONF_EXCHANGE_CURRENCIES]
    native_currency = config[DOMAIN][CONF_NATIVE_CURRENCY]

    hass.data[DATA_COINBASE] = coinbase_data = CoinbaseData(api_key, api_secret, native_currency)

    if not hasattr(coinbase_data, "accounts"):
        return False
    for account in coinbase_data.accounts:
        if account_currencies is None or account.currency in account_currencies:
            load_platform(hass, "sensor", DOMAIN, {"account": account}, config)
    for currency in exchange_currencies:
        if currency not in coinbase_data.exchange_rates.rates:
            _LOGGER.warning("Currency %s not found", currency)
            continue
        load_platform(
            hass,
            "sensor",
            DOMAIN,
            {"native_currency": native_currency, "exchange_currency": currency},
            config,
        )

    return True


class CoinbaseData:
    """Get the latest data and update the states."""

    def __init__(self, api_key, api_secret, native_currency):
        """Init the coinbase data object."""

        self.client = Client(api_key, api_secret)
        self.update(native_currency)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self, native_currency):
        """Get the latest data from coinbase."""

        try:
            response = self.client.get_accounts()
            accounts = response["data"]

            # Most of Coinbase's API seems paginated now (25 items per page, but first page has 24).
            # This API gives a 'next_starting_after' property to send back as a 'starting_after' param.
            # Their API documentation is not up to date when writing these lines (2021-05-20)
            next_starting_after = response.pagination.next_starting_after

            while next_starting_after:
                response = self.client.get_accounts(starting_after=next_starting_after)
                accounts = accounts + response["data"]
                next_starting_after = response.pagination.next_starting_after

            self.accounts = accounts

            self.exchange_rates = self.client.get_exchange_rates(currency=native_currency)
        except AuthenticationError as coinbase_error:
            _LOGGER.error(
                "Authentication error connecting to coinbase: %s", coinbase_error
            )
