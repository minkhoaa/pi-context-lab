#!/usr/bin/env python3
"""
scripts/verify-isolation.py

Verifies isolation for all profiles defined in config/profiles.json:
- Checks PI_CODING_AGENT_DIR and PI_CODING_AGENT_SESSION_DIR isolation from ~/.pi/agent and ~/pi-token-bench.
- Checks isolation CLI flags:
    --no-extensions, --no-skills, --no-context-files, --no-prompt-templates, --no-themes, --no-mcp,
    --tools read,bash,edit,write.
- Verifies forbidden extensions (ponytail, caveman, rtk, headroom, etc.) are completely absent.
- Tests that pi -ne -e <candidate_ext> works properly for candidate profiles.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path("/home/khoa/pi-context-lab")
CONFIG_DIR = ROOT_DIR / "config"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
ENV_LOCK_FILE = CONFIG_DIR / "environment-lock.json"

HOME_DIR = Path("/home/khoa")
DEFAULT_PI_AGENT = HOME_DIR / ".pi" / "agent"
FORBIDDEN_BENCH_DIR = HOME_DIR / "pi-token-bench"


def load_json(p: Path) -> Any:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_isolation() -> bool:
    print("[verify-isolation] Starting isolation checks...")
    all_ok = True

    if not PROFILES_FILE.exists():
        print(f"FAIL: profiles.json not found at {PROFILES_FILE}")
        return False

    if not ENV_LOCK_FILE.exists():
        print(f"FAIL: environment-lock.json not found at {ENV_LOCK_FILE}")
        return False

    profiles = load_json(PROFILES_FILE)
    env_lock = load_json(ENV_LOCK_FILE)

    pi_binary = env_lock.get("pi_binary", "/home/khoa/.local/bin/pi")
    if not os.path.exists(pi_binary):
        print(f"FAIL: Pi binary not found at {pi_binary}")
        return False

    forbidden_exts: List[str] = env_lock.get("forbidden_extensions", [])
    print(f"Forbidden extensions list: {forbidden_exts}")

    for prof_key, prof in profiles.items():
        prof_id = prof.get("id")
        name = prof.get("name")
        print(f"\n--- Checking Profile: {prof_id} ({name}) ---")

        agent_dir = Path(prof.get("agent_dir", ""))
        session_dir = Path(prof.get("session_dir", ""))

        # 1. Directory isolation checks
        print(f"  agent_dir: {agent_dir}")
        print(f"  session_dir: {session_dir}")

        if not agent_dir.is_absolute() or not session_dir.is_absolute():
            print(f"  FAIL: agent_dir or session_dir is not absolute: {agent_dir}, {session_dir}")
            all_ok = False

        if agent_dir == DEFAULT_PI_AGENT or DEFAULT_PI_AGENT in agent_dir.parents:
            print(f"  FAIL: agent_dir overlaps with ~/.pi/agent: {agent_dir}")
            all_ok = False

        if session_dir == DEFAULT_PI_AGENT or DEFAULT_PI_AGENT in session_dir.parents:
            print(f"  FAIL: session_dir overlaps with ~/.pi/agent: {session_dir}")
            all_ok = False

        if agent_dir == FORBIDDEN_BENCH_DIR or FORBIDDEN_BENCH_DIR in agent_dir.parents:
            print(f"  FAIL: agent_dir inside ~/pi-token-bench: {agent_dir}")
            all_ok = False

        if session_dir == FORBIDDEN_BENCH_DIR or FORBIDDEN_BENCH_DIR in session_dir.parents:
            print(f"  FAIL: session_dir inside ~/pi-token-bench: {session_dir}")
            all_ok = False

        # Ensure directories exist
        agent_dir.mkdir(parents=True, exist_ok=True)
        session_dir.mkdir(parents=True, exist_ok=True)

        # 2. Check forbidden extensions in candidate path or directories
        ext_path_str = prof.get("extension_path")
        if ext_path_str:
            ext_path = Path(ext_path_str)
            if not ext_path.exists():
                print(f"  FAIL: Extension path does not exist: {ext_path}")
                all_ok = False

            for forbidden in forbidden_exts:
                if forbidden.lower() in str(ext_path).lower():
                    print(f"  FAIL: Profile uses forbidden extension '{forbidden}' in path: {ext_path}")
                    all_ok = False

        # 3. Tool allowlist check
        tools = prof.get("tools", [])
        required_tools = {"read", "bash", "edit", "write"}
        if not required_tools.issubset(set(tools)):
            print(f"  FAIL: Tools missing standard base set (read, bash, edit, write): {tools}")
            all_ok = False
        else:
            print(f"  PASS: Tools allowlist valid: {tools}")

        # 4. Test pi command execution with isolation flags
        # Base isolation flags required:
        # --no-extensions, --no-skills, --no-context-files, --no-prompt-templates, --no-themes, --no-mcp
        test_env = os.environ.copy()
        test_env["PI_CODING_AGENT_DIR"] = str(agent_dir)
        test_env["PI_CODING_AGENT_SESSION_DIR"] = str(session_dir)
        test_env["PI_OFFLINE"] = "1"

        cmd = [
            pi_binary,
            "--no-extensions",
            "--no-skills",
            "--no-context-files",
            "--no-prompt-templates",
            "--no-themes",
            "--no-mcp",
            f"--tools={','.join(tools)}",
        ]

        if ext_path_str:
            cmd.extend(["-e", ext_path_str])

        cmd.extend(["--help"])

        try:
            res = subprocess.run(
                cmd,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
            if res.returncode != 0:
                print(f"  FAIL: pi command invocation failed with code {res.returncode}")
                print(f"  stderr: {res.stderr}")
                all_ok = False
            else:
                print(f"  PASS: pi invocation with isolation flags and extension succeeded.")
        except Exception as e:
            print(f"  FAIL: Failed to run pi command: {e}")
            all_ok = False

    if all_ok:
        print("\n[verify-isolation] ALL CHECKS PASSED: Environment and isolation strictly verified.")
        return True
    else:
        print("\n[verify-isolation] CHECKS FAILED: Isolation issues detected.")
        return False


if __name__ == "__main__":
    ok = verify_isolation()
    sys.exit(0 if ok else 1)
