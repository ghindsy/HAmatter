"""
homeassistant.components.recorder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Component that records all events and state changes.
Allows other components to query this database.
"""
import logging
import threading
import queue
import sqlite3
from datetime import datetime, date
import json
import atexit

from homeassistant import Event, EventOrigin, State
import homeassistant.util.dt as date_util
from homeassistant.remote import JSONEncoder
from homeassistant.const import (
    MATCH_ALL, EVENT_TIME_CHANGED, EVENT_STATE_CHANGED,
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)

DOMAIN = "recorder"
DEPENDENCIES = []

DB_FILE = 'home-assistant.db'

RETURN_ROWCOUNT = "rowcount"
RETURN_LASTROWID = "lastrowid"
RETURN_ONE_ROW = "one_row"

_INSTANCE = None
_LOGGER = logging.getLogger(__name__)


def query(sql_query, arguments=None):
    """ Query the database. """
    _verify_instance()

    return _INSTANCE.query(sql_query, arguments)


def query_states(state_query, arguments=None):
    """ Query the database and return a list of states. """
    return [
        row for row in
        (row_to_state(row) for row in query(state_query, arguments))
        if row is not None]


def query_events(event_query, arguments=None):
    """ Query the database and return a list of states. """
    return [
        row for row in
        (row_to_event(row) for row in query(event_query, arguments))
        if row is not None]


def row_to_state(row):
    """ Convert a databsae row to a state. """
    try:
        return State(
            row[1], row[2], json.loads(row[3]),
            date_util.utc_from_timestamp(row[4]),
            date_util.utc_from_timestamp(row[5]))
    except ValueError:
        # When json.loads fails
        _LOGGER.exception("Error converting row to state: %s", row)
        return None


def row_to_event(row):
    """ Convert a databse row to an event. """
    try:
        return Event(row[1], json.loads(row[2]), EventOrigin[row[3].lower()],
                     date_util.utc_from_timestamp(row[5]))
    except ValueError:
        # When json.loads fails
        _LOGGER.exception("Error converting row to event: %s", row)
        return None


def run_information(point_in_time=None):
    """ Returns information about current run or the run that
        covers point_in_time. """
    _verify_instance()

    if point_in_time is None or point_in_time > _INSTANCE.recording_start:
        return RecorderRun()

    run = _INSTANCE.query(
        "SELECT * FROM recorder_runs WHERE start<? AND END>?",
        (point_in_time, point_in_time), return_value=RETURN_ONE_ROW)

    return RecorderRun(run) if run else None


def setup(hass, config):
    """ Setup the recorder. """
    # pylint: disable=global-statement
    global _INSTANCE

    _INSTANCE = Recorder(hass)

    return True


class RecorderRun(object):
    """ Represents a recorder run. """
    def __init__(self, row=None):
        self.end = None

        if row is None:
            self.start = _INSTANCE.recording_start
            self.closed_incorrect = False
        else:
            self.start = date_util.utc_from_timestamp(row[1])

            if row[2] is not None:
                self.end = date_util.utc_from_timestamp(row[2])

            self.closed_incorrect = bool(row[3])

    def entity_ids(self, point_in_time=None):
        """
        Return the entity ids that existed in this run.
        Specify point_in_time if you want to know which existed at that point
        in time inside the run.
        """
        where = self.where_after_start_run
        where_data = []

        if point_in_time is not None or self.end is not None:
            where += "AND created < ? "
            where_data.append(point_in_time or self.end)

        return [row[0] for row in query(
            "SELECT entity_id FROM states WHERE {}"
            "GROUP BY entity_id".format(where), where_data)]

    @property
    def where_after_start_run(self):
        """ Returns SQL WHERE clause to select rows
            created after the start of the run. """
        return "created >= {} ".format(_adapt_datetime(self.start))

    @property
    def where_limit_to_run(self):
        """ Return a SQL WHERE clause to limit results to this run. """
        where = self.where_after_start_run

        if self.end is not None:
            where += "AND created < {} ".format(_adapt_datetime(self.end))

        return where


