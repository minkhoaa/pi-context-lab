# Comprehensive Audit & Static Analysis: Pi Context Management Candidates

This document provides a comprehensive audit and static analysis of the 4 candidate context management packages unpacked in `/home/khoa/pi-context-lab/candidates`:

1. `@agent-context/pi-sift` (0.0.2)
2. `pi-context-prune` (2.1.0)
3. `@pi-vault/pi-dcp` (0.11.0)
4. `pi-context-engine` (0.7.1)

---

## 1. Executive Summary & Readiness Matrix

| Package | Version | License | Status | Runtime Deps | Node 24 & Pi 1.4 Compat | Network Activity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`@agent-context/pi-sift`** | 0.0.2 | Apache-2.0 | **NOT_READY** | 1 (`@agent-context/sift`) | Missing unbundled dependency | None (pure local) |
| **`pi-context-prune`** | 2.1.0 | MIT | **READY** | 0 (bundled ESM) | Fully compatible | LLM calls via Pi API |
| **`@pi-vault/pi-dcp`** | 0.11.0 | MIT | **READY** | 0 (TypeScript source) | Fully compatible (`>=24.15.0`) | None (pure local) |
| **`pi-context-engine`** | 0.7.1 | MIT | **NOT_READY** | 5 + 1 opt (native/wasm) | Uninstalled native addons | HF model downloads, live pricing HTTP, Ollama |

---

## 2. Package-by-Package Deep Dive

### Candidate 1: `@agent-context/pi-sift` (v0.0.2)

- **Entry Point & Structure**:
  - Entry point: `index.ts` (configured under `"pi": { "extensions": ["./index.ts"] }`).
  - Written in TypeScript; relies on Pi's native TS extension loader.
  - Files included: `index.ts`, `hooks/tool-result.ts`, `lib/*`, `tools/sift-retrieve.ts`.
- **Dependencies**:
  - `dependencies`: `@agent-context/sift: 0.0.1` (NOT bundled; uninstalled in candidate directory).
  - `peerDependencies`: `@earendil-works/pi-ai`, `@earendil-works/pi-coding-agent`, `typebox`.
  - `devDependencies`: `@earendil-works/pi-coding-agent: 0.84.4`, `@types/node`, `typebox: 1.3.7`.
- **Lifecycle Scripts**:
  - None (`preinstall`, `postinstall`, etc. are absent).
- **Runtime Compatibility**:
  - **Status**: **NOT_READY** until `npm install` is executed.
  - `@agent-context/sift` publishes prebuilt N-API binaries for `linux-x64-gnu`.
  - Node v24.21.0 compatibility will be satisfied via N-API once installed.
- **Filesystem Writes & Storage Paths**:
  - Root: `$PI_CODING_AGENT_DIR/sift` (defaults to `~/.pi/agent/sift/<encoded-session-id>`).
  - **Worktree Isolation**: Has an explicit security check (`assertOutsideWorktree`) prohibiting stash directories from being inside the active git worktree.
  - **Redirection**: Set `PI_CODING_AGENT_DIR=/home/khoa/pi-context-lab/.pi-agent` to keep writes inside the lab.
- **Network Calls**:
  - None. Stashing and compression are performed locally by the Rust/C library bindings.
- **Registered Tools & Hooks**:
  - Tools registered:
    - `sift_retrieve`: Retrieves raw uncompressed tool output by stash key or marker (`<<stash:KEY>>`).
  - Injected flags: `--sift`, `--no-sift`, `--sift-min-length`, `--sift-exclude`.
  - System prompt modifications: None.
  - Extension hooks: `tool_result` (replaces large outputs with compressed text + stash key), `session_shutdown`, `session_start`.

---

### Candidate 2: `pi-context-prune` (v2.1.0)

- **Entry Point & Structure**:
  - Entry point: `dist/index.js` (`main`, `exports`, and `"pi.extensions"`).
  - Bundled standalone ESM via esbuild (includes source map).
- **Dependencies**:
  - `dependencies`: None (zero runtime dependencies).
  - `peerDependencies`: `@earendil-works/pi-ai: *`, `@earendil-works/pi-coding-agent: >=0.86.0`, `@earendil-works/pi-tui: *`.
- **Lifecycle Scripts**:
  - `prepack`: `npm run build && npm run check:package`. No install lifecycle scripts.
