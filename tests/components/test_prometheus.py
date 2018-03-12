"""The tests for the Prometheus exporter."""
import asyncio
import pytest

from homeassistant.setup import async_setup_component
import homeassistant.components.prometheus as prometheus


@pytest.fixture
def prometheus_client(loop, hass, test_client):
    """Initialize a test_client with Prometheus component."""
    assert loop.run_until_complete(async_setup_component(
        hass,
        prometheus.DOMAIN,
        {},
    ))
    return loop.run_until_complete(test_client(hass.http.app))


@asyncio.coroutine
def test_view(prometheus_client):
    """Test prometheus metrics view."""
    resp = yield from prometheus_client.get(prometheus.API_ENDPOINT)

    assert resp.status == 200
    assert resp.headers['content-type'] == 'text/plain'
    body = yield from resp.text()
    body = body.split("\n")

    assert len(body) > 3  # At least two comment lines and a metric
    for line in body:
        if line:
            assert line.startswith('# ') \
                or line.startswith('process_') \
                or line.startswith('python_info')
