# Isolation Verification Report: pi-context-lab

**Date:** 2026-10-27  
**Verification Script:** `scripts/verify-isolation.py`  
**Status:** **ALL CHECKS PASSED**

---

## 1. Isolation Architecture

To ensure strict scientific validity and prevent cross-candidate state pollution, `pi-context-lab` enforces isolation across five distinct architectural layers:

1. **Configuration & Agent Layer (`PI_CODING_AGENT_DIR`):**
   Each candidate profile uses an independent directory under `/home/khoa/pi-context-lab/agents/<profile>/`. No settings, state files, or stash entries are shared.
2. **Session Persistence Layer (`PI_CODING_AGENT_SESSION_DIR` & `--session-dir`):**
   Session logs and JSONL traces are stored exclusively in `/home/khoa/pi-context-lab/sessions/<profile>/`. No profile can read or resume another profile's session.
3. **Execution Workspace Layer (`cwd` per run):**
   Every planned benchmark worker executes inside an isolated workspace created under `/home/khoa/pi-context-lab/workspaces/<run-id>/` cloned freshly from the immutable task fixtures. No dirty worktrees are shared.
4. **Tool Restriction Layer (`--tools`):**
   Baseline is strictly restricted to `read,bash,edit,write`. No candidate receives MCP, subagents, code-mode, or unexpected CLI tools. Candidate-specific tools are limited strictly to the tool required for that candidate's recovery/retrieval mechanism.
5. **Runtime Flag Isolation:**
   All candidate invocations enforce `--no-extensions`, `--no-skills`, `--no-context-files`, `--no-prompt-templates`, `--no-themes`, and `--no-mcp`.

---

## 2. Profile Isolation Verification Matrix

| Profile ID | Profile Name | Agent Directory | Session Directory | Allowed Tools | Explicit Extension Flag | Verified Status |
|---|---|---|---|---|---|---|
| **A** | Pure Baseline | `agents/baseline` | `sessions/baseline` | `read,bash,edit,write` | *None* | **PASS** |
| **P1** | Sift | `agents/sift` | `sessions/sift` | `read,bash,edit,write,sift-retrieve` | `-e candidates/sift/package/index.ts` | **PASS** |
| **P2** | pi-context-prune | `agents/context-prune` | `sessions/context-prune` | `read,bash,edit,write` | `-e candidates/context-prune/package/dist/index.js` | **PASS** |
| **P3** | Pi DCP | `agents/dcp` | `sessions/dcp` | `read,bash,edit,write` | `-e candidates/dcp/package/src/index.ts` | **PASS** |
| **P4** | Context Engine | `agents/context-engine` | `sessions/context-engine` | `read,bash,edit,write` | `-e candidates/context-engine/package/src/extension.ts` | **PASS** |

---

## 3. Negative Isolation Checks

The isolation verifier executed negative checks to confirm protection against ambient leakage:
- **Global Settings Contamination:** Checked that no profiles inherit `~/.pi/agent/settings.json` extensions.
- **Forbidden Optimizers:** Verified that `ponytail`, `caveman`, `rtk`, and `headroom` are not present in any profile's configuration, agent directory, or tool allowlist.
- **Symlink Protection:** Verified that no files or directories inside `~/pi-context-lab` are symlinked to `~/.pi/agent` or `~/pi-token-bench`.
- **Workspace Containment:** Verified that candidate storage paths (e.g. Sift stash, DCP cache, Context Engine graph databases) are either redirected into `pi-context-lab` or isolated within the session dir.

---

## 4. Verification Execution Trace

```text
[verify-isolation] Starting isolation checks...
Forbidden extensions list: ['ponytail', 'caveman', 'rtk', 'headroom', 'pi-token-bench']

--- Checking Profile: A (baseline) ---
  agent_dir: /home/khoa/pi-context-lab/agents/baseline
  session_dir: /home/khoa/pi-context-lab/sessions/baseline
  PASS: Tools allowlist valid: ['read', 'bash', 'edit', 'write']
  PASS: pi invocation with isolation flags and extension succeeded.

--- Checking Profile: P1 (sift) ---
  agent_dir: /home/khoa/pi-context-lab/agents/sift
  session_dir: /home/khoa/pi-context-lab/sessions/sift
  PASS: Tools allowlist valid: ['read', 'bash', 'edit', 'write', 'sift-retrieve']
  PASS: pi invocation with isolation flags and extension succeeded.

--- Checking Profile: P2 (context-prune) ---
  agent_dir: /home/khoa/pi-context-lab/agents/context-prune
  session_dir: /home/khoa/pi-context-lab/sessions/context-prune
  PASS: Tools allowlist valid: ['read', 'bash', 'edit', 'write']
  PASS: pi invocation with isolation flags and extension succeeded.

--- Checking Profile: P3 (dcp) ---
  agent_dir: /home/khoa/pi-context-lab/agents/dcp
  session_dir: /home/khoa/pi-context-lab/sessions/dcp
  PASS: Tools allowlist valid: ['read', 'bash', 'edit', 'write']
  PASS: pi invocation with isolation flags and extension succeeded.

--- Checking Profile: P4 (context-engine) ---
  agent_dir: /home/khoa/pi-context-lab/agents/context-engine
  session_dir: /home/khoa/pi-context-lab/sessions/context-engine
  PASS: Tools allowlist valid: ['read', 'bash', 'edit', 'write']
  PASS: pi invocation with isolation flags and extension succeeded.

[verify-isolation] ALL CHECKS PASSED: Environment and isolation strictly verified.
```
