#!/usr/bin/env python3
"""Read-only audit of benchmark results against per-run summaries.

- When run without arguments: audits historical pilot (results/pilot-results.json)
  and expects historical P2/P3 discrepancies.
- When run with a file path: audits that results file against its per-run summary.json files.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PILOT = ROOT / "results" / "pilot-results.json"
RUNS = ROOT / "results" / "runs"
LEGACY_LABELS = {
    "A": "pilot-01_A_task-l",
    "P1": "pilot-02_P1_task-l",
    "P2": "pilot-03_P2_task-l",
    "P3": "pilot-04_P3_task-l",
}


def audit(target_file: Path):
    if not target_file.is_file():
        print(f"MISSING: {target_file}")
        return 2

    data = json.loads(target_file.read_text(encoding="utf-8"))
    failures = []
    is_legacy = target_file == DEFAULT_PILOT

    print(f"[reconcile] Auditing {len(data)} run(s) from {target_file.name}...")

    for row in data:
        pid = row["profile_id"]
        run_id = row.get("run_id")
        tid = row.get("task_id", "task-l")

        if is_legacy:
            summary_path = RUNS / LEGACY_LABELS[pid] / "summary.json"
        else:
            summary_path = RUNS / f"{run_id}_{pid}_{tid}" / "summary.json"

        if not summary_path.is_file():
            failures.append(f"{run_id} ({pid}): summary.json missing at {summary_path}")
            continue

        original = json.loads(summary_path.read_text(encoding="utf-8"))
        p = row.get("per_request_usage", [])
        inp = sum(x.get("input", 0) for x in p)
        cached = sum(x.get("cacheRead", 0) for x in p)
        output = sum(x.get("output", 0) for x in p)
        reported = sum(x.get("reported_cost", 0) for x in p)

        for field, expected in (
            ("input_tokens", inp),
            ("cache_read_tokens", cached),
            ("output_tokens", output),
        ):
            if row.get(field) != expected:
                failures.append(f"{run_id or pid}: {field} mismatch {row.get(field)} != {expected}")

        if abs(reported - row.get("reported_cost", 0)) > 0.000002:
            failures.append(f"{run_id or pid}: per-request reported costs do not reconcile")

        for key in (
            "secondary_metrics",
            "optimization_metrics",
            "optimization_status",
            "net_end_to_end_cost",
        ):
            if original.get(key) != row.get(key):
                failures.append(f"{run_id or pid}: {key} differs between per-run and aggregate")

        print(
            f"  [{run_id or pid}] pid={pid} rep={row.get('repetition', 1)}: "
            f"reported_primary=${reported:.6f}; "
            f"requests={len(p)}; peak={row.get('peak_input_context')}; "
            f"opt_status={row.get('optimization_status')}"
        )

    if failures:
        print("\nReconciliation discrepancies found:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("\nAll metrics successfully reconciled with per-run evidence.")
        return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_PILOT
    sys.exit(audit(target))
