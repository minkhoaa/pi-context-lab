# Shared Authentication Setup & Security Report: pi-context-lab

**Date:** 2026-10-27  
**Status:** **AUTH_WIRING_VERIFIED & READY**  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Executive Summary

In accordance with operator instructions, `pi-context-lab` has been configured to reuse the main Pi installation's OpenAI Codex OAuth authentication. No new credentials were created, no separate logins were performed for benchmark profiles, and zero credential secrets, OAuth tokens, or API keys were printed or leaked.

Authentication sharing was established via strict filesystem symbolic links from the four ready profile agent directories to the single authoritative authentication source at `~/.pi/agent/auth.json`. All other configuration layers (extensions, settings, sessions, workspaces, caches, stashes, and telemetry) remain 100% physically and logically isolated.

---

## 2. Authentication Architecture & Symbolic Links

### 2.1 Authoritative Source
- **Canonical Path:** `/home/khoa/.pi/agent/auth.json`
- **File Inode:** `8844971`
- **Permissions:** `0600` (`-rw-------`, user read/write only; zero group or world access)
- **Integrity:** Untouched during setup; zero in-place edits made.

### 2.2 Symbolic Link Mapping

```text
/home/khoa/.pi/agent/auth.json (inode: 8844971, mode: 0600)
    │
    ├── /home/khoa/pi-context-lab/agents/baseline/auth.json       [inode: 8844971]
    ├── /home/khoa/pi-context-lab/agents/sift/auth.json           [inode: 8844971]
    ├── /home/khoa/pi-context-lab/agents/context-prune/auth.json   [inode: 8844971]
    └── /home/khoa/pi-context-lab/agents/dcp/auth.json             [inode: 8844971]
```

Profile **P4 (`context-engine`)** is explicitly **EXCLUDED** from shared authentication wiring because it remains in `NOT_READY` status pending native C++ addon resolution and local embedding model staging.

---

## 3. Idempotent Setup Script (`scripts/setup-shared-auth.sh`)

The setup is managed by an automated, idempotent shell script that enforces strict safety constraints:
1. Validates that the source path `/home/khoa/.pi/agent/auth.json` exists, is a regular file, and resolves to the expected canonical realpath.
2. Checks that file permissions on the source are not overly permissive.
3. Checks existing target paths:
   - If a valid symlink already points to `auth.json`, it is reused without disturbance.
   - If an unexpected file or broken symlink exists, it safely halts with a `CONFLICT` error without reading or printing file contents.
4. Creates atomic absolute symbolic links only for the authorized profiles (`baseline`, `sift`, `context-prune`, `dcp`).

---

## 4. Verification & Pi CLI Offline Check

Automated audit via `scripts/verify-shared-auth.py` and `pi auth check --provider openai-codex --no-refresh --json` produced:

```text
[verify-shared-auth] Beginning shared authentication audit...
PASS: Main auth source verified: /home/khoa/.pi/agent/auth.json (inode: 8844971, perms: 0o600)

--- Validating Profile [A] 'baseline' ---
  PASS: Symlink verified: /home/khoa/pi-context-lab/agents/baseline/auth.json -> /home/khoa/.pi/agent/auth.json
  PASS: Inode match verified: 8844971 == 8844971
  PASS: Configuration isolation preserved (1 independent items in agent dir)
  PASS: Pi CLI credential check succeeded: status=ready, authType=oauth

--- Validating Profile [P1] 'sift' ---
  PASS: Symlink verified: /home/khoa/pi-context-lab/agents/sift/auth.json -> /home/khoa/.pi/agent/auth.json
  PASS: Inode match verified: 8844971 == 8844971
  PASS: Configuration isolation preserved (2 independent items in agent dir)
  PASS: Pi CLI credential check succeeded: status=ready, authType=oauth

--- Validating Profile [P2] 'context-prune' ---
  PASS: Symlink verified: /home/khoa/pi-context-lab/agents/context-prune/auth.json -> /home/khoa/.pi/agent/auth.json
  PASS: Inode match verified: 8844971 == 8844971
  PASS: Configuration isolation preserved (2 independent items in agent dir)
  PASS: Pi CLI credential check succeeded: status=ready, authType=oauth

--- Validating Profile [P3] 'dcp' ---
  PASS: Symlink verified: /home/khoa/pi-context-lab/agents/dcp/auth.json -> /home/khoa/.pi/agent/auth.json
  PASS: Inode match verified: 8844971 == 8844971
  PASS: Configuration isolation preserved (1 independent items in agent dir)
  PASS: Pi CLI credential check succeeded: status=ready, authType=oauth

--- Checking Excluded Profile P4 ('context-engine') ---
PASS: P4 is properly excluded from shared authentication (status: NOT_READY).

[verify-shared-auth] ALL SHARED AUTHENTICATION CHECKS PASSED.
```

---

## 5. Security & Trust Model

1. **Extension Trust Boundary:**
   Sharing `auth.json` grants candidate extensions access to the OAuth bearer token when executed under the user's UID. All three enabled candidate packages (`@agent-context/pi-sift`, `pi-context-prune`, `@pi-vault/pi-dcp`) were thoroughly audited:
   - Sift: Local stash storage only; no outbound network calls.
   - Context Prune: Native `ctx.model` streaming only; no third-party telemetry.
   - DCP: Rule-based in-memory and JSONL compaction; no external calls.
   - Zero candidates intercept, export, or log OAuth credentials.
2. **OAuth Token Refresh Dynamics:**
   When Pi refreshes an expiring OAuth token, it writes to `auth.json` in the resolved agent directory. Because the symlinks resolve directly to `/home/khoa/.pi/agent/auth.json`, token refreshes update the main credential file in place, keeping all profile sessions seamlessly authenticated without credential desynchronization.
3. **Repository Cleanliness:**
   `~/.gitignore` has been updated to explicitly ignore `**/auth.json` and `**/models-store.json`, preventing accidental git tracking of authentication symlinks or secrets.
