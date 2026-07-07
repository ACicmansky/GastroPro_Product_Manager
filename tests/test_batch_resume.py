"""Tests for chunked, resumable AI batch processing (BatchOrchestrator + RunDB)."""

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from src.ai.batch_orchestrator import BatchOrchestrator
from src.ai.result_parser import ResultParser
from src.ai.run_control import RunControl
from src.data.database.run_db import RunDB

pytestmark = pytest.mark.ai_enhancement


class FakeClient:
    """Fake Gemini batch API: jobs complete synchronously unless job_name is 'unreachable'."""

    def __init__(self):
        self.is_available = True
        self.model_name = "fake"
        self.uploads = {}
        self.jobs = {}
        self.create_calls = 0
        self.unreachable_jobs = set()
        self.fail_downloads = False

    def upload_file(self, file_path):
        name = f"uploaded/{len(self.uploads)}"
        with open(file_path, encoding="utf-8") as f:
            self.uploads[name] = f.read()
        return name

    def create_batch_job(self, uploaded_name, model=None):
        self.create_calls += 1
        job_name = f"job/{self.create_calls - 1}"
        self.jobs[job_name] = uploaded_name
        return SimpleNamespace(name=job_name, state=SimpleNamespace(name="JOB_STATE_PENDING"))

    def get_batch_job(self, job_name):
        if job_name in self.unreachable_jobs:
            raise RuntimeError("network down")
        return SimpleNamespace(
            name=job_name,
            state=SimpleNamespace(name="JOB_STATE_SUCCEEDED"),
            dest=SimpleNamespace(file_name=f"dest/{job_name}"),
        )

    def download_file(self, file_name):
        if self.fail_downloads:
            raise RuntimeError("download failed")
        job_name = file_name.replace("dest/", "")
        raw = self.uploads[self.jobs[job_name]]
        codes = []
        for line in raw.splitlines():
            req = json.loads(line)
            text = req["request"]["contents"][0]["parts"][0]["text"]
            codes.extend(p["code"] for p in json.loads(text))
        items = [{"code": c} for c in codes]
        line = json.dumps({"response": {"candidates": [{"content": {"parts": [{"text": json.dumps(items)}]}}]}})
        return line + "\n"

    def delete_file(self, file_name):
        pass

    def cancel_batch_job(self, job_name):
        pass


def _make_df(cat):
    return pd.DataFrame({
        "code": ["P1", "P2", "P3", "P4"],
        "name": ["N1", "N2", "N3", "N4"],
        "shortDescription": [""] * 4,
        "description": [""] * 4,
        "newCategory": [cat] * 4,
        "aiProcessed": [""] * 4,
    })


def _config(tmp_path, **overrides):
    ai_config = {"chunk_size": 2, "poll_failure_limit": 1, "batch_size": 45,
                 "tmp_dir": str(tmp_path / "tmp")}
    ai_config.update(overrides)
    return {"ai_enhancement": ai_config}


def _known_category():
    orch = BatchOrchestrator(client=None, result_parser=None, config={})
    return next(iter(orch.category_parameters))


def test_interrupted_chunk_resumes_without_resubmitting(tmp_path):
    """Chunk 1 applies; chunk 2's job is created but unpollable -> run interrupted.
    A fresh orchestrator (same RunDB) resumes chunk 2 using its stored job_name,
    without creating a new batch job for it."""
    cat = _known_category()
    df = _make_df(cat)
    config = _config(tmp_path)
    run_db = RunDB(str(tmp_path / "runs.db"))

    client = FakeClient()
    client.unreachable_jobs.add("job/1")
    orch = BatchOrchestrator(client=client, result_parser=ResultParser(allowed_params=set()), run_db=run_db, config=config)

    updated_df, stats = orch.process(df.copy(), group1_indices=set(), progress_callback=None)

    assert client.create_calls == 2  # both chunks submitted
    assert stats["ai_processed"] == 2  # only chunk 1 applied

    resumable = run_db.get_resumable_run()
    assert resumable is not None
    assert resumable["status"] == "interrupted"
    assert resumable["processed_products"] == 2

    # "restart": network reachable again, fresh orchestrator instance
    client.unreachable_jobs.discard("job/1")
    orch2 = BatchOrchestrator(client=client, result_parser=ResultParser(allowed_params=set()), run_db=run_db, config=config)
    final_df, stats2 = orch2.process(updated_df, group1_indices=set(), progress_callback=None)

    assert client.create_calls == 2  # no new job created for chunk 2
    assert stats2["ai_processed"] == 4
    assert run_db.get_run(resumable["id"])["status"] == "completed"


def test_download_failure_interrupts_instead_of_marking_applied(tmp_path):
    """Job succeeds in the cloud but the result download fails: the chunk must stay
    'submitted' (not 'applied') and the run 'interrupted', so resume re-downloads
    the paid results instead of silently dropping them."""
    cat = _known_category()
    df = _make_df(cat)
    config = _config(tmp_path, chunk_size=10)  # single chunk
    run_db = RunDB(str(tmp_path / "runs.db"))
    client = FakeClient()
    client.fail_downloads = True
    orch = BatchOrchestrator(client=client, result_parser=ResultParser(allowed_params=set()), run_db=run_db, config=config)

    updated_df, stats = orch.process(df.copy(), group1_indices=set(), progress_callback=None)

    assert stats["ai_processed"] == 0
    resumable = run_db.get_resumable_run()
    assert resumable["status"] == "interrupted"
    assert run_db.chunks_for(resumable["id"])[0]["status"] == "submitted"

    client.fail_downloads = False
    orch2 = BatchOrchestrator(client=client, result_parser=ResultParser(allowed_params=set()), run_db=run_db, config=config)
    final_df, stats2 = orch2.process(updated_df, group1_indices=set(), progress_callback=None)

    assert client.create_calls == 1  # same job reused, no resubmission
    assert stats2["ai_processed"] == 4
    assert run_db.get_run(resumable["id"])["status"] == "completed"


def test_pause_leaves_run_resumable(tmp_path):
    """A pause request stops before polling; the run stays 'paused' for later continue."""
    cat = _known_category()
    df = _make_df(cat)
    config = _config(tmp_path, chunk_size=10)  # single chunk
    run_db = RunDB(str(tmp_path / "runs.db"))
    client = FakeClient()
    orch = BatchOrchestrator(client=client, result_parser=ResultParser(allowed_params=set()), run_db=run_db, config=config)

    control = RunControl()
    control.pause()
    updated_df, stats = orch.process(df.copy(), group1_indices=set(), progress_callback=None, control=control)

    assert stats["ai_processed"] == 0
    run = run_db.get_resumable_run()
    assert run["status"] == "paused"


def test_cancel_stops_run(tmp_path):
    cat = _known_category()
    df = _make_df(cat)
    config = _config(tmp_path, chunk_size=10)
    run_db = RunDB(str(tmp_path / "runs.db"))
    client = FakeClient()
    orch = BatchOrchestrator(client=client, result_parser=ResultParser(allowed_params=set()), run_db=run_db, config=config)

    control = RunControl()
    control.cancel()
    orch.process(df.copy(), group1_indices=set(), progress_callback=None, control=control)

    assert run_db.get_resumable_run() is None  # cancelled is not resumable
    assert run_db.get_run(1)["status"] == "cancelled"  # first run in this fresh db
