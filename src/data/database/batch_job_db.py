"""Batch job tracking for AI processing."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class BatchJobDB:
    """Tracks Google Batch API job state in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    input_file TEXT,
                    uploaded_file_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT DEFAULT ''
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def add_job(self, job_name: str, status: str, input_file: str, uploaded_file_name: str):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO batch_jobs (job_name, status, input_file, uploaded_file_name)
                VALUES (?, ?, ?, ?)
            """, (job_name, status, input_file, uploaded_file_name))
            conn.commit()
        finally:
            conn.close()

    def update_status(self, job_name: str, new_status: str, details: str = ""):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE batch_jobs
                SET status = ?, details = ?, updated_at = ?
                WHERE job_name = ?
            """, (new_status, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_name))
            conn.commit()
        finally:
            conn.close()

    def get_active_job(self) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM batch_jobs
                WHERE status NOT IN ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED',
                                     'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED')
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_job(self, job_name: str) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_jobs WHERE job_name = ?", (job_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
