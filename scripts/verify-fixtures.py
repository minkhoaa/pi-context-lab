#!/usr/bin/env python3
"""
scripts/verify-fixtures.py

1. Re-hashes every file in /home/khoa/pi-context-lab/fixtures/ against fixtures/manifest.json.
2. Validates that evaluators can run offline and produce valid JSON output.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any

FIXTURES_DIR = Path("/home/khoa/pi-context-lab/fixtures")
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"
EVALUATORS_DIR = Path("/home/khoa/pi-context-lab/evaluators")


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_fixtures() -> bool:
    print("[verify-fixtures] Verifying fixture hashes against manifest...")
    all_ok = True

    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest.json not found at {MANIFEST_PATH}")
        return False

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest: Dict[str, str] = json.load(f)

    # 1. Check all files in manifest exist and hashes match
    verified_files = set()
    for rel_path_str, expected_hash in manifest.items():
        file_path = FIXTURES_DIR / rel_path_str
        if not file_path.exists():
            print(f"  FAIL: File listed in manifest does not exist: {rel_path_str}")
            all_ok = False
            continue

        verified_files.add(rel_path_str)
        actual_hash = compute_sha256(file_path)
        if actual_hash != expected_hash:
            print(f"  FAIL: Hash mismatch for {rel_path_str}: expected {expected_hash}, got {actual_hash}")
            all_ok = False

    # Check for any unexpected files in fixtures/ (excluding manifest.json and __pycache__)
    for root, dirs, files in os.walk(FIXTURES_DIR):
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(FIXTURES_DIR).as_posix()
            if rel_path == "manifest.json" or "__pycache__" in rel_path or rel_path.endswith(".pyc"):
                continue
            if rel_path not in manifest:
                print(f"  WARNING: File present in fixtures but not in manifest: {rel_path}")

    if all_ok:
        print(f"  PASS: All {len(manifest)} manifest files verified successfully.")
    else:
        print("  FAIL: Fixture manifest verification failed.")

    # 2. Validate evaluators offline execution and JSON output
    print("\n[verify-fixtures] Validating evaluators offline execution...")
    evaluators = [
        ("task-s", EVALUATORS_DIR / "eval_task_s.py", FIXTURES_DIR / "task-s"),
        ("task-m", EVALUATORS_DIR / "eval_task_m.py", FIXTURES_DIR / "task-m"),
        ("task-l", EVALUATORS_DIR / "eval_task_l.py", FIXTURES_DIR / "task-l"),
    ]

    for task_name, eval_script, fixture_target in evaluators:
        print(f"  Testing evaluator: {eval_script.name} on {fixture_target}...")
        if not eval_script.exists():
            print(f"  FAIL: Evaluator script not found: {eval_script}")
            all_ok = False
            continue

        env = os.environ.copy()
        env["PI_OFFLINE"] = "1"
        res = subprocess.run(
            [sys.executable, str(eval_script), str(fixture_target)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        raw_output = res.stdout.strip()
        try:
            parsed = json.loads(raw_output)
            required_keys = {"passed", "score", "details"}
            if not required_keys.issubset(parsed.keys()):
                print(f"  FAIL: Evaluator output JSON missing keys {required_keys}: {raw_output}")
                all_ok = False
            else:
                print(f"  PASS: {eval_script.name} produced valid JSON output (passed={parsed['passed']}, score={parsed['score']}).")
        except json.JSONDecodeError as e:
            print(f"  FAIL: Evaluator output is not valid JSON: {e}\nRaw output:\n{raw_output}\nStderr:\n{res.stderr}")
            all_ok = False

    if all_ok:
        print("\n[verify-fixtures] ALL FIXTURE CHECKS PASSED.")
        return True
    else:
        print("\n[verify-fixtures] FIXTURE CHECKS FAILED.")
        return False


if __name__ == "__main__":
    ok = verify_fixtures()
    sys.exit(0 if ok else 1)
