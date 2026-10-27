import os
import sys
import json
import shutil
import tempfile
import subprocess
from typing import Dict, Any


def evaluate_task_m(target_dir: str) -> Dict[str, Any]:
    """Evaluates Task M integration test suite and code correctness in an isolated copy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = os.path.join(tmpdir, "task-m")
        shutil.copytree(target_dir, dest)

        proc = subprocess.run(
            [sys.executable, "test_integration.py"],
            cwd=dest,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        passed = proc.returncode == 0
        details = (proc.stdout + "\n" + proc.stderr).strip()

        return {
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": details,
        }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "/home/khoa/pi-context-lab/fixtures/task-m"
    result = evaluate_task_m(target)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
