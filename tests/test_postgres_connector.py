import pytest
import psycopg2

from services import postgres_connector


class _Cursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return False

    def execute(self, query, params):
        self.connection.executed.append((query, params))
        if self.connection.fail_execute:
            self.connection.fail_execute = False
            raise psycopg2.OperationalError("SSL connection lost")

    def fetchone(self):
        return {"value": 1}


class _Connection:
    def __init__(self, fail_execute=False, fail_rollback=False):
        self.fail_execute = fail_execute
        self.fail_rollback = fail_rollback
        self.closed = 0
        self.autocommit = False
        self.executed = []

    def cursor(self, cursor_factory=None):
        assert cursor_factory is postgres_connector.RealDictCursor
        return _Cursor(self)

    def rollback(self):
        if self.fail_rollback:
            raise psycopg2.OperationalError("connection already closed")

    def commit(self):
        return None


class _Pool:
    def __init__(self, connections):
        self.connections = iter(connections)
        self.released = []

    def getconn(self):
        return next(self.connections)

    def putconn(self, connection, close=False):
        self.released.append((connection, close))


def test_fetch_one_retries_select_and_discards_broken_connection(monkeypatch):
    broken_connection = _Connection(fail_execute=True, fail_rollback=True)
    healthy_connection = _Connection()
    pool = _Pool([broken_connection, healthy_connection])
    monkeypatch.setattr(
        postgres_connector,
        "_get_or_create_pool",
        lambda: (pool, {}),
    )

    row = postgres_connector.fetch_one("SELECT value")

    assert row == {"value": 1}
    assert pool.released == [
        (broken_connection, True),
        (healthy_connection, False),
    ]


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO sample VALUES (1)",
        "SELECT setval('sample_id_seq', 1)",
    ],
)
def test_fetch_one_does_not_retry_mutating_queries(monkeypatch, query):
    connection = _Connection(fail_execute=True, fail_rollback=True)
    pool = _Pool([connection])
    monkeypatch.setattr(
        postgres_connector,
        "_get_or_create_pool",
        lambda: (pool, {}),
    )

    with pytest.raises(psycopg2.OperationalError):
        postgres_connector.fetch_one(query)

    assert pool.released == [(connection, True)]