- **Runtime Compatibility**:
  - **Status**: **READY**.
  - Built targeting Node 20+; runs cleanly on Node v24.21.0 and Pi 1.4.0 without any installation step.
- **Filesystem Writes & Storage Paths**:
  - Configuration: `$PI_CODING_AGENT_DIR/context-prune/settings.json` (defaults to `~/.pi/agent/context-prune/settings.json`).
  - Active session index: Maintained entirely in-memory during agent execution.
  - **Redirection**: Set `PI_CODING_AGENT_DIR=/home/khoa/pi-context-lab/.pi-agent`.
- **Network Calls**:
  - Does NOT initiate direct HTTP/sockets or telemetry calls.
  - Makes LLM summarization calls using Pi's model provider API (`provider.stream(...)` using the active session model or configured `summarizerModel`).
- **Registered Tools & System Prompt Injections**:
  - Tools registered:
    - `context_prune`: Summarizes and prunes preceding batches of tool calls.
    - `context_tree_query`: Recovers original tool outputs from the session index using short reference IDs.
  - Commands registered: `/pruner` (subcommands: `model`, `thinking`, `stats`, `prune-on`, `now`, etc.).
  - System prompt injection:
    - Hook: `before_agent_start`.
    - Injects `[Context Prune — Agentic Auto Mode]` guidelines when `pruneOn === "agentic-auto"`.

---

### Candidate 3: `@pi-vault/pi-dcp` (v0.11.0)

- **Entry Point & Structure**:
  - Entry point: `src/index.ts` (configured under `"pi": { "extensions": ["./src/index.ts"] }`).
  - Full TypeScript implementation loaded seamlessly by Pi.
- **Dependencies**:
  - `dependencies`: None (zero runtime dependencies).
  - `engines`: `"node": ">=24.15.0"` (Current Node is `v24.21.0` - satisfied).
  - `peerDependencies`: `@earendil-works/pi-agent-core: *`, `@earendil-works/pi-coding-agent: *`, `@earendil-works/pi-tui: *`, `typebox: *`.
- **Lifecycle Scripts**:
  - None.
- **Runtime Compatibility**:
  - **Status**: **READY**.
  - Directly compatible with Node v24.21.0 and Pi 1.4.0.
- **Filesystem Writes & Storage Paths**:
  - Global config: `$PI_CODING_AGENT_DIR/extensions/dcp.json` (default: `~/.pi/agent/extensions/dcp.json`).
  - Prompts directory: `$PI_CODING_AGENT_DIR/extensions/dcp-prompts/` (writes default templates to `defaults/` if not present).
  - Project config: `<cwd>/.pi/dcp.json` and `<cwd>/.pi/dcp-prompts/overrides`.
  - Session logs: `<sessionDir>/dcp/logs/<date>.log`.
  - Session state checkpoints: Saved into Pi session JSONL streams (`entry.customType === "pi-dcp-state"`).
  - **Redirection**: Set `PI_CODING_AGENT_DIR=/home/khoa/pi-context-lab/.pi-agent` to redirect global configurations and defaults.
- **Network Calls**:
  - None. Pure local deterministic pruning, deduplication, error purge, and token trimming.
- **Registered Tools & System Prompt Injections**:
  - Tools registered:
    - `compress`: Compresses conversation messages or ranges into technical summaries (`executionMode: sequential`, `defaultActive: false`).
  - Commands registered:
    - `/dcp`, `/dcp:compress`, `/dcp:help`, `/dcp:context`, `/dcp:stats`, `/dcp:sweep`, `/dcp:manual`, `/dcp:decompress`, `/dcp:recompress`, `/dcp:lifetime`, `/dcp:permission`.
  - System prompt injections:
    - Injects `sections.dcp` via `before_agent_start` when compression is enabled and the `compress` tool is active.

---

### Candidate 4: `pi-context-engine` (v0.7.1)

- **Entry Point & Structure**:
  - Entry point: `src/extension.ts` (configured under `"pi": { "extensions": ["./src/extension.ts"] }`).
- **Dependencies**:
  - `dependencies`:
    - `better-sqlite3: ^13.0.3` (Native C++ Node addon)
    - `sqlite-vec: ^0.1.9` (SQLite C extension)
    - `web-tree-sitter: ^0.22.6` (WASM bindings)
    - `tree-sitter-wasms: ^0.1.13` (Precompiled WASM grammars)
    - `yaml: ^2.9.1`
  - `optionalDependencies`:
    - `@huggingface/transformers: ^4.3.1` (Local embeddings via ONNX)
  - `peerDependencies`: `@earendil-works/pi-ai`, `@earendil-works/pi-coding-agent`, `typebox`.
