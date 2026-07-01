"""Job-queue integration test — enqueue -> process -> persist.

Deterministic + offline: fakeredis for the broker, RQ sync mode (is_async=False) so
the job runs inline, and a SQLite file as the shared DB (the worker's make_store and
the test's make_store point at the same file, mirroring API+worker sharing Postgres).
"""

import fakeredis
import pytest
from api.jobs import enqueue_analysis, get_queue
from api.sample_data import SAMPLE_CSV, SAMPLE_K8S, SAMPLE_TF
from api.settings import settings


@pytest.fixture
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'jobs.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "redis_url", "redis://fake")
    return url


def test_enqueue_processes_and_persists(sqlite_db):
    from api.store import make_store

    make_store()  # create tables
    queue = get_queue(connection=fakeredis.FakeStrictRedis(), is_async=False)

    enqueue_analysis(queue, "job-1", SAMPLE_TF, SAMPLE_CSV, SAMPLE_K8S, {"src": "test"})

    result = make_store().get("job-1")
    assert result is not None
    assert result.analysis.status.value == "complete"
    assert result.analysis.total_monthly_savings == 494.50
    assert len(result.findings) == 9


def test_job_is_idempotent_on_retry(sqlite_db):
    from api.store import make_store

    make_store()
    queue = get_queue(connection=fakeredis.FakeStrictRedis(), is_async=False)

    for _ in range(2):  # same id twice -> replaces, not duplicates
        enqueue_analysis(queue, "job-2", SAMPLE_TF, SAMPLE_CSV, None, {})

    assert len(make_store().get("job-2").findings) == 6  # AWS-only (no K8s here)
