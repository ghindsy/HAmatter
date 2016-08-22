"""The tests for the Demo cover platform."""
import unittest
import homeassistant.util.dt as dt_util
import logging

from datetime import timedelta
from homeassistant.components import cover
from tests.common import get_test_home_assistant, fire_time_changed

ENTITY_COVER = 'cover.living_room_window'

_LOGGER = logging.getLogger(__name__)


class TestCoverDemo(unittest.TestCase):
    """Test the Demo cover."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.assertTrue(cover.setup(self.hass, {'cover': {
            'platform': 'demo',
        }}))

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_close_cover(self):
        """Test closing the cover."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(70, state.attributes.get('current_position'))
        cover.close_cover(self.hass, ENTITY_COVER)
        _LOGGER.info("time=%s", dt_util.utcnow())
        future = dt_util.utcnow() + timedelta(seconds=7)
        fire_time_changed(self.hass, future)
        self.hass.pool.block_till_done()
        _LOGGER.info("time=%s", dt_util.utcnow())
        self.assertEqual(0, state.attributes.get('current_position'))

    def test_open_cover(self):
        """Test opening the cover."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(70, state.attributes.get('current_position'))
        cover.open_cover(self.hass, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.hass.pool.block_till_done()
        self.assertEqual(100, state.attributes.get('current_position'))

    def test_set_cover_position(self):
        """Test moving the cover to a specific position."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(70, state.attributes.get('current_position'))
        cover.set_cover_position(self.hass, 10, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.hass.pool.block_till_done()
        self.assertEqual(10, state.attributes.get('current_position'))

    def test_stop_cover(self):
        """Test stopping the cover."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(70, state.attributes.get('current_position'))
        cover.open_cover(self.hass, ENTITY_COVER)
        cover.stop_cover(self.hass, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.assertEqual(70, state.attributes.get('current_position'))

    def test_close_cover_tilt(self):
        """Test closing the cover tilt."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(50, state.attributes.get('current_tilt_position'))
        cover.close_cover_tilt(self.hass, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.hass.pool.block_till_done()
        self.assertEqual(0, state.attributes.get('current_tilt_position'))

    def test_open_cover_tilt(self):
        """Test opening the cover tilt."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(50, state.attributes.get('current_tilt_position'))
        cover.open_cover_tilt(self.hass, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.hass.pool.block_till_done()
        self.assertEqual(100, state.attributes.get('current_tilt_position'))

    def test_set_cover_tilt_position(self):
        """Test moving the cover til to a specific position."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(50, state.attributes.get('current_tilt_position'))
        cover.set_cover_tilt_position(self.hass, 90, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.hass.pool.block_till_done()
        self.assertEqual(90, state.attributes.get('current_tilt_position'))

    def test_stop_cover_tilt(self):
        """Test stopping the cover tilt."""
        state = self.hass.states.get(ENTITY_COVER)
        self.assertEqual(50, state.attributes.get('current_tilt_position'))
        cover.close_cover_tilt(self.hass, ENTITY_COVER)
        cover.stop_cover_tilt(self.hass, ENTITY_COVER)
        fire_time_changed(self.hass, dt_util.utcnow())
        self.hass.pool.block_till_done()
        self.assertEqual(50, state.attributes.get('current_tilt_position'))
