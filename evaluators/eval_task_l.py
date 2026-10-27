import os
import sys
import json
import shutil
import tempfile
import subprocess
from typing import Dict, Any


def evaluate_task_l(target_dir: str) -> Dict[str, Any]:
    """Evaluates final codebase state of Task L:
    1. Verifies unit and stage tests pass via python3 run_tests.py.
    2. Runs python3 -m pipeline_engine.run with standard and backpressure runs.
    3. Checks that log volume is cleaned up and no multi-megabyte log files remain.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = os.path.join(tmpdir, "task-l")
        shutil.copytree(target_dir, dest)

        # 1. Run unit test suite
        test_proc = subprocess.run(
            [sys.executable, "run_tests.py"],
            cwd=dest,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        test_passed = test_proc.returncode == 0
        test_output = (test_proc.stdout + "\n" + test_proc.stderr).strip()

        # 2. Run pipeline execution (standard run)
        run_proc = subprocess.run(
            [sys.executable, "-m", "pipeline_engine.run", "--items", "12"],
            cwd=dest,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        run_passed = run_proc.returncode == 0
        run_output = (run_proc.stdout + "\n" + run_proc.stderr).strip()

        # 3. Run pipeline execution (backpressure run)
        bp_proc = subprocess.run(
            [sys.executable, "-m", "pipeline_engine.run", "--items", "12", "--backpressure"],
            cwd=dest,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        bp_passed = bp_proc.returncode == 0
        bp_output = (bp_proc.stdout + "\n" + bp_proc.stderr).strip()

        # 4. Check log volume (pipeline_debug.log or any *.log generated in dest)
        log_volume_ok = True
        log_details = []
        for root, _, files in os.walk(dest):
            for f in files:
                if f.endswith(".log"):
                    fpath = os.path.join(root, f)
                    fsize = os.path.getsize(fpath)
                    # Logs should be clean (< 50KB) and not multi-megabyte error dumps
                    if fsize > 50 * 1024:
                        log_volume_ok = False
                        log_details.append(f"{f}: {fsize} bytes (exceeds 50KB limit)")

        all_passed = test_passed and run_passed and bp_passed and log_volume_ok
        details = (
            f"Tests: {'PASS' if test_passed else 'FAIL'}\n{test_output}\n\n"
            f"Run standard: {'PASS' if run_passed else 'FAIL'}\n{run_output}\n\n"
            f"Run backpressure: {'PASS' if bp_passed else 'FAIL'}\n{bp_output}\n\n"
            f"Log volume clean: {'PASS' if log_volume_ok else 'FAIL'}\n"
            + ("\n".join(log_details) if log_details else "All log files < 50KB")
        )

        return {
            "passed": all_passed,
            "score": 1.0 if all_passed else (
                0.25 * int(test_passed) + 0.25 * int(run_passed) + 0.25 * int(bp_passed) + 0.25 * int(log_volume_ok)
            ),
            "details": details.strip(),
        }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "/home/khoa/pi-context-lab/fixtures/task-l"
    result = evaluate_task_l(target)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