- **Lifecycle Scripts**:
  - `"prepublishOnly"`: Blocks manual npm publishing.
  - `"allowScripts": { "better-sqlite3": true }`.
- **Runtime Compatibility**:
  - **Status**: **NOT_READY** (Uninstalled dependencies).
  - `better-sqlite3@13.0.3` must be compiled against Node 24 (NODE_MODULE_VERSION 137) via `node-gyp`.
  - `sqlite-vec@0.1.9` provides prebuilt binary extensions (`sqlite-vec-linux-x64`).
  - Requires `@huggingface/transformers` or an active Ollama instance for vector embeddings.
- **Filesystem Writes & Storage Paths**:
  - Global config: `~/.pi-context-engine/config.yaml`.
  - Pricing cache: `~/.pi-context-engine/pricing_cache.json`.
  - Model weights: `~/.pi-context-engine/models/` (overridable via `PCE_TRANSFORMERS_CACHE` or `TRANSFORMERS_CACHE`).
  - Per-project storage: `~/.pi-context-engine/projects/<project-slug>/` (contains `manifest.json`, `graph.db`, `embedding_cache.db`, `fts/`, `vectors/`, `sessions/`).
  - Project config: `<cwd>/.context-engine.yaml`.
  - **Redirection**:
    - Set `storage.path: /home/khoa/pi-context-lab/storage` in configuration.
    - Set `PCE_TRANSFORMERS_CACHE=/home/khoa/pi-context-lab/models`.
- **Network Calls**:
  - **Live Pricing**: Queries `https://docs.anthropic.com/en/docs/about-claude/models` on startup to update pricing table.
  - **Model Download**: Downloads ONNX models (~80 MB) from Hugging Face Hub if local backend is selected.
  - **Ollama API**: Makes HTTP calls to `http://localhost:11434` if Ollama backend is configured.
  - **Local Dashboard Server**: Creates an HTTP server on `127.0.0.1:<random-port>` when `/context-dashboard` is executed.
- **Registered Tools & System Prompt Injections**:
  - Tools registered:
    - `context_search`: Semantic search over tree-sitter chunks (vector + BM25).
    - `expand_chunk`: Fetch uncompressed code for a snippet.
    - `related_context`: Query code knowledge graph edges.
    - `session_recall`: Cross-session memory search.
    - `session_timeline`: Drill into past session turns.
    - `session_event`: Inspect raw tool event payloads.
    - `record_decision`: Save architectural decisions across sessions.
    - `record_code_area`: Save notes on modified code areas.
    - `index_status`: Report index health and token savings.
    - `reindex`: Trigger incremental or full reindexing.
  - Commands registered:
    - `/context-index`, `/context-status`, `/context-savings`, `/context-warmup`, `/context-dashboard`.
  - System prompt injection:
    - Injects `sections.context_search_guidelines` (~900 tokens) via `before_agent_start`.

---

## 3. Comparison & Strategic Takeaways

1. **Immediate Out-of-the-Box Evaluability**:
   - `pi-context-prune` (2.1.0) and `@pi-vault/pi-dcp` (0.11.0) are ready for immediate evaluation. Neither requires `npm install` or native builds.
   - `@agent-context/pi-sift` requires installing `@agent-context/sift@0.0.1`.
   - `pi-context-engine` requires a heavy setup step (`npm install` with native compilation of `better-sqlite3`, downloading ONNX models or configuring Ollama).

2. **Network & Privacy Footprint**:
   - `@pi-vault/pi-dcp` and `@agent-context/pi-sift` operate strictly offline and make zero external network requests.
   - `pi-context-prune` leverages the agent's configured LLM provider for summarization.
   - `pi-context-engine` contacts external endpoints (Anthropic docs and Hugging Face model repository).

3. **Storage Isolation**:
   - All 4 packages can be redirected into `/home/khoa/pi-context-lab/` by setting:
     ```bash
     export PI_CODING_AGENT_DIR="/home/khoa/pi-context-lab/.pi-agent"
     export PCE_TRANSFORMERS_CACHE="/home/khoa/pi-context-lab/models"
     ```
     and specifying `storage.path: /home/khoa/pi-context-lab/storage` in `.context-engine.yaml`.
