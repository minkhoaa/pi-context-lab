# Task L Evaluator Hardening & Independent Validation Report

## Executive Summary

This report documents the architectural hardening of the Task L independent evaluator (`evaluators/eval_task_l.py`), the frozen external test suite (`evaluators/task_l_hidden_checks.py`), the documentation and resolution of canonical specification discrepancies, and the offline regression verification across all four required test fixtures.

---

## 1. Evaluator Architecture & Isolation

In early benchmark pilots, evaluation relied primarily on the worker-visible `python3 run_tests.py` inside the candidate workspace. This created a critical vulnerability: workers could alter unit tests, suppress assertions, or delete test files to manufacture a false `PASS`.

To ensure evaluation integrity:
1. **Isolated Execution Directory:**
   The evaluator creates a private, isolated copy of the candidate workspace in a temporary directory (`tempfile.TemporaryDirectory()`). Tests are executed without polluting the workspace or host environment.
2. **Evaluator-Owned Hidden Tests:**
   The external hidden test suite (`evaluators/task_l_hidden_checks.py`) resides outside the worker workspace and is referenced via `PYTHONPATH`. Workers cannot inspect, edit, or tamper with these tests.
3. **Workspace Test Tamper Detection:**
   Before running any workspace tests, `eval_task_l.py` compares worker-visible test files (`run_tests.py`, `tests/test_pipeline.py`) byte-for-byte against the frozen canonical files in `fixtures/task-l/`. If any modification is detected, `workspace_tests_immutable` is set to `False`, and the run is rejected.

---

## 2. Specification Audit & Discrepancy Resolution

### A. The Discrepancy in `test_reject_zero_or_negative_count`
In the initial hidden test implementation, `test_reject_zero_or_negative_count` tested:
```python
for n in (0, -1):
    with self.assertRaises((ValueError, TypeError)):
        ChunkBuffer().push(chunk(1, n, True))
```
This asserted that `n = 0` (an empty chunk with `count: 0, items: []`) **must raise** a `ValueError` or `TypeError`.

### B. Audit Against Canonical Specification
- **Task L Turn 2 Prompt:**
  `"1. Implement your repair in pipeline_engine/buffer.py to allow final chunks (chunk.is_last == True) or partial chunks where count <= expected_size to be accepted."`
- **Canonical Fixture Docstring (`buffer.py`):**
  `"# Bug: Doesn't allow chunks with size <= expected_size when chunk.is_last is True"`
  `"# Instead, it strictly asserts count == expected_size"`
- **Streaming Semantics (`stream.py`):**
  `DataStream` yields chunks where `len(items) >= 1`. An empty stream yields 0 chunks.

### C. Finding
Requiring `count == 0` to raise `ValueError` directly contradicts the prompt's instruction: *"allow ... partial chunks where count <= expected_size to be accepted"*, because `0 <= 5`. 
In all four original pilot runs, every model followed this prompt literally and allowed `0 <= count <= expected_size` (e.g. `actual_count < 0 or actual_count > expected_size`).
Because of this test flaw, the fully correct implementation in `pilot-01` (which solved the buffer bug, aggregator backpressure, and compact logging without tampering) was marked `FAIL` solely on `n = 0`.

### D. Resolution
1. **Negative counts (`n < 0`, e.g. `-1`, `-5`)** and invalid non-integer counts represent unambiguous corruption and **must raise `(ValueError, TypeError)`**.
2. **Empty chunks (`count = 0, items = []`)** are handled cleanly without crashing or corrupting buffer state. If a candidate accepts or rejects zero-count chunks, it passes as long as negative counts are strictly rejected.
3. Tests were expanded to 22 thorough regression checks covering all pipeline semantics.

---

## 3. Comprehensive Regression Coverage

The hidden test suite (`evaluators/task_l_hidden_checks.py`) was expanded to verify:

| Category | Test Methods | Description |
|---|---|---|
| **Stream Chunking** | `test_stream_exact` | Verifies chunk sizes `(5, 5, 2)` for 12 items. |
| **Partial Final Chunks** | `test_accept_final_partial`, `test_accept_final_partial_various_sizes` | Verifies partial chunks of sizes 1, 2, 3, 4 with `is_last=True` are accepted. |
| **Full Chunks** | `test_accept_full_chunk` | Verifies full chunk of size 5 is accepted. |
| **Oversized Chunks** | `test_reject_oversized` | Verifies chunks of size 6 and 10 raise `(ValueError, TypeError)`. |
| **Negative & Invalid Counts** | `test_reject_negative_count`, `test_reject_non_integer_count` | Verifies negative counts (-1, -5) and non-int ("5") raise `ValueError/TypeError`. |
| **Payload Consistency** | `test_count_matches_payload` | Verifies `count != len(items)` (3 vs 1, 1 vs 3) raises `ValueError/TypeError`. |
| **Buffer Capacity** | `test_capacity`, `test_capacity_multistep`, `test_pop_order` | Verifies capacity bounds, reject when full, and FIFO pop order. |
| **Out-of-Order Aggregation** | `test_out_of_order`, `test_out_of_order_interleaved`, `test_no_premature_order` | Verifies reordering buffers gaps (e.g., [1, 4, 2, 5, 3]) and aggregates in order. |
| **Duplicate Sequences** | `test_duplicate_rejected_or_ignored`, `test_duplicate_in_reorder_buffer` | Verifies duplicate sequence IDs are rejected or ignored without item duplication. |
| **Backpressure Delivery** | `test_large_reverse_sequence`, `test_backpressure_scrambled` | Verifies reverse delivery (16..1) and scrambled delivery ([5, 2, 8, 1, 4, 7, 3, 6]). |
| **Debug Logging Volume** | `test_compact_logging` | Verifies diagnostic error dumps remain under 50KB limit. |
| **Adversarial / Edge Cases** | `test_empty_buffer_pop`, `test_empty_aggregator_total`, `test_zero_count_handling` | Verifies pop on empty buffer returns `None`, empty aggregator returns 0. |

---

## 4. Evaluation Scoring Formula

In `evaluators/eval_task_l.py`, the score is weighted across five pillars (0.2 each):
```python
all_passed = bool(
    test_passed
    and run_passed
    and bp_passed
    and log_volume_ok
    and independent_passed
    and tests_immutable
)

score = 1.0 if all_passed else round(
    0.2 * int(test_passed and tests_immutable)
    + 0.2 * int(run_passed)
    + 0.2 * int(bp_passed)
    + 0.2 * int(log_volume_ok)
    + 0.2 * int(independent_passed),
    2,
)
```
If any pillar fails (such as test tampering, log bloat, or an independent check failure), `score` is strictly `< 1.0` and `passed` is `False`.

---

## 5. Offline Verification Results

The hardened evaluator was tested against all four mandatory scenarios via automated tests (`tests/test_evaluator_regression.py`):

| Test Case | Workspace Target | Expected | Actual Result | Status |
|---|---|---|---|---|
| **Case 1** | Original broken Task L fixture (`fixtures/task-l`) | FAIL (Score 0.0) | `passed: false, score: 0.0` | **PASS** |
| **Case 2** | Verified correct implementation (`workspaces/pilot-01_A_task-l_r1`) | PASS (Score 1.0) | `passed: true, score: 1.0` | **PASS** |
| **Case 3** | Deliberately broken aggregator (broken ingest) | FAIL (Score < 1.0) | `passed: false, score: 0.4` | **PASS** |
| **Case 4** | Tampered workspace tests (`test_pipeline.py` altered) | REJECTED | `passed: false, workspace_tests_immutable: false` | **PASS** |

All four test cases pass with 100% adherence to specifications.
