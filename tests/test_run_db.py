"""Tests for RunDB — resumable AI run/chunk tracking."""

import pytest

from src.data.database.run_db import RunDB


@pytest.fixture
def run_db(tmp_path):
    return RunDB(str(tmp_path / "runs.db"))


@pytest.mark.unit
class TestRunDB:
    def test_create_run_and_chunks(self, run_db):
        run_id = run_db.create_run(False, [["A", "B"], ["C"]])
        run = run_db.get_run(run_id)
        assert run["status"] == "running"
        assert run["total_products"] == 3
        assert run["processed_products"] == 0

        chunks = run_db.chunks_for(run_id)
        assert len(chunks) == 2
        assert chunks[0]["codes"] == ["A", "B"]
        assert chunks[0]["status"] == "pending"

    def test_get_resumable_run_only_active_states(self, run_db):
        run_id = run_db.create_run(False, [["A"]])
        assert run_db.get_resumable_run()["id"] == run_id

        run_db.update_run(run_id, status="completed")
        assert run_db.get_resumable_run() is None

        run_id2 = run_db.create_run(True, [["B"]])
        run_db.update_run(run_id2, status="interrupted", detail="network lost")
        resumable = run_db.get_resumable_run()
        assert resumable["id"] == run_id2
        assert resumable["detail"] == "network lost"

    def test_mark_chunk_and_update_run_progress(self, run_db):
        run_id = run_db.create_run(False, [["A"], ["B"]])
        chunks = run_db.chunks_for(run_id)
        run_db.mark_chunk(chunks[0]["id"], "submitted", job_name="jobs/1")
        run_db.mark_chunk(chunks[0]["id"], "applied")
        run_db.update_run(run_id, processed_delta=1)

        refreshed = run_db.chunks_for(run_id)
        assert refreshed[0]["status"] == "applied"
        assert refreshed[0]["job_name"] == "jobs/1"
        assert run_db.get_run(run_id)["processed_products"] == 1
