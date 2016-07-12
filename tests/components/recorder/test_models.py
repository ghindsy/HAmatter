"""The tests for the Recorder component."""
# pylint: disable=too-many-public-methods,protected-access
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import homeassistant.core as ha
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.util import dt
from homeassistant.components.recorder.models import (
    Base, Events, States, RecorderRuns)

engine = None
Session = None


def setUpModule():
    """Set up a database to use."""
    global engine, Session

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)


def tearDownModule():
    """Close database."""
    global engine, Session

    engine.dispose()
    engine = None
    Session = None


class TestEvents(unittest.TestCase):
    """Test Events model."""

    def test_from_event(self):
        """Test converting event to db event."""
        event = ha.Event('test_event', {
            'some_data': 15
        })
        assert event == Events.from_event(event).to_native()


class TestStates(unittest.TestCase):
    """Test States model."""

    def test_from_event(self):
        """Test converting event to db state."""
        state = ha.State('sensor.temperature', '18')
        event = ha.Event(EVENT_STATE_CHANGED, {
            'entity_id': 'sensor.temperature',
            'old_state': None,
            'new_state': state,
        })
        assert state == States.from_event(event).to_native()

    def test_from_event_to_delete_state(self):
        """Test converting deleting state event to db state."""
        event = ha.Event(EVENT_STATE_CHANGED, {
            'entity_id': 'sensor.temperature',
            'old_state': ha.State('sensor.temperature', '18'),
            'new_state': None,
        })
        db_state = States.from_event(event)

        assert db_state.entity_id == 'sensor.temperature'
        assert db_state.domain == 'sensor'
        assert db_state.state == ''
        assert db_state.last_changed == event.time_fired
        assert db_state.last_updated == event.time_fired


class TestRecorderRuns(unittest.TestCase):
    """Test recorder run model."""

    def setUp(self):
        """Set up recorder runs."""
        self.session = session = Session()
        session.query(Events).delete()
        session.query(States).delete()
        session.query(RecorderRuns).delete()

    def tearDown(self):
        """Clean up."""
        self.session.rollback()

    def test_entity_ids(self):
        """Test if entity ids helper method works."""
        run = RecorderRuns(
            start=datetime(2016, 7, 9, 11, 0, 0, tzinfo=dt.UTC),
            end=datetime(2016, 7, 9, 23, 0, 0, tzinfo=dt.UTC),
            closed_incorrect=False,
            created=datetime(2016, 7, 9, 11, 0, 0, tzinfo=dt.UTC),
        )

        self.session.add(run)
        self.session.commit()

        before_run = datetime(2016, 7, 9, 8, 0, 0, tzinfo=dt.UTC)
        in_run = datetime(2016, 7, 9, 13, 0, 0, tzinfo=dt.UTC)
        in_run2 = datetime(2016, 7, 9, 15, 0, 0, tzinfo=dt.UTC)
        in_run3 = datetime(2016, 7, 9, 18, 0, 0, tzinfo=dt.UTC)
        after_run = datetime(2016, 7, 9, 23, 30, 0, tzinfo=dt.UTC)

        assert run.to_native() == run
        assert run.entity_ids() == []

        self.session.add(States(
            entity_id='sensor.temperature',
            state='20',
            last_changed=before_run,
            last_updated=before_run,
        ))
        self.session.add(States(
            entity_id='sensor.sound',
            state='10',
            last_changed=after_run,
            last_updated=after_run,
        ))

        self.session.add(States(
            entity_id='sensor.humidity',
            state='76',
            last_changed=in_run,
            last_updated=in_run,
        ))
        self.session.add(States(
            entity_id='sensor.lux',
            state='5',
            last_changed=in_run3,
            last_updated=in_run3,
        ))

        assert sorted(run.entity_ids()) == ['sensor.humidity', 'sensor.lux']
        assert run.entity_ids(in_run2) == ['sensor.humidity']
