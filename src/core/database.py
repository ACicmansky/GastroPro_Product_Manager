import sqlite3
import pandas as pd
import json
import os
import shutil
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

class ProductDatabase:
    """
    Handles SQLite database operations for the product manager.
    Acts as the source of truth, persisting internal columns and merging client updates.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the database manager with configuration.
        
        Args:
            config: Main application configuration dictionary
        """
        self.config = config
        
        # Default DB path if not defined
        self.db_path = config.get("db_path", "data/products.db")
        self.backups_dir = os.path.dirname(self.db_path) + "/backups"
        
        # Determine table schema from configuration
        self.table_name = "products"
        self.primary_key = "code"
        self._ensure_directories()
        self.init_db()

    def _ensure_directories(self):
        """Ensure necessary directories exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)
        
    def _get_connection(self):
        """Get a database connection."""
        # Using check_same_thread=False since Pandas might read it in a different thread
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_defined_columns(self) -> List[str]:
        """
        Get all defined columns from config.json to construct table schema.
        We combine final_csv_columns and new_output_columns to ensure we have all possible columns.
        """
        final_cols = self.config.get("final_csv_columns", [])
        new_cols = self.config.get("new_output_columns", [])
        
        # Add essential tracking columns just in case
        internal_cols = ["source", "last_updated", "aiProcessed", "aiProcessedDate"]
        
        all_cols = []
        # Maintain order roughly prioritizing new formats
        for c in new_cols + final_cols + internal_cols:
            if c not in all_cols:
                all_cols.append(c)
                
        # Ensure 'code' is the first column as it's our primary key
        if "code" in all_cols:
            all_cols.remove("code")
        all_cols.insert(0, "code")
        
        return all_cols

    def init_db(self):
        """Initialize database, creating the main table if it does not exist."""
        columns = self._get_defined_columns()
        
        # Build CREATE TABLE statement
        # Using TEXT for all columns to match pandas flexibility, except 'code' as primary key
        col_defs = ["\"code\" TEXT PRIMARY KEY"]
        for col in columns:
            if col != "code":
                col_defs.append(f"\"{col}\" TEXT")
                
        create_stmt = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(col_defs)})"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_stmt)
            
            # Add missing columns dynamically if configuration evolved
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            existing_cols = [row[1] for row in cursor.fetchall()]
            
            for col in columns:
                if col not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE {self.table_name} ADD COLUMN \"{col}\" TEXT")
                    except sqlite3.OperationalError as e:
                        print(f"Warning: Could not add column {col}: {e}")
                        
            # Initialize batch jobs table
            batch_table_stmt = """
            CREATE TABLE IF NOT EXISTS batch_jobs (
                job_name TEXT PRIMARY KEY,
                created_at TEXT,
                status TEXT,
                input_file TEXT,
                uploaded_file_name TEXT,
                details TEXT
            )
            """
            cursor.execute(batch_table_stmt)

            conn.commit()

    def backup_db(self, max_backups: int = 10) -> Optional[str]:
        """
        Create a backup of the current database.
        
        Args:
            max_backups: Maximum number of backups to keep (older ones deleted).
            
        Returns:
            Path to the new backup file, or None if no db exists.
        """
        if not os.path.exists(self.db_path):
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(self.db_path)
        name, ext = os.path.splitext(base_name)
        
        backup_name = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(self.backups_dir, backup_name)
        
        shutil.copy2(self.db_path, backup_path)
        print(f"Database backup created: {backup_path}")
        
        # Cleanup old backups
        backups = glob.glob(os.path.join(self.backups_dir, f"{name}_*{ext}"))
        backups.sort(key=os.path.getmtime)
        
        if len(backups) > max_backups:
            to_delete = backups[:-max_backups]
            for old_backup in to_delete:
                try:
                    os.remove(old_backup)
                except OSError as e:
                    print(f"Failed to delete old backup {old_backup}: {e}")
                    
        return backup_path

    # --- Batch Job Operations ---
    
    def add_batch_job(self, job_name: str, status: str, input_file: str, uploaded_file_name: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO batch_jobs (job_name, created_at, status, input_file, uploaded_file_name, details) VALUES (?, ?, ?, ?, ?, ?)",
                (job_name, timestamp, status, input_file, uploaded_file_name, "")
            )
            conn.commit()

    def update_batch_job_status(self, job_name: str, new_status: str, details: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE batch_jobs SET status = ?, details = ? WHERE job_name = ?",
                (new_status, details, job_name)
            )
            conn.commit()

    def get_active_batch_job(self) -> Optional[dict]:
        """Returns the most recent active batch job if any"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM batch_jobs WHERE status NOT IN ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED') ORDER BY created_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_batch_job(self, job_name: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_jobs WHERE job_name = ?", (job_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # --- End Batch Job Operations ---

    def get_all_products_df(self) -> pd.DataFrame:
        """
        Retrieve all products from the database as a pandas DataFrame.
        """
        with self._get_connection() as conn:
            # First check if table exists and has data
            try:
                df = pd.read_sql_query(f"SELECT * FROM {self.table_name}", conn)
                return df
            except pd.errors.DatabaseError:
                # Table might not exist yet if empty db
                return pd.DataFrame()

    def upsert_from_client(self, client_df: pd.DataFrame) -> pd.DataFrame:
        """
        Update the database with data from a client-provided file (XLSX/CSV).
        This does an UPSERT logic, but preserves internal columns like aiProcessed 
        from the database if the client DF is missing them or they are empty.
        
        Args:
            client_df: DataFrame from client file
            
        Returns:
            The combined state DataFrame (client updates + preserved DB columns)
        """
        if client_df.empty or "code" not in client_df.columns:
            return client_df
            
        # 1. Get current DB state
        db_df = self.get_all_products_df()
        
        if db_df.empty:
            # Nothing to preserve, just insert all
            self.upsert_final(client_df)
            return self.get_all_products_df()
            
        # 2. Identify internal columns to preserve if missing in client
        internal_cols = ["aiProcessed", "aiProcessedDate", "source", "last_updated"]
        
        # Convert DataFrames to string data type to match DB
        client_df = client_df.astype(str).replace('nan', '')
        client_df = client_df.replace('None', '')
        
        db_df = db_df.astype(str).replace('nan', '')
        db_df = db_df.replace('None', '')
        
        # We'll merge by updating the DB records with the client records
        # Set index to 'code' for easy updating
        client_indexed = client_df.set_index("code")
        db_indexed = db_df.set_index("code")
        
        # Elements in client exist in DB: UPDATE existing rows
        existing_mask = client_indexed.index.isin(db_indexed.index)
        existing_client = client_indexed[existing_mask]
        
        # Preserve internal fields explicitly for matching records
        for col in internal_cols:
            if col in db_indexed.columns:
                # If column is missing in client, add it
                if col not in existing_client.columns:
                    existing_client[col] = db_indexed.loc[existing_client.index, col]
                else:
                    # If column exists in client but has empty values, replace with DB values
                    empty_mask = (existing_client[col] == '') | (existing_client[col].isna())
                    existing_client.loc[empty_mask, col] = db_indexed.loc[existing_client.index[empty_mask], col]
                    
        # Elements only in client (New inserts)
        new_client = client_indexed[~existing_mask]
        
        # Combine updated existing records + new records
        # NOTE: client might not have sent ALL records from DB. 
        # Those not in client should still remain in DB
        
        # Combine back
        db_indexed.update(existing_client)
        combined_indexed = pd.concat([db_indexed, new_client])
        
        # Convert to string and handle NAs before saving
        combined_indexed = combined_indexed.fillna("").astype(str)
        
        # 3. Save combined dataframe to DB
        combined_df = combined_indexed.reset_index()
        self.upsert_final(combined_df)
        
        # Return the retrieved full state
        return self.get_all_products_df()

    def upsert_final(self, final_df: pd.DataFrame):
        """
        Replaces/Upserts all records in the DB with the provided final DataFrame.
        This is typically called at the end of the pipeline when external feeds and AI 
        have run, and we want to solidify the state.
        
        Args:
            final_df: The final processed DataFrame to save
        """
        if final_df.empty or "code" not in final_df.columns:
            return
            
        # Ensure column types match (SQLite TEXT)
        save_df = final_df.copy()
        for col in save_df.columns:
            # Handle list/dict objects if they accidentally got here
            save_df[col] = save_df[col].apply(lambda x: str(x) if pd.notna(x) else "")
            
        # Exclude columns not in DB schema (though schema should adapt)
        db_columns = self._get_defined_columns()
        valid_cols = [c for c in save_df.columns if c in db_columns]
        
        if "code" not in valid_cols:
            valid_cols.append("code")
            
        save_df = save_df[valid_cols]
        
        with self._get_connection() as conn:
            # Pandas default to_sql with if_exists='append' doesn't handle UPSERT gracefully
            # Instead we create a temporary table, then INSERT ON CONFLICT DO UPDATE
            
            temp_table = f"{self.table_name}_temp"
            save_df.to_sql(temp_table, conn, if_exists="replace", index=False)
            
            # Build the UPDATE clause mapping for EXCLUDED
            update_cols = [c for c in save_df.columns if c != "code"]
            set_clause = ", ".join([f"\"{c}\"=EXCLUDED.\"{c}\"" for c in update_cols])
            
            insert_stmt = f"""
            INSERT INTO {self.table_name} ("{'", "'.join(save_df.columns)}")
            SELECT "{"\", \"".join(save_df.columns)}" FROM {temp_table}
            WHERE "code" IS NOT NULL AND "code" != ''
            ON CONFLICT("code") DO UPDATE SET
            {set_clause}
            """
            
            cursor = conn.cursor()
            cursor.execute(insert_stmt)
            cursor.execute(f"DROP TABLE {temp_table}")
            conn.commit()
