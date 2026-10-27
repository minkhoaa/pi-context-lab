#!/usr/bin/env python3
"""Read-only audit of the historical pilot: do not rewrite source results.

Use this before deciding whether to run new paid model sessions.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "results" / "pilot-results.json"
RUNS = ROOT / "results" / "runs"
LABELS = {"A":"pilot-01_A_task-l", "P1":"pilot-02_P1_task-l",
          "P2":"pilot-03_P2_task-l", "P3":"pilot-04_P3_task-l"}

def audit():
    if not PILOT.is_file():
        print("MISSING: pilot-results.json")
        return 2
    data=json.loads(PILOT.read_text())
    failures=[]
    for row in data:
        pid=row["profile_id"]
        summary_path=RUNS/LABELS[pid]/"summary.json"
        original=json.loads(summary_path.read_text())
        p=row.get("per_request_usage",[])
        inp=sum(x.get("input",0) for x in p)
        cached=sum(x.get("cacheRead",0) for x in p)
        output=sum(x.get("output",0) for x in p)
        reported=sum(x.get("reported_cost",0) for x in p)
        for field,expected in (("input_tokens",inp),("cache_read_tokens",cached),
                               ("output_tokens",output)):
            if row.get(field)!=expected:
                failures.append(f"{pid}: {field} mismatch {row.get(field)} != {expected}")
        if abs(reported-row.get("reported_cost",0))>0.000002:
            failures.append(f"{pid}: per-request reported costs do not reconcile")
        for key in ("secondary_metrics","optimization_metrics","optimization_status",
                    "net_end_to_end_cost"):
            if original.get(key)!=row.get(key):
                failures.append(f"{pid}: {key} differs between per-run and aggregate")
        print(f"{pid}: reported_primary_estimate=${reported:.6f}; "
              f"legacy_modeled=${row['calculated_cost']:.6f}; "
              f"requests={len(p)}; peak={row.get('peak_input_context')}")
    print("\\n".join(failures) if failures else "All reconciled.")
    return 1 if failures else 0

if __name__=="__main__":
    sys.exit(audit())
