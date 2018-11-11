"""The tests for generic camera component."""
import io

from datetime import timedelta

from homeassistant import core as ha
from homeassistant.components import webhook
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util


async def test_bad_posting(aioclient_mock, hass, aiohttp_client):
    """Test that posting to wrong api endpoint fails."""
    await async_setup_component(hass, webhook.DOMAIN, {})
    await async_setup_component(hass, 'camera', {
        'camera': {
            'platform': 'push',
            'name': 'config_test',
            'webhook_id': 'camera.config_test'
        }})
    await hass.async_block_till_done()
    client = await aiohttp_client(hass.http.app)

    # wrong webhook
    files = {'image': io.BytesIO(b'fake')}
    resp = await client.post('/api/webhood/camera.wrong', data=files)
    assert resp.status == 404

    # missing file
    camera_state = hass.states.get('camera.config_test')
    assert camera_state.state == 'idle'

    resp = await client.post('/api/webhook/camera.config_test')
    assert resp.status == 200  # webhooks always return 200

    camera_state = hass.states.get('camera.config_test')
    assert camera_state.state == 'idle'  # no file supplied we are still idle


async def test_posting_url(hass, aiohttp_client):
    """Test that posting to api endpoint works."""
    await async_setup_component(hass, webhook.DOMAIN, {})
    await async_setup_component(hass, 'camera', {
        'camera': {
            'platform': 'push',
            'name': 'config_test',
            'webhook_id': 'camera.config_test'
        }})
    await hass.async_block_till_done()

    client = await aiohttp_client(hass.http.app)
    files = {'image': io.BytesIO(b'fake')}

    # initial state
    camera_state = hass.states.get('camera.config_test')
    assert camera_state.state == 'idle'

    # post image
    resp = await client.post(
        '/api/webhook/camera.config_test',
        data=files)
    assert resp.status == 200

    # state recording
    camera_state = hass.states.get('camera.config_test')
    assert camera_state.state == 'recording'

    # await timeout
    shifted_time = dt_util.utcnow() + timedelta(seconds=15)
    hass.bus.async_fire(ha.EVENT_TIME_CHANGED, {ha.ATTR_NOW: shifted_time})
    await hass.async_block_till_done()

    # back to initial state
    camera_state = hass.states.get('camera.config_test')
    assert camera_state.state == 'idle'
