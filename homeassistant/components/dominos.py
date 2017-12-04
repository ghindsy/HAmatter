"""
Support for Dominos Pizza ordering.

The Dominos Pizza component ceates a service which can be invoked to order
from their menu

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/dominos/.
"""
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components import http
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

# The domain of your component. Should be equal to the name of your component.
DOMAIN = 'dominos'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

ATTR_COUNTRY = 'country_code'
ATTR_FIRST_NAME = 'first_name'
ATTR_LAST_NAME = 'last_name'
ATTR_EMAIL = 'email'
ATTR_PHONE = 'phone'
ATTR_ADDRESS = 'address'
ATTR_ORDERS = 'orders'
ATTR_SHOW_MENU = 'show_menu'
ATTR_ORDER_ENTITY = 'order_entity_id'
ATTR_ORDER_NAME = 'name'
ATTR_ORDER_CODES = 'codes'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)
MIN_TIME_BETWEEN_STORE_UPDATES = timedelta(minutes=3330)

REQUIREMENTS = ['pizzapi==0.0.3']

DEPENDENCIES = ['http']

_ORDERS_SCHEMA = vol.Schema({
    vol.Required(ATTR_ORDER_NAME): cv.string,
    vol.Required(ATTR_ORDER_CODES): vol.All(cv.ensure_list, [cv.string]),
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(ATTR_COUNTRY): cv.string,
        vol.Required(ATTR_FIRST_NAME): cv.string,
        vol.Required(ATTR_LAST_NAME): cv.string,
        vol.Required(ATTR_EMAIL): cv.string,
        vol.Required(ATTR_PHONE): cv.string,
        vol.Required(ATTR_ADDRESS): cv.string,
        vol.Optional(ATTR_SHOW_MENU): cv.boolean,
        vol.Optional(ATTR_ORDERS): vol.All(cv.ensure_list, [_ORDERS_SCHEMA]),
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    dominos = Dominos(hass, config)

    component = EntityComponent(_LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = {}
    entities = []
    conf = config[DOMAIN]

    hass.services.register(DOMAIN, 'order', dominos.handle_order)

    if conf.get(ATTR_SHOW_MENU):
        hass.http.register_view(DominosProductListView(dominos))

    if conf.get(ATTR_ORDERS) is not None:
        for order_info in conf.get(ATTR_ORDERS):
            order = DominosOrder(order_info, dominos)
            entities.append(order)

        component.add_entities(entities)

    # Return boolean to indicate that initialization was successfully.
    return True


class Dominos():
    """Main Dominos service."""

    def __init__(self, hass, config):
        """Set up main service."""
        conf = config[DOMAIN]
        from pizzapi import Address, Customer
        from pizzapi.address import StoreException
        self.hass = hass
        self.customer = Customer(
            conf.get(ATTR_FIRST_NAME),
            conf.get(ATTR_LAST_NAME),
            conf.get(ATTR_EMAIL),
            conf.get(ATTR_PHONE),
            conf.get(ATTR_ADDRESS))
        self.address = Address(
            *self.customer.address.split(','),
            country=conf.get(ATTR_COUNTRY))
        self.country = conf.get(ATTR_COUNTRY)
        try:
            self.closest_store = self.address.closest_store()
        except StoreException:
            self.closest_store = False

    def handle_order(self, call):
        """Handle ordering pizza."""
        entity_ids = call.data.get(ATTR_ORDER_ENTITY, None)

        target_orders = [order for order in self.hass.data[DOMAIN]['entities']
                         if order.entity_id in entity_ids]

        for order in target_orders:
            order.place()

    @Throttle(MIN_TIME_BETWEEN_STORE_UPDATES)
    def update_closest_store(self):
        """Update the shared closest store (if open)."""
        from pizzapi.address import StoreException
        try:
            self.closest_store = self.address.closest_store()
        except StoreException:
            self.closest_store = False

    def get_menu(self):
        """Return the products from the closest stores menu."""
        if self.closest_store is False:
            _LOGGER.warning('Cannot get menu. Store may be closed')
            return

        menu = self.closest_store.get_menu()
        product_entries = []

        for product in menu.products:
            item = {}
            if isinstance(product.menu_data['Variants'], list):
                variants = ', '.join(product.menu_data['Variants'])
            else:
                variants = product.menu_data['Variants']
            item['name'] = product.name
            item['variants'] = variants
            product_entries.append(item)

        return product_entries


class DominosProductListView(http.HomeAssistantView):
    """View to retrieve product list content."""

    url = '/api/dominos'
    name = "api:dominos"

    def __init__(self, dominos):
        """Initialize suite view."""
        self.dominos = dominos

    @callback
    def get(self, request):
        """Retrieve if API is running."""
        return self.json(self.dominos.get_menu())


class DominosOrder(Entity):
    """Represents a Dominos order entity."""

    def __init__(self, order_info, dominos):
        """Set up the entity."""
        self._name = order_info['name']
        self._product_codes = order_info['codes']
        self._orderable = False
        self.dominos = dominos

    @property
    def name(self):
        """Return the orders name."""
        return self._name

    @property
    def product_codes(self):
        """Return the orders product codes."""
        return self._product_codes

    @property
    def orderable(self):
        """Return the true if orderable."""
        return self._orderable

    @property
    def state(self):
        """Return the state either closed, orderable or unorderable."""
        if self.dominos.closest_store is False:
            return 'closed'
        else:
            return 'orderable' if self._orderable else 'unorderable'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the order state and refreshes the store."""
        from pizzapi.address import StoreException
        try:
            self.dominos.update_closest_store()
        except StoreException:
            self._orderable = False
            return

        try:
            order = self.order()
            order.pay_with()
            self._orderable = True
        except StoreException:
            self._orderable = False

    def order(self):
        """Create the order object."""
        from pizzapi import Order
        from pizzapi.address import StoreException

        if self.dominos.closest_store is False:
            raise StoreException

        order = Order(
            self.dominos.closest_store,
            self.dominos.customer,
            self.dominos.address,
            self.dominos.country)

        for code in self._product_codes:
            order.add_item(code)

        return order

    def place(self):
        """Place the order."""
        from pizzapi.address import StoreException
        try:
            order = self.order()
            order.place()
        except StoreException:
            self._orderable = False
            _LOGGER.warning(
                'Attempted to order Dominos - Order invalid or store closed')
