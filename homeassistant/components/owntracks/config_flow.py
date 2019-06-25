"""Config flow for OwnTracks."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.auth.util import generate_secret

CONF_SECRET = 'secret'
CONF_CLOUDHOOK = 'cloudhook'


def supports_encryption():
    """Test if we support encryption."""
    try:
        import nacl   # noqa pylint: disable=unused-import
        return True
    except OSError:
        return False


@config_entries.HANDLERS.register('owntracks')
class OwnTracksFlow(config_entries.ConfigFlow):
    """Set up OwnTracks."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a user initiated set up flow to create OwnTracks webhook."""
        if self._async_current_entries():
            return self.async_abort(reason='one_instance_allowed')

        if user_input is None:
            data_schema = vol.Schema({
                vol.Optional(CONF_CLOUDHOOK, default=True): bool,
            }) if self.hass.components.cloud.async_active_subscription() \
                else None

            return self.async_show_form(
                step_id='user',
                data_schema=data_schema
            )

        webhook_id, webhook_url, cloudhook = await self._get_webhook_id(
            user_input.get(CONF_CLOUDHOOK, False)
        )

        secret = generate_secret(16)

        if supports_encryption():
            secret_desc = (
                "The encryption key is {} "
                "(on Android under preferences -> advanced)".format(secret)
            )
        else:
            secret_desc = (
                "Encryption is not supported because libsodium is not "
                "installed.")

        return self.async_create_entry(
            title="OwnTracks",
            data={
                CONF_WEBHOOK_ID: webhook_id,
                CONF_SECRET: secret,
                CONF_CLOUDHOOK: cloudhook,
            },
            description_placeholders={
                'secret': secret_desc,
                'webhook_url': webhook_url,
                'android_url':
                'https://play.google.com/store/apps/details?'
                'id=org.owntracks.android',
                'ios_url':
                'https://itunes.apple.com/us/app/owntracks/id692424691?mt=8',
                'docs_url':
                'https://www.home-assistant.io/components/owntracks/'
            }
        )

    async def async_step_import(self, user_input):
        """Import a config flow from configuration."""
        webhook_id, _webhook_url, cloudhook = await self._get_webhook_id()
        secret = generate_secret(16)
        return self.async_create_entry(
            title="OwnTracks",
            data={
                CONF_WEBHOOK_ID: webhook_id,
                CONF_SECRET: secret,
                CONF_CLOUDHOOK: cloudhook,
            }
        )

    async def _get_webhook_id(self, get_cloudhook: bool = False):
        """Generate webhook ID."""
        webhook_id = self.hass.components.webhook.async_generate_id()
        if get_cloudhook and \
                self.hass.components.cloud.async_active_subscription():
            webhook_url = \
                await self.hass.components.cloud.async_create_cloudhook(
                    webhook_id
                )
            cloudhook = True
        else:
            webhook_url = \
                self.hass.components.webhook.async_generate_url(webhook_id)
            cloudhook = False

        return webhook_id, webhook_url, cloudhook
