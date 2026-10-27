# pi-context-lab: Pi Context Optimization Benchmark Laboratory

A strictly isolated, reproducible benchmark laboratory designed to evaluate modern Pi context and token optimization extensions.

---

## 1. Laboratory Directory Layout

```text
~/pi-context-lab/
├── README.md                          # Laboratory manual and execution guide
├── .gitignore                         # Workspace, session, and credential exclusion rules
├── config/
│   ├── profiles.json                  # Profile definitions (A, P1, P2, P3, P4)
│   ├── environment-lock.json          # Locked Pi and Node.js runtime versions
│   └── model-lock.json                # Pinned model (openai-codex/gpt-6-luna:max) & pricing
├── agents/                            # Isolated PI_CODING_AGENT_DIR per profile
│   ├── baseline/                      # auth.json -> ~/.pi/agent/auth.json
│   ├── sift/                          # auth.json -> ~/.pi/agent/auth.json + local stash
│   ├── context-prune/                 # auth.json -> ~/.pi/agent/auth.json + settings.json
│   ├── dcp/                           # auth.json -> ~/.pi/agent/auth.json
│   └── context-engine/                # Isolated (unlinked, P4 excluded)
├── candidates/                        # Pinned local candidate packages & audit files
│   ├── CANDIDATE_AUDIT.json
│   ├── AUDIT_SUMMARY.md
│   ├── sift/package/
│   ├── context-prune/package/
│   ├── dcp/package/
│   └── context-engine/package/
├── fixtures/                          # Immutable test task repositories
│   ├── manifest.json                  # SHA-256 digests of all 20 fixture files
│   ├── task-s/                        # Task S: mini_validator (short coding fix)
│   ├── task-l/                        # Task L: pipeline_engine (long multi-turn log pressure)
│   └── task-m/                        # Task M: micro_mesh (monorepo cross-service navigation)
├── evaluators/                        # Out-of-process, independent test evaluators
│   ├── eval_task_s.py
│   ├── eval_task_l.py
│   └── eval_task_m.py
├── prompts/                           # Canonical task prompts (identical across profiles)
│   ├── task-s.md
│   ├── task-l-turn1.md ... turn4.md   # Multi-turn sequence for Task L
│   └── task-m.md
├── scripts/                           # Preflight, verification, and controller scripts
│   ├── setup-shared-auth.sh           # Safe, idempotent shared authentication symlink setup
│   ├── verify-shared-auth.py          # Shared authentication integrity & Pi CLI validator
│   ├── preflight.sh                   # Main 5-stage verification test suite runner
│   ├── verify-isolation.py            # Layered isolation verifier
│   ├── verify-profiles.py             # Profile configuration verifier
│   ├── verify-fixtures.py             # Fixture hash and evaluator verifier
│   ├── smoke-local.py                 # Telemetry collector synthetic unit test
│   └── benchmark.py                   # Central CLI benchmark controller
├── runner/                            # Telemetry collector module
│   └── telemetry.py
├── sessions/                          # Dedicated session directories per profile
├── workspaces/                        # Ephemeral execution working directories for workers
├── results/                           # Benchmark JSONL and telemetry artifacts
│   ├── preflight/
│   ├── smoke/
│   └── experiments/
└── reports/                           # Complete audit and protocol reports
    ├── ENVIRONMENT_AUDIT.md
    ├── ISOLATION_VERIFICATION.md
    ├── CANDIDATE_PROVENANCE.md
    ├── DEPENDENCY_COMPATIBILITY.md
    ├── PROFILE_READINESS.md
    ├── FIXTURE_VALIDATION.md
    ├── BENCHMARK_PROTOCOL.md
    ├── PREFLIGHT_REPORT.md
    ├── READINESS_HARDENING.md
    ├── CANDIDATE_RUNTIME_VALIDATION.md
    ├── TELEMETRY_AUDIT.md
    ├── PILOT_EXECUTION_PLAN.md
    ├── SHARED_AUTH_SETUP.md
    └── PILOT_READY.md
```

---

## 2. Candidate Profiles & Readiness Status

