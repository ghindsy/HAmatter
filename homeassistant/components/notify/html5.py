"""
HTML5 Push Messaging notification service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.html5/
"""
import os
import logging
import json
import time
import datetime
import uuid

import voluptuous as vol
from voluptuous.humanize import humanize_error

from homeassistant.const import (HTTP_BAD_REQUEST,
                                 HTTP_INTERNAL_SERVER_ERROR)
from homeassistant.util import ensure_unique_string
from homeassistant.components.notify import (
    ATTR_TARGET, ATTR_TITLE, ATTR_DATA, BaseNotificationService,
    PLATFORM_SCHEMA)
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.frontend import add_manifest_json_key
from homeassistant.helpers import config_validation as cv

REQUIREMENTS = ['https://github.com/web-push-libs/pywebpush/archive/'
                'e743dc92558fc62178d255c0018920d74fa778ed.zip#'
                'pywebpush==0.5.0', 'PyJWT==1.4.2']

DEPENDENCIES = ['frontend']

_LOGGER = logging.getLogger(__name__)

REGISTRATIONS_FILE = 'html5_push_registrations.conf'

ATTR_GCM_SENDER_ID = 'gcm_sender_id'
ATTR_GCM_API_KEY = 'gcm_api_key'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(ATTR_GCM_SENDER_ID): cv.string,
    vol.Optional(ATTR_GCM_API_KEY): cv.string,
})

ATTR_SUBSCRIPTION = 'subscription'
ATTR_BROWSER = 'browser'

REGISTER_SCHEMA = vol.Schema({
    vol.Required(ATTR_SUBSCRIPTION): cv.match_all,
    vol.Required(ATTR_BROWSER): vol.In(['chrome', 'firefox'])
})

NOTIFY_CALLBACK_EVENT = 'html5_notification'


def get_service(hass, config):
    """Get the HTML5 push notification service."""
    json_path = hass.config.path(REGISTRATIONS_FILE)

    registrations = _load_config(json_path)

    if registrations is None:
        return None

    hass.wsgi.register_view(
        HTML5PushRegistrationView(hass, registrations, json_path))
    hass.wsgi.register_view(HTML5PushCallbackView(hass, registrations))

    gcm_api_key = config.get('gcm_api_key')
    gcm_sender_id = config.get('gcm_sender_id')

    if gcm_sender_id is not None:
        add_manifest_json_key('gcm_sender_id', config.get('gcm_sender_id'))

    return HTML5NotificationService(gcm_api_key, registrations)


def _load_config(filename):
    """Load configuration."""
    if not os.path.isfile(filename):
        return {}

    try:
        with open(filename, 'r') as fdesc:
            inp = fdesc.read()

        # In case empty file
        if not inp:
            return {}

        return json.loads(inp)
    except (IOError, ValueError) as error:
        _LOGGER.error('Reading config file %s failed: %s', filename, error)
        return None


def _save_config(filename, config):
    """Save configuration."""
    try:
        with open(filename, 'w') as fdesc:
            fdesc.write(json.dumps(config, indent=4, sort_keys=True))
    except (IOError, TypeError) as error:
        _LOGGER.error('Saving config file failed: %s', error)
        return False
    return True


class HTML5PushRegistrationView(HomeAssistantView):
    """Accepts push registrations from a browser."""

    url = '/api/notify.html5'
    name = 'api:notify.html5'

    def __init__(self, hass, registrations, json_path):
        """Init HTML5PushRegistrationView."""
        super().__init__(hass)
        self.registrations = registrations
        self.json_path = json_path

    def post(self, request):
        """Accept the POST request for push registrations from a browser."""
        try:
            data = REGISTER_SCHEMA(request.json)
        except vol.Invalid as ex:
            return self.json_message(humanize_error(request.json, ex),
                                     HTTP_BAD_REQUEST)

        name = ensure_unique_string('unnamed device',
                                    self.registrations.keys())

        self.registrations[name] = data

        if not _save_config(self.json_path, self.registrations):
            return self.json_message('Error saving registration.',
                                     HTTP_INTERNAL_SERVER_ERROR)

        return self.json_message('Push notification subscriber registered.')


