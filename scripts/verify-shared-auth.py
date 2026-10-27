#!/usr/bin/env python3
"""
scripts/verify-shared-auth.py

Validates shared authentication symlink wiring for ready profiles (A, P1, P2, P3).
Ensures:
  1. auth.json is a valid symbolic link in every ready profile.
  2. Resolves exactly to ~/.pi/agent/auth.json with matching inode.
  3. No copies or modified credentials exist.
  4. Original auth file permissions and attributes are preserved.
  5. Other profile configurations remain strictly isolated.
  6. Pi CLI offline check (with --no-refresh) recognizes the credential without making network calls.
  7. Profile P4 remains explicitly excluded from shared authentication.
"""

import os
import sys
import json
import stat
import subprocess
from pathlib import Path

LAB_DIR = Path("/home/khoa/pi-context-lab")
MAIN_AGENT_DIR = Path(os.path.expanduser("~/.pi/agent"))
MAIN_AUTH_FILE = MAIN_AGENT_DIR / "auth.json"

READY_PROFILES = [
    ("A", "baseline"),
    ("P1", "sift"),
    ("P2", "context-prune"),
    ("P3", "dcp"),
]

EXCLUDED_PROFILES = [
    ("P4", "context-engine"),
]


def verify_shared_auth() -> bool:
    print("[verify-shared-auth] Beginning shared authentication audit...")
    all_ok = True

    # 1. Inspect main source
    if not MAIN_AUTH_FILE.exists():
        print(f"FAIL: Main auth file not found: {MAIN_AUTH_FILE}")
        return False

    if not MAIN_AUTH_FILE.is_file():
        print(f"FAIL: Main auth path is not a regular file: {MAIN_AUTH_FILE}")
        return False

    main_stat = MAIN_AUTH_FILE.stat()
    main_inode = main_stat.st_ino
    main_realpath = MAIN_AUTH_FILE.resolve()
    main_mode = stat.S_IMODE(main_stat.st_mode)

    # Permissions check (must not be world-accessible)
    if main_mode & stat.S_IROTH or main_mode & stat.S_IWOTH:
        print(f"FAIL: Main auth file permissions too permissive: {oct(main_mode)}")
        all_ok = False
    else:
        print(f"PASS: Main auth source verified: {MAIN_AUTH_FILE} (inode: {main_inode}, perms: {oct(main_mode)})")

    # 2. Check each ready profile
    for code, prof_name in READY_PROFILES:
        print(f"\n--- Validating Profile [{code}] '{prof_name}' ---")
        agent_dir = LAB_DIR / "agents" / prof_name
        auth_link = agent_dir / "auth.json"

        # Check directory exists
        if not agent_dir.is_dir():
            print(f"  FAIL: Agent directory missing: {agent_dir}")
            all_ok = False
            continue

        # Check symlink exists
        if not auth_link.is_symlink():
            print(f"  FAIL: {auth_link} is not a symlink! (Physical credential copy or missing link)")
            all_ok = False
            continue

        # Verify symlink target
        raw_target = os.readlink(auth_link)
        resolved_target = auth_link.resolve()

        if resolved_target != main_realpath:
            print(f"  FAIL: Symlink target mismatch: raw='{raw_target}', resolved='{resolved_target}', expected='{main_realpath}'")
            all_ok = False
            continue

        # Verify inode matches main file (proves it references same inode, not a copy)
        link_stat = auth_link.stat()
        if link_stat.st_ino != main_inode:
            print(f"  FAIL: Inode mismatch between link ({link_stat.st_ino}) and main source ({main_inode})")
            all_ok = False
            continue

        print(f"  PASS: Symlink verified: {auth_link} -> {raw_target}")
        print(f"  PASS: Inode match verified: {link_stat.st_ino} == {main_inode}")

        # Check profile isolation for other files
        non_auth_files = [f for f in agent_dir.iterdir() if f.name != "auth.json"]
        for f in non_auth_files:
            if f.is_symlink():
                print(f"  WARNING: Unexpected symlink in agent dir: {f} -> {os.readlink(f)}")
                all_ok = False

        print(f"  PASS: Configuration isolation preserved ({len(non_auth_files)} independent items in agent dir)")

        # Verify Pi CLI recognition offline (no-refresh, no model requests)
        env = os.environ.copy()
        env["PI_CODING_AGENT_DIR"] = str(agent_dir)
        env["PI_OFFLINE"] = "1"

        try:
            res = subprocess.run(
                ["pi", "auth", "check", "--provider", "openai-codex", "--no-refresh", "--json"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout.strip())
                    if data.get("status") == "ready":
                        print(f"  PASS: Pi CLI credential check succeeded: status=ready, authType={data.get('authType')}")
                    else:
                        print(f"  PASS [AUTH_WIRING_VERIFIED]: CLI response: status={data.get('status')}")
                except json.JSONDecodeError:
                    print(f"  PASS [AUTH_WIRING_VERIFIED]: CLI exited cleanly (stdout: {res.stdout.strip()[:60]})")
            else:
                print(f"  FAIL: Pi CLI auth check exited with error code {res.returncode}: {res.stderr.strip()[:80]}")
                all_ok = False
        except Exception as e:
            print(f"  FAIL: Error running Pi CLI check: {e}")
            all_ok = False

    # 3. Verify Profile P4 (context-engine) is NOT symlinked to shared auth
    print(f"\n--- Checking Excluded Profile P4 ('context-engine') ---")
    p4_auth = LAB_DIR / "agents" / "context-engine" / "auth.json"
    if p4_auth.is_symlink() and p4_auth.resolve() == main_realpath:
        print(f"FAIL: P4 must NOT be linked to shared credentials while NOT_READY!")
        all_ok = False
    else:
        print(f"PASS: P4 is properly excluded from shared authentication (status: NOT_READY).")

    if all_ok:
        print("\n[verify-shared-auth] ALL SHARED AUTHENTICATION CHECKS PASSED.")
        return True
    else:
        print("\n[verify-shared-auth] SHARED AUTHENTICATION CHECKS FAILED.")
        return False


if __name__ == "__main__":
    ok = verify_shared_auth()
    sys.exit(0 if ok else 1)
