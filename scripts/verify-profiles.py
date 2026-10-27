#!/usr/bin/env python3
"""
scripts/verify-profiles.py

Loads /home/khoa/pi-context-lab/config/profiles.json.
Validates paths, tool allowlists, flags, and offline status.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

PROFILES_PATH = Path("/home/khoa/pi-context-lab/config/profiles.json")
ENV_LOCK_PATH = Path("/home/khoa/pi-context-lab/config/environment-lock.json")


def verify_profiles() -> bool:
    print(f"[verify-profiles] Loading profiles from {PROFILES_PATH}...")
    if not PROFILES_PATH.exists():
        print(f"FAIL: File not found: {PROFILES_PATH}")
        return False

    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles: Dict[str, Any] = json.load(f)

    if not ENV_LOCK_PATH.exists():
        print(f"FAIL: File not found: {ENV_LOCK_PATH}")
        return False

    with open(ENV_LOCK_PATH, "r", encoding="utf-8") as f:
        env_lock: Dict[str, Any] = json.load(f)

    pi_binary = env_lock.get("pi_binary", "/home/khoa/.local/bin/pi")

    expected_profiles = ["baseline", "sift", "context-prune", "dcp", "context-engine"]
    expected_ids = {"A", "P1", "P2", "P3", "P4"}

    found_keys = list(profiles.keys())
    found_ids = {p.get("id") for p in profiles.values()}

    print(f"Found {len(profiles)} profile definitions: {found_keys}")

    all_ok = True

    if set(expected_profiles) != set(found_keys):
        print(f"FAIL: Expected profiles {expected_profiles}, but found {found_keys}")
        all_ok = False

    if expected_ids != found_ids:
        print(f"FAIL: Expected IDs {expected_ids}, but found {found_ids}")
        all_ok = False

    for name, p in profiles.items():
        pid = p.get("id")
        pname = p.get("name")
        print(f"\nValidating Profile [{pid}] '{name}':")

        if pname != name:
            print(f"  FAIL: 'name' mismatch: {pname} != {name}")
            all_ok = False

        # Validate agent_dir & session_dir
        agent_dir = Path(p.get("agent_dir", ""))
        session_dir = Path(p.get("session_dir", ""))
        if not agent_dir.exists() or not agent_dir.is_dir():
            print(f"  FAIL: agent_dir does not exist or not a directory: {agent_dir}")
            all_ok = False
        else:
            print(f"  PASS: agent_dir exists: {agent_dir}")

        if not session_dir.exists() or not session_dir.is_dir():
            print(f"  FAIL: session_dir does not exist or not a directory: {session_dir}")
            all_ok = False
        else:
            print(f"  PASS: session_dir exists: {session_dir}")

        # Validate extension_path
        ext_path = p.get("extension_path")
        if ext_path is not None:
            ep = Path(ext_path)
            if not ep.exists() or not ep.is_file():
                print(f"  FAIL: extension_path does not exist: {ext_path}")
                all_ok = False
            else:
                print(f"  PASS: extension_path exists: {ext_path}")
        else:
            print("  PASS: Pure baseline (no extension)")

        # Validate tool allowlist
        tools = p.get("tools", [])
        if not isinstance(tools, list) or len(tools) == 0:
            print(f"  FAIL: tools must be a non-empty list: {tools}")
            all_ok = False
        else:
            for t in ["read", "bash", "edit", "write"]:
                if t not in tools:
                    print(f"  FAIL: Standard tool '{t}' missing from tools list: {tools}")
                    all_ok = False
            print(f"  PASS: Tools allowlist valid: {tools}")

        # Validate flags
        extra_flags = p.get("extra_flags", [])
        if not isinstance(extra_flags, list):
            print(f"  FAIL: extra_flags must be a list: {extra_flags}")
            all_ok = False
        if ext_path is not None:
            if "-e" not in extra_flags or ext_path not in extra_flags:
                print(f"  FAIL: extra_flags missing -e or extension path: {extra_flags}")
                all_ok = False

        # Validate offline status execution
        test_env = os.environ.copy()
        test_env["PI_OFFLINE"] = "1"
        test_env["PI_CODING_AGENT_DIR"] = str(agent_dir)
        test_env["PI_CODING_AGENT_SESSION_DIR"] = str(session_dir)

        test_cmd = [
            pi_binary,
            "--offline",
            "--no-extensions",
            "--no-skills",
            "--no-context-files",
            "--no-prompt-templates",
            "--no-themes",
            "--no-mcp",
            f"--tools={','.join(tools)}",
        ]
        test_cmd.extend(extra_flags)
        test_cmd.append("--help")

        try:
            res = subprocess.run(
                test_cmd,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
            if res.returncode != 0:
                print(f"  FAIL: Offline invocation failed with code {res.returncode}")
                print(f"  stderr: {res.stderr}")
                all_ok = False
            else:
                print("  PASS: Offline CLI invocation verified.")
        except Exception as e:
            print(f"  FAIL: Execution error testing offline status: {e}")
            all_ok = False

    if all_ok:
        print("\n[verify-profiles] ALL PROFILES VALID.")
        return True
    else:
        print("\n[verify-profiles] PROFILE VALIDATION FAILED.")
        return False


if __name__ == "__main__":
    ok = verify_profiles()
    sys.exit(0 if ok else 1)
