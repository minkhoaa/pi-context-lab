# Benchmark Fixtures & Evaluators Validation: pi-context-lab

**Date:** 2026-10-27  
**Validation Script:** `scripts/verify-fixtures.py`  
**Manifest:** `fixtures/manifest.json` (20 files tracked)  
**Status:** **ALL CHECKS PASSED**

---

## 1. Overview of Realistic Benchmark Tasks

Three distinct, non-overlapping workloads were designed and built entirely fresh for `pi-context-lab`. No code, tests, or prompts were copied from legacy benchmarks.

### Task S: Short Coding Session (`mini_validator`)
- **Directory:** `/home/khoa/pi-context-lab/fixtures/task-s/`
- **Architecture:** Compact Python library for data validation (`rules.py`, `validator.py`).
- **Nature of Defect:** An off-by-one boundary defect in range validation for negative index offsets in string length clamping.
- **Test Baseline:** 3 unit tests pass, exactly 1 boundary test fails.
- **Benchmark Purpose:** Evaluates whether extension startup overhead, system prompt injections, or tool registration costs impose an unnecessary token and financial penalty on brief, straightforward coding requests.

---

### Task L: Long Context & Tool-Output Pressure (`pipeline_engine`)
- **Directory:** `/home/khoa/pi-context-lab/fixtures/task-l/`
- **Architecture:** Multi-module asynchronous data pipeline (`stream.py`, `transformers.py`, `buffer.py`, `aggregator.py`, `metrics.py`, `run.py`).
- **Nature of Defect:**
  1. Stream chunk mismatch causing buffer overflow.
  2. Out-of-order chunk accumulation under backpressure.
- **Pressure Mechanism:**
  When errors occur, the pipeline dumps multi-megabyte structured JSON trace logs (`sample_logs/sample_error.log`).
- **Multi-Turn Design (4 Discrete Turns):**
  - **Turn 1 (`task-l-turn1.md`):** Inspect repository, run `pipeline_engine.run`, and diagnose stream chunk mismatch.
  - **Turn 2 (`task-l-turn2.md`):** Implement repair in `buffer.py` and run initial tests.
  - **Turn 3 (`task-l-turn3.md`):** Inspect second failure log (out-of-order chunks under backpressure) and repair `aggregator.py`.
  - **Turn 4 (`task-l-turn4.md`):** Final end-to-end verification and verify log file cleanup.
- **Benchmark Purpose:** Evaluates whether context pruning (P2), dynamic context pruning (P3), or tool-output compression (P1) genuinely reduces cumulative context and peak context across an extended multi-step debugging workflow.

---

### Task M: Multi-Service Monorepo Navigation (`micro_mesh`)
- **Directory:** `/home/khoa/pi-context-lab/fixtures/task-m/`
- **Architecture:** Local monorepo containing 5 distinct packages:
  - `packages/shared_types`
  - `packages/auth_service`
  - `packages/inventory_service`
  - `packages/billing_service`
  - `packages/gateway`
- **Nature of Defect:** Cross-service contract drift. An HTTP header name mismatch (`X-Auth-Token` vs `X-Session-Token`) between the Gateway and Billing services causes end-to-end checkout requests to fail silently with 401 Unauthorized while individual unit tests pass.
- **Benchmark Purpose:** Evaluates whether structured indexing and retrieval tools discover cross-component dependencies more efficiently than exhaustive source reads.

---

## 2. Independent Evaluators Architecture

All evaluators reside in `/home/khoa/pi-context-lab/evaluators/` and are strictly isolated from the worker execution workspace:
- `eval_task_s.py`: Runs `pytest`/`unittest` in a clean workspace copy and checks boundary conditions.
- `eval_task_l.py`: Executes multi-stage pipeline tests, validates log file retention, and confirms memory cleanliness.
- `eval_task_m.py`: Executes `test_integration.py` across all monorepo microservices.

### Standard Output Format
All evaluators return structured JSON to stdout:
```json
{
  "passed": false,
  "score": 0.0,
  "details": "Explanation of failure or pass"
}
```

### Initial State Verification
The automated verification verified that all evaluators correctly return `passed: false` and `score: 0.0` on the unfixed starting fixtures:
- `eval_task_s.py` on `fixtures/task-s`: **PASS (Expected Initial Failure Confirmed)**
- `eval_task_l.py` on `fixtures/task-l`: **PASS (Expected Initial Failure Confirmed)**
- `eval_task_m.py` on `fixtures/task-m`: **PASS (Expected Initial Failure Confirmed)**

---

## 3. Fixture SHA-256 Manifest

The integrity of all 20 fixture files is cryptographically locked in `fixtures/manifest.json`. During preflight, `scripts/verify-fixtures.py` verified that 100% of files match their recorded SHA-256 digests.