class Recorder(threading.Thread):
    """
    Threaded recorder
    """
    def __init__(self, hass):
        threading.Thread.__init__(self)

        self.hass = hass
        self.conn = None
        self.queue = queue.Queue()
        self.quit_object = object()
        self.lock = threading.Lock()
        self.recording_start = date_util.utcnow()
        self.utc_offset = date_util.now().utcoffset().total_seconds()

        def start_recording(event):
            """ Start recording. """
            self.start()

        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_recording)
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, self.shutdown)
        hass.bus.listen(MATCH_ALL, self.event_listener)

    def run(self):
        """ Start processing events to save. """
        self._setup_connection()
        self._setup_run()

        while True:
            event = self.queue.get()

            if event == self.quit_object:
                self._close_run()
                self._close_connection()
                self.queue.task_done()
                return

            elif event.event_type == EVENT_TIME_CHANGED:
                self.queue.task_done()
                continue

            event_id = self.record_event(event)

            if event.event_type == EVENT_STATE_CHANGED:
                self.record_state(
                    event.data['entity_id'], event.data.get('new_state'),
                    event_id)

            self.queue.task_done()

    def event_listener(self, event):
        """ Listens for new events on the EventBus and puts them
            in the process queue. """
        self.queue.put(event)

    def shutdown(self, event):
        """ Tells the recorder to shut down. """
        self.queue.put(self.quit_object)

    def record_state(self, entity_id, state, event_id):
        """ Save a state to the database. """
        now = date_util.utcnow()

        # State got deleted
        if state is None:
            state_state = ''
            state_attr = '{}'
            last_changed = last_updated = now
        else:
            state_state = state.state
            state_attr = json.dumps(state.attributes)
            last_changed = state.last_changed
            last_updated = state.last_updated

        info = (
            entity_id, state_state, state_attr, last_changed, last_updated,
            now, self.utc_offset, event_id)

        self.query(
            "INSERT INTO states ("
            "entity_id, state, attributes, last_changed, last_updated,"
            "created, utc_offset, event_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            info)

    def record_event(self, event):
        """ Save an event to the database. """
        info = (
            event.event_type, json.dumps(event.data, cls=JSONEncoder),
            str(event.origin), date_util.utcnow(), event.time_fired,
            self.utc_offset
        )

        return self.query(
            "INSERT INTO events ("
            "event_type, event_data, origin, created, time_fired, utc_offset"
            ") VALUES (?, ?, ?, ?, ?, ?)", info, RETURN_LASTROWID)

    def query(self, sql_query, data=None, return_value=None):
        """ Query the database. """
        try:
            with self.conn, self.lock:
                _LOGGER.info("Running query %s", sql_query)

                cur = self.conn.cursor()

                if data is not None:
                    cur.execute(sql_query, data)
                else:
                    cur.execute(sql_query)

                if return_value == RETURN_ROWCOUNT:
                    return cur.rowcount
                elif return_value == RETURN_LASTROWID:
                    return cur.lastrowid
                elif return_value == RETURN_ONE_ROW:
                    return cur.fetchone()
                else:
                    return cur.fetchall()

        except sqlite3.IntegrityError:
            _LOGGER.exception(
                "Error querying the database using: %s", sql_query)
            return []

    def block_till_done(self):
        """ Blocks till all events processed. """
        self.queue.join()

    def _setup_connection(self):
        """ Ensure database is ready to fly. """
        db_path = self.hass.config.path(DB_FILE)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Make sure the database is closed whenever Python exits
        # without the STOP event being fired.
        atexit.register(self._close_connection)

        # Have datetime objects be saved as integers
        sqlite3.register_adapter(date, _adapt_datetime)
        sqlite3.register_adapter(datetime, _adapt_datetime)

        # Validate we are on the correct schema or that we have to migrate
        cur = self.conn.cursor()

        def save_migration(migration_id):
            """ Save and commit a migration to the database. """
            cur.execute('INSERT INTO schema_version VALUES (?, ?)',
                        (migration_id, date_util.utcnow()))
            self.conn.commit()
            _LOGGER.info("Database migrated to version %d", migration_id)

        try:
            cur.execute('SELECT max(migration_id) FROM schema_version;')
            migration_id = cur.fetchone()[0] or 0

        except sqlite3.OperationalError:
            # The table does not exist
            cur.execute('CREATE TABLE schema_version ('
                        'migration_id integer primary key, performed integer)')
            migration_id = 0

        if migration_id < 1:
            self.query("""
                CREATE TABLE recorder_runs (
                    run_id integer primary key,
                    start integer,
                    end integer,
                    closed_incorrect integer default 0,
                    created integer)
            """)

            self.query("""
                CREATE TABLE events (
                    event_id integer primary key,
                    event_type text,
                    event_data text,
                    origin text,
                    created integer)
            """)
            self.query(
                'CREATE INDEX events__event_type ON events(event_type)')

            self.query("""
                CREATE TABLE states (
                    state_id integer primary key,
                    entity_id text,
                    state text,
                    attributes text,
                    last_changed integer,
                    last_updated integer,
                    created integer)
            """)
            self.query('CREATE INDEX states__entity_id ON states(entity_id)')

            save_migration(1)

        if migration_id < 2:
            self.query("""
                ALTER TABLE events
                ADD COLUMN time_fired integer
            """)

            self.query('UPDATE events SET time_fired=created')

            save_migration(2)

        if migration_id < 3:
            utc_offset = self.utc_offset

            self.query("""
                ALTER TABLE recorder_runs
                ADD COLUMN utc_offset integer
            """)

            self.query("""
                ALTER TABLE events
                ADD COLUMN utc_offset integer
            """)

            self.query("""
                ALTER TABLE states
                ADD COLUMN utc_offset integer
            """)

            self.query("UPDATE recorder_runs SET utc_offset=?", [utc_offset])
            self.query("UPDATE events SET utc_offset=?", [utc_offset])
            self.query("UPDATE states SET utc_offset=?", [utc_offset])

            save_migration(3)

        if migration_id < 4:
            # We had a bug where we did not save utc offset for recorder runs
            self.query(
                """UPDATE recorder_runs SET utc_offset=?
                   WHERE utc_offset IS NULL""", [self.utc_offset])

            self.query("""
                ALTER TABLE states
                ADD COLUMN event_id integer
            """)

            save_migration(4)

    def _close_connection(self):
        """ Close connection to the database. """
        _LOGGER.info("Closing database")
        atexit.unregister(self._close_connection)
        self.conn.close()

    def _setup_run(self):
        """ Log the start of the current run. """
        if self.query("""UPDATE recorder_runs SET end=?, closed_incorrect=1
                      WHERE end IS NULL""", (self.recording_start, ),
                      return_value=RETURN_ROWCOUNT):

            _LOGGER.warning("Found unfinished sessions")

        self.query(
            """INSERT INTO recorder_runs (start, created, utc_offset)
               VALUES (?, ?, ?)""",
            (self.recording_start, date_util.utcnow(), self.utc_offset))

    def _close_run(self):
        """ Save end time for current run. """
        self.query(
            "UPDATE recorder_runs SET end=? WHERE start=?",
            (date_util.utcnow(), self.recording_start))


def _adapt_datetime(datetimestamp):
    """ Turn a datetime into an integer for in the DB. """
    return date_util.as_utc(datetimestamp.replace(microsecond=0)).timestamp()


def _verify_instance():
    """ throws error if recorder not initialized. """
    if _INSTANCE is None:
        raise RuntimeError("Recorder not initialized.")