| Code | Profile Name | Tool Package | Status | Allowed Tools | Shared Auth Wiring | Optimization Mechanism |
|---|---|---|:---:|---|:---:|---|
| **A** | **Pure Baseline** | *None (Built-in)* | **READY** | `read,bash,edit,write` | Verified Symlink | None (Standard Reference) |
| **P1** | **Sift** | `@agent-context/pi-sift@0.0.2` | **READY** | `read,bash,edit,write,sift_retrieve` | Verified Symlink | Local Stash Compression (`minLength: 200`) |
| **P2** | **Context Prune** | `pi-context-prune@2.1.0` | **READY** | `read,bash,edit,write,context_tree_query,context_prune` | Verified Symlink | Cache-Conscious Batch Pruning (`agent-message`) |
| **P3** | **Pi DCP** | `@pi-vault/pi-dcp@0.11.0` | **READY** | `read,bash,edit,write,compress` | Verified Symlink | Deterministic Deduplication & Error Purging |
| **P4** | **Context Engine** | `pi-context-engine@0.7.1` | **NOT_READY** | *Excluded* | *Excluded* | Blocked by native build & local ONNX weights |

---

## 3. Shared Authentication Architecture

The laboratory reuses the main Pi installation's OpenAI Codex OAuth authentication (`~/.pi/agent/auth.json`) via symbolic links:

- **Setup command:**
  ```bash
  bash scripts/setup-shared-auth.sh
  ```
- **Verification command:**
  ```bash
  python3 scripts/verify-shared-auth.py
  ```
- **Security & Integrity:**
  - Inode matching guarantees zero copies of private tokens exist.
  - Profile configurations, extensions, sessions, and workspaces remain 100% independent.
  - OAuth token refreshes update the main credential file in place, keeping all profile sessions valid.
  - `**/auth.json` is strictly ignored in `.gitignore`.
  - P4 (`context-engine`) is explicitly excluded from shared authentication.

---

## 4. Benchmark Controller CLI

All laboratory verification and benchmark operations run via `scripts/benchmark.py`:

```bash
# 1. Run full 5-stage preflight verification suite
python3 scripts/benchmark.py preflight

# 2. View current candidate profile readiness and matrix status
python3 scripts/benchmark.py status

# 3. Preview 4 planned pilot runs on Task L (dry-run mode)
python3 scripts/benchmark.py dry-run --pilot

# 4. Preview all 45 planned runs across the counterbalanced matrix
python3 scripts/benchmark.py dry-run --full

# 5. Execute controlled pilot run (requires spend authorization)
python3 scripts/benchmark.py run --pilot --authorize-benchmark-spend

# 6. Execute full 45-run counterbalanced matrix (requires spend authorization)
python3 scripts/benchmark.py run --full --authorize-benchmark-spend

# 7. Generate summary reports from experiment results
python3 scripts/benchmark.py report
```

---

## 5. Controlled Pilot Protocol (Task L)

The controlled pilot evaluates candidate context performance under heavy multi-turn log pressure using Task L (`pipeline_engine`):
1. **pilot-01:** Profile A (Baseline) — Reference context expansion.
2. **pilot-02:** Profile P1 (Sift) — Tool output compression and `sift_retrieve` recovery.
3. **pilot-03:** Profile P2 (Context Prune) — Cache-conscious batch summarization (`agent-message`) with secondary token billing.
4. **pilot-04:** Profile P3 (Pi DCP) — Deterministic deduplication of repeated test logs.

Runs execute sequentially under identical hardware, model (`gpt-6-luna`), and thinking (`max`) conditions. Runs where optimizations do not activate are classified as `NON_TRIGGERED`.

---

## 6. Safe Cleanup Instructions

To completely reset run artifacts without deleting core configurations or fixtures:
```bash
rm -rf ~/pi-context-lab/workspaces/run-*
rm -rf ~/pi-context-lab/sessions/*/*
rm -rf ~/pi-context-lab/results/experiments/*
```
To remove the entire laboratory cleanly:
```bash
rm -rf ~/pi-context-lab
```
*(No modifications were made to `~/.pi/agent` or `~/pi-token-bench`).*
