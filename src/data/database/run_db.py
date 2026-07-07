"""Tracks resumable AI enhancement runs, chunked into small batch jobs.

A run pins its product set (by code) at creation time, so resuming after an
interruption (quota, network, app restart) continues the exact same set
regardless of force-mode or aiProcessed flags.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

ACTIVE_STATES = ("running", "paused", "interrupted")
TERMINAL_STATES = ("completed", "cancelled")


class RunDB:
    """Tracks enhancement_runs + run_chunks state in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS enhancement_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    force_reprocess INTEGER DEFAULT 0,
                    total_products INTEGER DEFAULT 0,
                    processed_products INTEGER DEFAULT 0,
                    detail TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS run_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES enhancement_runs(id),
                    chunk_index INTEGER NOT NULL,
                    codes TEXT NOT NULL,
                    job_name TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    detail TEXT DEFAULT ''
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def create_run(self, force_reprocess: bool, chunks: List[List[str]]) -> int:
        """Create a run and its chunk rows. chunks[i] = list of product codes for chunk i."""
        total = sum(len(c) for c in chunks)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO enhancement_runs (status, force_reprocess, total_products) "
                "VALUES ('running', ?, ?)",
                (1 if force_reprocess else 0, total),
            )
            run_id = cursor.lastrowid
            cursor.executemany(
                "INSERT INTO run_chunks (run_id, chunk_index, codes, status) VALUES (?, ?, ?, 'pending')",
                [(run_id, i, json.dumps(codes, ensure_ascii=False)) for i, codes in enumerate(chunks)],
            )
            conn.commit()
            return run_id
        finally:
            conn.close()

    def get_resumable_run(self) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM enhancement_runs WHERE status IN "
                f"({','.join('?' for _ in ACTIVE_STATES)}) ORDER BY created_at DESC LIMIT 1",
                ACTIVE_STATES,
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_run(self, run_id: int) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enhancement_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def chunks_for(self, run_id: int) -> List[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM run_chunks WHERE run_id = ? ORDER BY chunk_index", (run_id,)
            )
            chunks = []
            for row in cursor.fetchall():
                chunk = dict(row)
                chunk["codes"] = json.loads(chunk["codes"])
                chunks.append(chunk)
            return chunks
        finally:
            conn.close()

    def mark_chunk(self, chunk_id: int, status: str, job_name: str = "", detail: str = ""):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if job_name:
                cursor.execute(
                    "UPDATE run_chunks SET status = ?, job_name = ?, detail = ? WHERE id = ?",
                    (status, job_name, detail, chunk_id),
                )
            else:
                cursor.execute(
                    "UPDATE run_chunks SET status = ?, detail = ? WHERE id = ?",
                    (status, detail, chunk_id),
                )
            conn.commit()
        finally:
            conn.close()

    def update_run(self, run_id: int, status: Optional[str] = None, processed_delta: int = 0, detail: Optional[str] = None):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            sets = ["updated_at = CURRENT_TIMESTAMP", "processed_products = processed_products + ?"]
            params = [processed_delta]
            if status is not None:
                sets.append("status = ?")
                params.append(status)
            if detail is not None:
                sets.append("detail = ?")
                params.append(detail)
            params.append(run_id)
            cursor.execute(f"UPDATE enhancement_runs SET {', '.join(sets)} WHERE id = ?", params)
            conn.commit()
        finally:
            conn.close()