class HTML5PushCallbackView(HomeAssistantView):
    """Accepts push registrations from a browser."""

    requires_auth = False
    url = '/api/notify.html5/callback'
    name = 'api:notify.html5/callback'

    def __init__(self, hass, registrations):
        """Init HTML5PushCallbackView."""
        super().__init__(hass)
        self.registrations = registrations

    def decode_jwt(self, token):
        """Find the registration that signed this JWT and return it."""
        import jwt

        # 1.  Check claims w/o verifying to see if a target is in there.
        # 2.  If target in claims, attempt to verify against the given name.
        # 2a. If decode is successful, return the payload.
        # 3.  If no target, loop through all registrations & attempt decode.
        # 3a. If a registration successfully decodes, return the payload.
        # 4.  Unable to decode the JWT, return False.

        target_check = jwt.decode(token, verify=False)
        if target_check['target'] in self.registrations.keys():
            possible_target = self.registrations[target_check['target']]
            key = possible_target['subscription']['keys']['auth']
            try:
                return jwt.decode(token, key)
            except jwt.exceptions.DecodeError:
                pass

        for reg in self.registrations.values():
            try:
                return jwt.decode(token, reg['subscription']['keys']['auth'])
            except jwt.exceptions.DecodeError:
                continue
        return False

    # The following is based on code from Auth0
    # https://auth0.com/docs/quickstart/backend/python
    # pylint: disable=too-many-return-statements
    def check_authorization_header(self, request):
        """Check the authorization header."""
        import jwt
        auth = request.headers.get('Authorization', None)
        if not auth:
            return self.json_message('Authorization header is expected',
                                     status_code=401)

        parts = auth.split()

        if parts[0].lower() != 'bearer':
            return self.json_message('Authorization header must '
                                     'start with Bearer', status_code=401)
        elif len(parts) != 2:
            return self.json_message('Authorization header must '
                                     'be Bearer token', status_code=401)

        token = parts[1]
        try:
            payload = self.decode_jwt(token)
        except jwt.exceptions.InvalidTokenError:
            return self.json_message('token is invalid', status_code=401)
        return payload

    def post(self, request):
        """Accept the POST request for push registrations event callback."""
        auth_check = self.check_authorization_header(request)
        if not isinstance(auth_check, dict):
            return auth_check

        event_payload = {
            'tag': request.json.get('tag', None),
            'type': request.json['type'],
            'target': auth_check['target'],
        }

        if request.json.get('action') is not None:
            event_payload['action'] = request.json.get('action')

        event_name = '{}.{}'.format(NOTIFY_CALLBACK_EVENT,
                                    event_payload['type'])
        self.hass.bus.fire(event_name, event_payload)
        return self.json({'status': 'ok',
                          'event': event_payload['type']})


# pylint: disable=too-few-public-methods
class HTML5NotificationService(BaseNotificationService):
    """Implement the notification service for HTML5."""

    # pylint: disable=too-many-arguments
    def __init__(self, gcm_key, registrations):
        """Initialize the service."""
        self._gcm_key = gcm_key
        self.registrations = registrations

    @property
    def targets(self):
        """Return a dictionary of registered targets."""
        return self.registrations.keys()

    def send_message(self, message="", **kwargs):
        """Send a message to a user."""
        import jwt
        from pywebpush import WebPusher

        timestamp = int(time.time())
        tag = str(uuid.uuid4())

        payload = {
            'body': message,
            'data': {},
            'icon': '/static/icons/favicon-192x192.png',
            'tag': tag,
            'timestamp': (timestamp*1000),  # Javascript ms since epoch
            'title': kwargs.get(ATTR_TITLE)
        }

        data = kwargs.get(ATTR_DATA)

        if data:
            payload.update(data)

            if data.get('url') is not None:
                payload['data']['url'] = data.get('url')
            elif (payload['data'].get('url') is None and
                  payload.get('actions') is None):
                payload['data']['url'] = '/'

        targets = kwargs.get(ATTR_TARGET)

        if not targets:
            targets = self.registrations.keys()
        elif not isinstance(targets, list):
            targets = [targets]

        for target in targets:
            info = self.registrations.get(target)
            if info is None:
                _LOGGER.error('%s is not a valid HTML5 push notification'
                              ' target!', target)
                continue

            jwt_exp = (datetime.datetime.fromtimestamp(timestamp) +
                       datetime.timedelta(days=7))
            jwt_secret = info[ATTR_SUBSCRIPTION]['keys']['auth']
            jwt_claims = {'exp': jwt_exp, 'nbf': timestamp,
                          'iat': timestamp, 'target': target,
                          'tag': payload['tag']}
            payload['data']['jwt'] = jwt.encode(jwt_claims,
                                                jwt_secret).decode('utf-8')

            WebPusher(info[ATTR_SUBSCRIPTION]).send(
                json.dumps(payload), gcm_key=self._gcm_key, ttl='86400')
