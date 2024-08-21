"""Issues utility for HTML5."""

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUCCESSFUL_IMPORT_LOG = """Loading HTML5 push notification via configuration.yaml is deprecated,
 it has been automatically imported. Once you have confirmed correct
 operation, please remove HTML5 notification configuration from
 configuration.yaml""".replace("\n", "")
SUCCESSFUL_IMPORT_TRANSLATION_KEY = "deprecated_yaml"

FAILED_IMPORT_LOG = """Loading HTML5 push notification via configuration.yaml is deprecated and
 the automatic import has failed. Please remove the HTML5 notification configuration from configuration.yaml
 and setup HTML5 from scratch via the UI.""".replace("\n", "")
FAILED_IMPORT_TRANSLATION_KEY = "deprecated_yaml_import_issue"


@callback
def async_create_html5_issue(hass: HomeAssistant, import_success: bool) -> None:
    """Create issues for HTML5."""
    _LOGGER.warning(SUCCESSFUL_IMPORT_LOG if import_success else FAILED_IMPORT_LOG)

    translation_key = SUCCESSFUL_IMPORT_TRANSLATION_KEY
    if not import_success:
        translation_key = FAILED_IMPORT_TRANSLATION_KEY

    async_create_issue(
        hass,
        DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        breaks_in_ha_version="2024.7.0",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key=translation_key,
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": "HTML5 Push Notifications",
        },
    )
