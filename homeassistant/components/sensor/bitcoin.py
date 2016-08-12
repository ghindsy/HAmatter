"""
Bitcoin information service that uses blockchain.info.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.bitcoin/
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import CONF_PLATFORM
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

REQUIREMENTS = ['blockchain==1.3.3']

OPTION_TYPES = {
    'exchangerate': ['Exchange rate (1 BTC)', None],
    'trade_volume_btc': ['Trade volume', 'BTC'],
    'miners_revenue_usd': ['Miners revenue', 'USD'],
    'btc_mined': ['Mined', 'BTC'],
    'trade_volume_usd': ['Trade volume', 'USD'],
    'difficulty': ['Difficulty', None],
    'minutes_between_blocks': ['Time between Blocks', 'min'],
    'number_of_transactions': ['No. of Transactions', None],
    'hash_rate': ['Hash rate', 'PH/s'],
    'timestamp': ['Timestamp', None],
    'mined_blocks': ['Minded Blocks', None],
    'blocks_size': ['Block size', None],
    'total_fees_btc': ['Total fees', 'BTC'],
    'total_btc_sent': ['Total sent', 'BTC'],
    'estimated_btc_sent': ['Estimated sent', 'BTC'],
    'total_btc': ['Total', 'BTC'],
    'total_blocks': ['Total Blocks', None],
    'next_retarget': ['Next retarget', None],
    'estimated_transaction_volume_usd': ['Est. Transaction volume', 'USD'],
    'miners_revenue_btc': ['Miners revenue', 'BTC'],
    'market_price_usd': ['Market price', 'USD']
}
ICON = 'mdi:currency-btc'
CONF_CURRENCY = 'currency'
CONF_DISPLAY_OPTIONS = 'display_options'

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): 'bitcoin',
    vol.Optional(CONF_CURRENCY, default='USD'): cv.string,
    vol.Required(CONF_DISPLAY_OPTIONS, default=[]):
        [vol.In(OPTION_TYPES.keys())],
})

_LOGGER = logging.getLogger(__name__)

# Return cached results if last scan was less then this time ago.
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Bitcoin sensors."""
    from blockchain import exchangerates

    currency = config.get(CONF_CURRENCY)

    if currency not in exchangerates.get_ticker():
        _LOGGER.error('Currency "%s" is not available. Using "USD"', currency)
        currency = 'USD'

    data = BitcoinData()
    dev = []
    for variable in config[CONF_DISPLAY_OPTIONS]:
        if variable not in OPTION_TYPES:
            _LOGGER.error('Option type: "%s" does not exist', variable)
        else:
            dev.append(BitcoinSensor(data, variable, currency))

    add_devices(dev)


# pylint: disable=too-few-public-methods
class BitcoinSensor(Entity):
    """Representation of a Bitcoin sensor."""

    def __init__(self, data, option_type, currency):
        """Initialize the sensor."""
        self.data = data
        self._name = OPTION_TYPES[option_type][0]
        self._unit_of_measurement = OPTION_TYPES[option_type][1]
        self._currency = currency
        self.type = option_type
        self._state = None
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    # pylint: disable=too-many-branches
    def update(self):
        """Get the latest data and updates the states."""
        self.data.update()
        stats = self.data.stats
        ticker = self.data.ticker

        # pylint: disable=no-member
        if self.type == 'exchangerate':
            self._state = ticker[self._currency].p15min
            self._unit_of_measurement = self._currency
        elif self.type == 'trade_volume_btc':
            self._state = '{0:.1f}'.format(stats.trade_volume_btc)
        elif self.type == 'miners_revenue_usd':
            self._state = '{0:.0f}'.format(stats.miners_revenue_usd)
        elif self.type == 'btc_mined':
            self._state = '{}'.format(stats.btc_mined * 0.00000001)
        elif self.type == 'trade_volume_usd':
            self._state = '{0:.1f}'.format(stats.trade_volume_usd)
        elif self.type == 'difficulty':
            self._state = '{0:.0f}'.format(stats.difficulty)
        elif self.type == 'minutes_between_blocks':
            self._state = '{0:.2f}'.format(stats.minutes_between_blocks)
        elif self.type == 'number_of_transactions':
            self._state = '{}'.format(stats.number_of_transactions)
        elif self.type == 'hash_rate':
            self._state = '{0:.1f}'.format(stats.hash_rate * 0.000001)
        elif self.type == 'timestamp':
            self._state = stats.timestamp
        elif self.type == 'mined_blocks':
            self._state = '{}'.format(stats.mined_blocks)
        elif self.type == 'blocks_size':
            self._state = '{0:.1f}'.format(stats.blocks_size)
        elif self.type == 'total_fees_btc':
            self._state = '{0:.2f}'.format(stats.total_fees_btc * 0.00000001)
        elif self.type == 'total_btc_sent':
            self._state = '{0:.2f}'.format(stats.total_btc_sent * 0.00000001)
        elif self.type == 'estimated_btc_sent':
            self._state = '{0:.2f}'.format(stats.estimated_btc_sent *
                                           0.00000001)
        elif self.type == 'total_btc':
            self._state = '{0:.2f}'.format(stats.total_btc * 0.00000001)
        elif self.type == 'total_blocks':
            self._state = '{0:.2f}'.format(stats.total_blocks)
        elif self.type == 'next_retarget':
            self._state = '{0:.2f}'.format(stats.next_retarget)
        elif self.type == 'estimated_transaction_volume_usd':
            self._state = '{0:.2f}'.format(
                stats.estimated_transaction_volume_usd)
        elif self.type == 'miners_revenue_btc':
            self._state = '{0:.1f}'.format(stats.miners_revenue_btc *
                                           0.00000001)
        elif self.type == 'market_price_usd':
            self._state = '{0:.2f}'.format(stats.market_price_usd)


class BitcoinData(object):
    """Get the latest data and update the states."""

    def __init__(self):
        """Initialize the data object."""
        self.stats = None
        self.ticker = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from blockchain.info."""
        from blockchain import statistics, exchangerates

        self.stats = statistics.get()
        self.ticker = exchangerates.get_ticker()
