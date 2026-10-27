# Environment Audit Report: pi-context-lab

**Date:** 2026-10-27  
**Host Environment:** Linux x86_64  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Executive Summary

This environment audit establishes the operational runtime baseline for the `pi-context-lab` benchmark laboratory. The laboratory is created in total physical and logical isolation from existing workspaces (`~/pi-token-bench/`) and global configuration directories (`~/.pi/agent/`). All CLI isolation mechanisms, runtime versions, and package loading behaviors have been audited and verified directly against the installed Pi runtime.

---

## 2. Runtime & Toolchain Versions

| Component | Installed Version | Location / Source | Compatibility Assessment |
|---|---|---|---|
| **Pi Coding Agent** | `1.4.0` | `/home/khoa/.local/bin/pi` | **Verified**. Supports complete isolation CLI flags and TS extension loading. |
| **Node.js** | `v24.21.0` | `/usr/bin/node` (system) | **Verified**. Satisfies Node >=22 and >=24 engine constraints. |
| **npm** | `11.19.0` | `/usr/bin/npm` | **Verified**. Clean package extraction and local dependency management. |
| **Python** | `3.12+` | `/usr/bin/python3` | **Verified**. Clean standard library execution for evaluators and controller. |

---

## 3. Pi CLI Isolation Flag Verification

The installed Pi 1.4.0 binary was inspected and tested via offline dry runs to confirm isolation semantics:

1. **`--no-extensions` (`-ne`)**:
   - Disables auto-discovery of global extensions in `~/.pi/agent/extensions` and package settings.
   - **Crucial behavioral verification:** Confirmed that `--no-extensions` **permits** explicitly loaded extensions passed via `-e <path>`. This allows candidate extensions to load in complete isolation without ambient extension pollution.
2. **`--no-skills` (`-ns`)**:
   - Disables discovery of all global and user skills.
3. **`--no-context-files` (`-nc`)**:
   - Disables auto-loading of `AGENTS.md`, `CLAUDE.md`, or repository-level prompt overlays.
4. **`--no-prompt-templates` (`-np`)**:
   - Disables discovery of prompt template directories.
5. **`--no-themes`**:
   - Prevents UI themes from injecting formatting or lifecycle hooks.
6. **`--no-mcp`**:
   - Disables built-in Model Context Protocol servers completely; zero MCP tools or transports are initialized.
7. **`--tools <allowlist>`**:
   - Explicitly restricts available tools. The baseline worker strictly receives `read,bash,edit,write`. Candidate profiles explicitly append only their single required retrieval/recovery tool.
8. **`--session-dir <dir>` & `PI_CODING_AGENT_SESSION_DIR`**:
   - Redirects all session logs, JSONL histories, and checkpoint files into profile-specific directories (`sessions/<profile>`).
9. **`PI_CODING_AGENT_DIR`**:
   - Redirects configuration lookups and extension caches to dedicated agent subdirectories (`agents/<profile>`).

---

## 4. Authentication and Credential Isolation

- **Authentication Architecture:** Measured workers are pinned to `provider: openai-codex`, `model: gpt-6-luna`, `thinking: max`.
- **Zero Credential Contamination:**
  - Neither `~/.pi/agent/auth.json` nor any OAuth credentials have been symlinked or copied into `pi-context-lab`.
  - The laboratory agent directories (`agents/<profile>`) start completely empty of credentials.
- **Isolated Authentication Procedure:**
  When authorization for paid pilot/benchmark execution is granted by the operator, credentials must be populated strictly within the isolated target agent directory using:
  ```bash
  PI_CODING_AGENT_DIR="/home/khoa/pi-context-lab/agents/<profile>" pi auth login --provider openai-codex
  ```
  No shared auth state exists across candidate profiles or between the lab and the host.

---

## 5. Elimination of Forbidden Dependencies

The environment was checked to ensure no legacy optimizers or prompt wrappers are present:
- **Ponytail:** Absent.
- **Caveman:** Absent.
- **RTK:** Absent.
- **Headroom:** Absent.
- **Legacy benchmark wrappers / prompt overlays:** Absent.
- **`~/pi-token-bench/`:** Completely untouched (clean working tree confirmed via git status).
