"""Constants for dnsip integration."""
from homeassistant.const import Platform

DOMAIN = "dnsip"
PLATFORMS = [Platform.SENSOR]

CONF_HOSTNAME = "hostname"
CONF_IPV6 = "ipv6"
CONF_RESOLVER = "resolver"
CONF_RESOLVER_IPV6 = "resolver_ipv6"

DEFAULT_HOSTNAME = "myip.opendns.com"
DEFAULT_IPV6 = False
DEFAULT_NAME = "myip"
DEFAULT_RESOLVER = "208.67.222.222"
DEFAULT_RESOLVER_IPV6 = "2620:0:ccc::2"
