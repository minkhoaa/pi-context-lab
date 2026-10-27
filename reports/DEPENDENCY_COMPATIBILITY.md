# Dependency & Runtime Compatibility Report: pi-context-lab

**Date:** 2026-10-27  
**Host Runtime:** Node.js `v24.21.0` (ABI 137), npm `11.19.0`, Linux x86_64  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Executive Summary

This audit assesses the runtime compatibility of each benchmark candidate against the system's Node.js version (`v24.21.0`) and Pi runtime (`1.4.0`). No global Node.js or npm packages were modified. All dependency installations remain confined strictly within individual candidate directories.

---

## 2. Runtime Compatibility Matrix

| Profile | Candidate Package | Declared Node Engine | Actual Node `v24.21.0` Status | Dependencies Present | Native Addons / WASM | Runtime Assessment |
|---|---|---|---|---|---|---|
| **A** | Pure Baseline | *None* | **Compatible** | None | None | **100% Ready** |
| **P1** | `@agent-context/pi-sift@0.0.2` | *None specified* | **Compatible** | Requires `@agent-context/sift@0.0.1` | Native prebuilds available for linux-x64 | **Ready with local install** |
| **P2** | `pi-context-prune@2.1.0` | `>=22.0.0` | **Compatible** | Zero dependencies (bundled ESM) | None | **100% Ready** |
| **P3** | `@pi-vault/pi-dcp@0.11.0` | `>=24.15.0` | **Compatible** | Zero dependencies | None | **100% Ready** |
| **P4** | `pi-context-engine@0.7.1` | *None specified* | **Incompatible / Blocked** | `better-sqlite3`, `sqlite-vec`, `web-tree-sitter`, `yaml` | `better-sqlite3` (C++ ABI 137), `sqlite-vec` | **Blocked / Incomplete** |

---

## 3. Deep-Dive Per Candidate

### Profile A: Pure Baseline
- Pure built-in tools (`read, bash, edit, write`).
- Requires zero external dependencies, native modules, or Node engine constraints.

### Profile P1: Sift (`@agent-context/pi-sift`)
- **Package Status:** Ships TypeScript source (`index.ts`).
- **External Dependency Requirement:** The package requires `@agent-context/sift` version `0.0.1`.
- **Node 24 Compatibility:** `@agent-context/sift` provides prebuilt binary bindings for Linux x64 that function on Node 24.
- **Action Required for Execution:** Run `npm install --no-save @agent-context/sift@0.0.1` within `/home/khoa/pi-context-lab/candidates/sift/package`.

### Profile P2: Context Prune (`pi-context-prune`)
- **Package Status:** Ships a self-contained bundle at `dist/index.js` compiled with Rollup/esbuild.
- **Dependencies:** Zero runtime npm dependencies.
- **Node 24 Compatibility:** Fully verified on Node v24.21.0 without errors or warnings.
- **Action Required for Execution:** None. Ready immediately.

### Profile P3: Pi DCP (`@pi-vault/pi-dcp`)
- **Package Status:** Ships modular TypeScript code in `src/index.ts`. Pi's TS loader executes it seamlessly.
- **Engine Requirement:** Explicitly declares `"node": ">=24.15.0"`. The host system is running Node `v24.21.0`, satisfying this constraint natively.
- **Dependencies:** Zero external dependencies.
- **Node 24 Compatibility:** Fully verified on Node v24.21.0.
- **Action Required for Execution:** None. Ready immediately.

### Profile P4: Pi Context Engine (`pi-context-engine`)
- **Package Status:** Ships modular TypeScript code in `src/extension.ts`.
- **Dependency Issues:**
  1. `better-sqlite3`: Version `13.0.3` is a native C++ Node addon. Node v24.21.0 uses V8 / Node ABI 137. Prebuilt binaries on npm often target LTS releases (Node 20/22). Compiling on Node 24 requires `node-gyp`, Python, and build headers.
  2. `sqlite-vec`: Provides prebuilt extensions for Linux x64.
  3. `web-tree-sitter`: Requires WebAssembly files from `tree-sitter-wasms`.
  4. Local Embedding Models: The package defaults to loading transformer embedding models (`@huggingface/transformers` with ONNX runtime). Under laboratory isolation rules, remote downloading of models during benchmarking is strictly forbidden.
- **Remediation Needed:**
  - Build/install `better-sqlite3` locally in `candidates/context-engine/package`.
  - Pre-download embedding weights locally to `/home/khoa/pi-context-lab/storage/models` and configure offline model paths.
  - Disable Anthropic pricing HTTP scraping.
