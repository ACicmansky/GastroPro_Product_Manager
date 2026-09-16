# 2026-09-16: Concurrent Parallel Batch Chunk Processing (Sliding Window)

## Motivation
With sequential batch execution and ~18-minute turnaround time per Google Cloud Batch API job, processing 194 chunks of 50 products took ~58 hours. Because all products are independent, waiting for Chunk 1 to finish before submitting Chunk 2 was an unnecessary bottleneck.

## Implementation Details
1. **Configuration (`config.json`)**:
   - Added `"parallel_chunks": 5` inside `"ai_enhancement"`.
   - Combined with `"chunk_size": 50` and `"thinking_budget": 3072`.

2. **BatchOrchestrator (`src/ai/batch_orchestrator.py`)**:
   - Replaced sequential `for chunk in chunks:` loop in `_run_chunks` with a **sliding window concurrent dispatcher**:
     - `in_flight` dictionary tracking up to `parallel_chunks` active jobs.
     - Automatically submits pending chunks until `len(in_flight) == parallel_chunks`.
     - Single polling loop checks all active batch jobs every `poll_interval` seconds.
     - As any job reaches `JOB_STATE_SUCCEEDED`, its products are immediately parsed, merged into `df`, committed to SQLite (`ProductDB`), and the chunk is marked `applied` in `RunDB`.
     - The slot is immediately refilled on the next iteration.
     - Multi-job cancellation: on cancel, loops through all in-flight jobs and invokes `cancel_batch_job`.

3. **Automated Testing (`tests/test_batch_resume.py`)**:
   - Added `test_parallel_chunks_dispatch` (verifies concurrent submission and completion).
   - Added `test_parallel_chunks_sliding_window` (verifies dynamic refill as jobs complete).
   - Added `test_parallel_chunks_cancel_cancels_all_inflight` (verifies cancellation propagation).

## Verification
- `uv run poe check` passed with zero errors (**248 tests passed** in 9.42s).
