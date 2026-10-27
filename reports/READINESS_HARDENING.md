# Environment Readiness Hardening Report: pi-context-lab

**Date:** 2026-10-27  
**Scope:** P1 Fix, P2 & P3 Validation, P4 Deep-Dive Diagnosis, Telemetry Hardening  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Executive Summary

This hardening phase progressed candidate readiness from preliminary preflight to rigorous, offline-verified runtime states. No global npm packages were modified, no global Pi configuration was altered, and zero commercial API calls were executed.

All four planned pilot profiles (**A**, **P1**, **P2**, **P3**) are now **100% READY** and functionally verified in offline testing. Profile **P4** remains strictly **NOT_READY** due to native build constraints and local embedding requirements.

---

## 2. Updated Candidate Readiness Classification

| Code | Profile Name | Candidate Version | Previous State | Hardened State | Key Functional Verification |
|---|---|---|:---:|:---:|---|
| **A** | **Pure Baseline** | *Built-in* | READY | **READY** | Pi 1.4.0 isolated flags verified; strict 4-tool boundary (`read,bash,edit,write`). |
| **P1** | **Sift** | `@agent-context/pi-sift@0.0.2` | READY_WITH_LIMITATIONS | **READY** | Installed `@agent-context/sift@0.0.1` locally; verified `sift_retrieve`, stash storage outside worktree, and full lossy compression + lossless retrieval round-trip (783 tokens saved, 3420 bytes restored). |
| **P2** | **pi-context-prune** | `pi-context-prune@2.1.0` | READY | **READY** | Initialized isolated configuration at `$PI_CODING_AGENT_DIR/context-prune/settings.json` with `enabled: true`, `pruneOn: "every-turn"`, and secondary model telemetry extraction from `context-prune-stats`. |
| **P3** | **Pi DCP** | `@pi-vault/pi-dcp@0.11.0` | READY | **READY** | Verified offline on Node 24 (`v24.21.0`). Validated deterministic deduplication: pruned duplicate tool results with 600 tokens saved without secondary model calls. |
| **P4** | **Context Engine** | `pi-context-engine@0.7.1` | NOT_READY | **NOT_READY** | Audited native addon `better-sqlite3` on Node 24 ABI 137, ONNX local embedding model requirements (~90MB), and outbound pricing web scraper. Blocked from live runs. |

---

## 3. Detailed Actions Taken

### 3.1 P1 Sift Fix & Functional Verification
1. **Dependency Audit:** Inspected lifecycle scripts of `@agent-context/sift@0.0.1` and platform package `@agent-context/sift-linux-x64-gnu@0.0.1`. Confirmed zero malicious or build-time install scripts.
2. **Local Installation:** Installed `@agent-context/sift@0.0.1` and `typebox@1.3.7` strictly inside `candidates/sift/package/node_modules` (`--no-package-lock`, `--ignore-scripts`). Zero global packages modified.
3. **Round-Trip Test:** Executed a functional verification script compressing a 3,420-byte test log. Sift generated a 24-character stash key (`dc880a8327b8389a3645c0c0`), stored the raw output in `$PI_CODING_AGENT_DIR/sift/sift-stash`, and `sift_retrieve` recovered 100% of the original content without distortion.
4. **Tool Schema Sync:** Updated `config/profiles.json` to register the canonical tool name `sift_retrieve`.

### 3.2 P2 Context Prune Activation & Telemetry Integration
1. **Configuration Persistence:** Discovered that `pi-context-prune` reads its settings from `$PI_CODING_AGENT_DIR/context-prune/settings.json`, and defaults to `enabled: false`. Without an explicit settings file, pruning would never activate.
2. **Isolated Configuration Created:** Created `/home/khoa/pi-context-lab/agents/context-prune/context-prune/settings.json` configuring `enabled: true`, `pruneOn: "every-turn"`, `summarizerModel: "default"`, and `summarizerThinking: "low"`.
3. **Secondary Model Accounting:** Traced source code to confirm that `pi-context-prune` records summarizer token usage in session custom entries with `customType: "context-prune-stats"`. Integrated these entries into `runner/telemetry.py` to guarantee secondary model costs are factored into net end-to-end pricing.

### 3.3 P3 DCP Verification
1. **Engine Validation:** Tested compatibility with Node `v24.21.0`. Installed local `typebox` dev-peer dependency inside `candidates/dcp/package`.
2. **Pipeline Test:** Fed duplicate tool results (`pytest` execution) through `runPipeline()`. DCP's deduplication strategy automatically stripped superseded output, inserted an explanation notice, preserved the most recent execution, and yielded 600 saved tokens with zero secondary model API cost.

### 3.4 P4 Context Engine Deep Diagnosis
1. Kept strictly excluded from live runs.
2. Compiled complete remediation prerequisites: requires pre-compiling `better-sqlite3` on Node 24, pre-fetching local ONNX weights to `PCE_TRANSFORMERS_CACHE`, and disabling the 5-second pricing scrape against Anthropic docs.
