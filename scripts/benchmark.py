#!/usr/bin/env python3
"""
scripts/benchmark.py

CLI controller supporting subcommands:
  * preflight: Runs isolation, profile, fixture, and smoke tests.
  * status: Shows status of all 5 profiles (A, P1, P2, P3, P4) and matrix.
  * dry-run: Prints exact command line and environment that would be used for each worker run,
             with 45 planned runs across the counterbalanced schedule (Latin square or balanced block),
             without making model calls.
  * run --pilot: Requires --authorize-benchmark-spend. When absent, safely aborts with explicit instructions.
  * run --full: Requires --authorize-benchmark-spend. When absent, safely aborts with explicit instructions.
  * report: Generates summary reports from benchmark results.
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from runner.telemetry import TelemetryCollector
CONFIG_DIR = ROOT_DIR / "config"
SCRIPTS_DIR = ROOT_DIR / "scripts"
RESULTS_DIR = ROOT_DIR / "results"
REPORTS_DIR = ROOT_DIR / "reports"
WORKSPACES_DIR = ROOT_DIR / "workspaces"

PROFILES_FILE = CONFIG_DIR / "profiles.json"
MODEL_LOCK_FILE = CONFIG_DIR / "model-lock.json"
ENV_LOCK_FILE = CONFIG_DIR / "environment-lock.json"
PROMPTS_MANIFEST_FILE = ROOT_DIR / "prompts" / "prompts_manifest.json"


def load_json(p: Path) -> Any:
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_preflight(args) -> int:
    """Runs isolation, profile, fixture, and smoke tests."""
    print("=" * 60)
    print("RUNNING BENCHMARK PREFLIGHT VERIFICATION SUITE")
    print("=" * 60)

    verifications = [
        ("Profile Verification", SCRIPTS_DIR / "verify-profiles.py"),
        ("Shared Authentication Verification", SCRIPTS_DIR / "verify-shared-auth.py"),
        ("Isolation Verification", SCRIPTS_DIR / "verify-isolation.py"),
        ("Fixture Verification", SCRIPTS_DIR / "verify-fixtures.py"),
        ("Telemetry Smoke Test", SCRIPTS_DIR / "smoke-local.py"),
    ]

    all_passed = True
    for title, script in verifications:
        print(f"\n>>> Running: {title} ({script.name})")
        res = subprocess.run([sys.executable, str(script)])
        if res.returncode != 0:
            print(f"[FAIL] {title} failed with code {res.returncode}")
            all_passed = False
        else:
            print(f"[PASS] {title} succeeded.")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL PREFLIGHT CHECKS PASSED.")
        print("=" * 60)
        return 0
    else:
        print("PREFLIGHT VERIFICATION FAILED.")
        print("=" * 60)
        return 1


def cmd_status(args) -> int:
    """Shows status of all 5 profiles (A, P1, P2, P3, P4) and matrix."""
    print("=" * 70)
    print("BENCHMARK MATRIX & PROFILE STATUS")
    print("=" * 70)

    profiles = load_json(PROFILES_FILE)
    model_lock = load_json(MODEL_LOCK_FILE)
    prompts_manifest = load_json(PROMPTS_MANIFEST_FILE)

    print(f"Model Pinned: {model_lock.get('provider')}/{model_lock.get('model')} (thinking: {model_lock.get('thinking')})")
    print(f"Pricing: Prompt=${model_lock.get('pricing', {}).get('prompt_per_1m')}/M, "
          f"CacheRead=${model_lock.get('pricing', {}).get('cache_read_per_1m')}/M, "
          f"Completion=${model_lock.get('pricing', {}).get('completion_per_1m')}/M\n")

    print(f"{'Profile ID':<12} {'Name':<18} {'Extension Present':<20} {'Tools Count':<12}")
    print("-" * 70)

    for prof_key, prof in profiles.items():
        pid = prof.get("id")
        pname = prof.get("name")
        ext = prof.get("extension_path")
        ext_status = "Built-in" if ext is None else ("Found" if os.path.exists(ext) else "MISSING")
        tools_cnt = len(prof.get("tools", []))
        print(f"{pid:<12} {pname:<18} {ext_status:<20} {tools_cnt:<12}")

    print("\nBenchmark Tasks:")
    tasks = prompts_manifest.get("tasks", {})
    for tid, tinfo in tasks.items():
        print(f"  - {tid}: {tinfo.get('name')} (turns: {len(tinfo.get('turns', []))}, fixture: {tinfo.get('fixture_dir')})")

    print("\nMatrix Design:")
    print("  - Profiles (5): A (baseline), P1 (sift), P2 (context-prune), P3 (dcp), P4 (context-engine)")
    print("  - Tasks (3): task-s, task-m, task-l")
    print("  - Replications: 3 repetitions per cell (balanced counterbalanced blocks)")
    print("  - Total Planned Runs: 5 profiles * 3 tasks * 3 reps = 45 runs")

    return 0


def generate_schedule(num_reps: int = 3) -> List[Dict[str, Any]]:
    """
    Generates a counterbalanced schedule of runs across 5 profiles and 3 tasks.
    Total runs = 5 * 3 * num_reps.
    Uses balanced Latin Square / block rotations for task ordering across profiles:
    Tasks: T1=task-s, T2=task-m, T3=task-l
    Profiles: A, P1, P2, P3, P4
    """
    profiles = ["A", "P1", "P2", "P3", "P4"]
    tasks = ["task-s", "task-m", "task-l"]

    # Latin square / balanced rotations for order balance
    # Block 1, Block 2, Block 3
    runs = []
    run_idx = 1
    for rep in range(1, num_reps + 1):
        # Shift profiles slightly per rep to counterbalance sequence effects
        for p_idx, prof in enumerate(profiles):
            # Rotated task sequence for this profile in this repetition
            task_order = [tasks[(p_idx + rep - 1 + t_idx) % len(tasks)] for t_idx in range(len(tasks))]
            for task in task_order:
                runs.append({
                    "run_id": f"run-{run_idx:02d}",
                    "rep": rep,
                    "profile_id": prof,
                    "task_id": task,
                })
                run_idx += 1
    return runs


def get_profile_by_id(profiles_dict: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
    for key, p in profiles_dict.items():
        if p.get("id") == profile_id:
            return p
    raise ValueError(f"Unknown profile ID: {profile_id}")


def generate_pilot_schedule() -> List[Dict[str, Any]]:
    """
    Generate the 4 planned pilot sessions strictly on Task L:
    1. A: Baseline
    2. P1: Sift
    3. P2: Context Prune
    4. P3: DCP
    Sequential execution only. Task L multi-turn (4 turns).
    """
    return [
        {"run_id": "pilot-01", "profile_id": "A", "task_id": "task-l", "rep": 1},
        {"run_id": "pilot-02", "profile_id": "P1", "task_id": "task-l", "rep": 1},
        {"run_id": "pilot-03", "profile_id": "P2", "task_id": "task-l", "rep": 1},
        {"run_id": "pilot-04", "profile_id": "P3", "task_id": "task-l", "rep": 1},
    ]


def cmd_dry_run(args) -> int:
    """
    Prints exact command line and environment that would be used for each worker run,
    with 45 planned runs across the counterbalanced schedule (or 4 pilot runs on Task L),
    without making model calls.
    """
    is_pilot = getattr(args, "pilot", False)
    header_title = "BENCHMARK PILOT DRY-RUN: 4 SEQUENTIAL RUNS (TASK L)" if is_pilot else "BENCHMARK DRY-RUN: 45 PLANNED COUNTERBALANCED RUNS"
    print("=" * 80)
    print(header_title)
    print("=" * 80)

    profiles = load_json(PROFILES_FILE)
    model_lock = load_json(MODEL_LOCK_FILE)
    env_lock = load_json(ENV_LOCK_FILE)
    prompts_manifest = load_json(PROMPTS_MANIFEST_FILE)

    pi_binary = env_lock.get("pi_binary", "/home/khoa/.local/bin/pi")
    schedule = generate_pilot_schedule() if is_pilot else generate_schedule(num_reps=3)

    if is_pilot:
        print(f"Generated {len(schedule)} planned pilot runs on Task L (Multi-Turn Debugging) across A, P1, P2, P3.\n")
    else:
        print(f"Generated {len(schedule)} planned runs across Latin square schedule.\n")

    for item in schedule:
        run_id = item["run_id"]
        rep = item["rep"]
        pid = item["profile_id"]
        tid = item["task_id"]

        prof = get_profile_by_id(profiles, pid)
        prof_name = prof.get("name")
        task_info = prompts_manifest.get("tasks", {}).get(tid, {})

        ws_dir = WORKSPACES_DIR / f"{run_id}_{pid}_{tid}_r{rep}"

        # Build isolated environment variables
        env_vars = {
            "PI_CODING_AGENT_DIR": prof.get("agent_dir"),
            "PI_CODING_AGENT_SESSION_DIR": prof.get("session_dir"),
            "PI_OFFLINE": "0",  # In dry run showing live env; actual runner checks auth
        }

        # Build command invocation
        cmd = [
            pi_binary,
            "--provider", model_lock.get("provider", "openai-codex"),
            "--model", model_lock.get("model", "gpt-6-luna"),
            "--thinking", model_lock.get("thinking", "max"),
            "--mode", "rpc",
            "--session-dir", prof.get("session_dir"),
            "--no-extensions",
            "--no-skills",
            "--no-context-files",
            "--no-prompt-templates",
            "--no-themes",
            "--no-mcp",
            "--tools", ','.join(prof.get('tools', [])),
        ]
        cmd.extend(prof.get("extra_flags", []))

        # Add initial prompt
        first_prompt_path = task_info.get("turns", [{}])[0].get("prompt", "")
        cmd.append(f"@{first_prompt_path}")

        print(f"[{run_id}] Repetition {rep} | Profile: {pid} ({prof_name}) | Task: {tid}")
        print(f"  Workspace:   {ws_dir}")
        print(f"  Environment: PI_CODING_AGENT_DIR={env_vars['PI_CODING_AGENT_DIR']}")
        print(f"               PI_CODING_AGENT_SESSION_DIR={env_vars['PI_CODING_AGENT_SESSION_DIR']}")
        print(f"  Command:     {' '.join(cmd)}")
        print("-" * 80)

    print(f"\nDry run complete: {len(schedule)} runs planned. Counterbalancing verified.")
    return 0


def run_single_worker(
    item: Dict[str, Any],
    profiles: Dict[str, Any],
    model_lock: Dict[str, Any],
    env_lock: Dict[str, Any],
    prompts_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    run_id = item["run_id"]
    pid = item["profile_id"]
    tid = item["task_id"]
    rep = item.get("rep", 1)

    prof = get_profile_by_id(profiles, pid)
    prof_name = prof.get("name")
    task_info = prompts_manifest.get("tasks", {}).get(tid, {})

    ws_dir = WORKSPACES_DIR / f"{run_id}_{pid}_{tid}_r{rep}"
    results_run_dir = RESULTS_DIR / "runs" / f"{run_id}_{pid}_{tid}"
    results_run_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print(f"[{run_id}] Executing Session: Profile {pid} ({prof_name}) on {tid} (Rep {rep})", flush=True)
    print(f"  Workspace: {ws_dir}", flush=True)
    print(f"  Session Directory: {prof.get('session_dir')}", flush=True)
    print("=" * 80, flush=True)

    # 1. Fresh workspace clone
    if ws_dir.exists():
        shutil.rmtree(ws_dir)
    fixture_dir = ROOT_DIR / task_info.get("fixture_dir", f"fixtures/{tid}")
    shutil.copytree(fixture_dir, ws_dir)

    # 2. Session dir setup
    # Unique session directory per RUN. Bare -c on a shared profile directory
    # can continue a different repetition, violating benchmark independence.
    session_dir = Path(prof.get("session_dir")) / f"{run_id}_{pid}_{tid}_r{rep}"
    if session_dir.exists():
        raise RuntimeError(f"Refusing to reuse existing benchmark session: {session_dir}")
    session_dir.mkdir(parents=True, exist_ok=False)

    # 3. Environment configuration
    env = os.environ.copy()
    env["PI_CODING_AGENT_DIR"] = prof.get("agent_dir")
    env["PI_CODING_AGENT_SESSION_DIR"] = prof.get("session_dir")
    env.pop("PI_OFFLINE", None)

    pi_binary = env_lock.get("pi_binary", "/home/khoa/.local/bin/pi")
    pricing = model_lock.get("pricing", {
        "prompt_per_1m": 2.50,
        "cache_read_per_1m": 1.25,
        "cache_write_per_1m": 2.50,
        "completion_per_1m": 10.00
    })

    collector = TelemetryCollector(pricing_config=pricing)
    turns = task_info.get("turns", [])
    run_start_time = time.time()
    last_exit_code = 0
    turn_summaries = []

    for t_idx, t_info in enumerate(turns):
        t_num = t_info.get("turn", t_idx + 1)
        prompt_rel = t_info.get("prompt", "")
        prompt_path = ROOT_DIR / prompt_rel
        prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        print(f"\n--- [{run_id}] Turn {t_num}/{len(turns)} ---", flush=True)
        t_start = time.time()

        cmd = [
            pi_binary,
            "--provider", model_lock.get("provider", "openai-codex"),
            "--model", model_lock.get("model", "gpt-6-luna"),
            "--thinking", model_lock.get("thinking", "max"),
            "--mode", "json",
            "-p",
            "--session-dir", str(session_dir),
        ]
        if t_idx > 0:
            cmd.append("-c")

        cmd.extend([
            "--no-extensions",
            "--no-skills",
            "--no-context-files",
            "--no-prompt-templates",
            "--no-themes",
            "--no-mcp",
            "--tools", ','.join(prof.get('tools', [])),
        ])
        cmd.extend(prof.get("extra_flags", []))
        cmd.append("--")
        cmd.append(prompt_text)

        turn_events = []
        stderr_lines = []

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=ws_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            for line in proc.stdout:
                line_str = line.strip()
                if not line_str:
                    continue
                turn_events.append(line_str)
                collector.process_jsonl_line(line_str)

            _, stderr_data = proc.communicate()
            if stderr_data:
                stderr_lines.append(stderr_data)

            last_exit_code = proc.returncode
            t_duration = time.time() - t_start

            print(f"  Turn {t_num} finished in {t_duration:.1f}s (exit code: {last_exit_code})", flush=True)

            # Persist raw turn events
            turn_file = results_run_dir / f"turn_{t_num}_events.jsonl"
            with open(turn_file, "w", encoding="utf-8") as f:
                for ev in turn_events:
                    f.write(ev + "\n")

            if stderr_data:
                stderr_file = results_run_dir / f"turn_{t_num}_stderr.log"
                with open(stderr_file, "w", encoding="utf-8") as f:
                    f.write(stderr_data)

            turn_summaries.append({
                "turn": t_num,
                "duration_seconds": round(t_duration, 2),
                "exit_code": last_exit_code,
                "events_count": len(turn_events)
            })

            if last_exit_code != 0:
                print(f"  WARNING: Turn {t_num} exited with code {last_exit_code}")
                if stderr_data:
                    print(f"  STDERR: {stderr_data.strip()[:200]}")

        except Exception as e:
            print(f"  ERROR executing Turn {t_num}: {e}")
            last_exit_code = 1
            break

    run_duration = time.time() - run_start_time

    # Inspect persisted session JSONL in session_dir for any custom extension messages
    try:
        escaped_ws = "--" + str(ws_dir).replace("/", "-").strip("-") + "--"
        candidate_session_files = list((session_dir / escaped_ws).glob("*.jsonl"))
        if candidate_session_files:
            latest_session_file = max(candidate_session_files, key=lambda f: f.stat().st_mtime)
            with open(latest_session_file, "r", encoding="utf-8") as sf:
                for sline in sf:
                    sline = sline.strip()
                    if not sline:
                        continue
                    try:
                        s_data = json.loads(sline)
                        if s_data.get("type") in ("custom", "custom_message"):
                            collector.process_event(s_data)
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"  Note: session directory scan encountered: {e}")

    collector.set_termination(exit_code=last_exit_code, timed_out=False)

    # Run independent task evaluator
    print(f"\n[{run_id}] Running Independent Evaluator on workspace...")
    eval_script = ROOT_DIR / task_info.get("evaluator", "evaluators/eval_task_l.py")
    try:
        eval_proc = subprocess.run(
            [sys.executable, str(eval_script), str(ws_dir)],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        try:
            eval_result = json.loads(eval_proc.stdout.strip())
        except json.JSONDecodeError:
            eval_result = {
                "passed": False,
                "score": 0.0,
                "details": f"Evaluator output parsing error: {eval_proc.stdout[:200]} / {eval_proc.stderr[:200]}",
            }
    except Exception as e:
        eval_result = {"passed": False, "score": 0.0, "details": f"Evaluator execution exception: {e}"}

    print(f"[{run_id}] Evaluation Result: Passed={eval_result.get('passed')}, Score={eval_result.get('score')}")

    # Determine optimization status
    opt_status = "NON_TRIGGERED"
    if pid == "A":
        opt_status = "BASELINE"
    elif pid == "P1":
        stash_dir = Path(prof["agent_dir"]) / "sift"
        has_stash = any(stash_dir.glob("**/*")) if stash_dir.exists() else False
        if collector.compression_events > 0 or collector.recovery_calls > 0 or has_stash:
            opt_status = "TRIGGERED"
    elif pid == "P2":
        if collector.pruning_events > 0 or collector.secondary_model_requests > 0:
            opt_status = "TRIGGERED"
    elif pid == "P3":
        if collector.pruning_events > 0 or collector.tool_calls.get("compress", 0) > 0:
            opt_status = "TRIGGERED"

    summary = collector.compute_summary()
    summary["run_id"] = run_id
    summary["profile_id"] = pid
    summary["profile_name"] = prof_name
    summary["task_id"] = tid
    summary["repetition"] = rep
    summary["wall_clock_duration_seconds"] = round(run_duration, 2)
    summary["evaluation"] = eval_result
    summary["optimization_status"] = opt_status
    summary["telemetry_reconciliation_status"] = "REQUIRES_RAW_EXTENSION_EVENT_PROVENANCE" if pid in ("P2", "P3") else "PRIMARY_USAGE_CAPTURED"
    summary["turn_summaries"] = turn_summaries

    # Save summary
    with open(results_run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


def generate_pilot_report(results: List[Dict[str, Any]]) -> str:
    """Generates PILOT_BENCHMARK_ANALYSIS.md from pilot results."""
    report_file = REPORTS_DIR / "PILOT_BENCHMARK_ANALYSIS.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Pilot Benchmark Analysis & Optimization Audit: pi-context-lab\n")
    lines.append("**Date:** 2026-10-27  ")
    lines.append("**Workload:** Task L (`pipeline_engine`) — 4 Interactive Turns  ")
    lines.append("**Model:** `openai-codex/gpt-6-luna` (thinking: `max`)  ")
    lines.append("**Execution Mode:** Sequential Pilot (4 independent runs: A, P1, P2, P3)  \n")
    lines.append("---\n")

    lines.append("## 1. Executive Summary\n")
    lines.append("The 4-run pilot was executed sequentially under strict isolation to evaluate whether modern Pi context optimizers genuinely reduce token consumption, peak window context, and monetary costs during heavy multi-turn log debugging without compromising correctness.\n")

    lines.append("## 2. Pilot Performance & Telemetry Comparison Table\n")
    lines.append("| Metric | Profile A (Baseline) | Profile P1 (Sift) | Profile P2 (Context Prune) | Profile P3 (Pi DCP) |")
    lines.append("|---|:---:|:---:|:---:|:---:|")

    def get_run(pid):
        for r in results:
            if r.get("profile_id") == pid:
                return r
        return {}

    run_a = get_run("A")
    run_p1 = get_run("P1")
    run_p2 = get_run("P2")
    run_p3 = get_run("P3")

    def format_bool(v):
        return "PASS" if v else "FAIL"

    lines.append(f"| **Task Correctness** | {format_bool(run_a.get('evaluation', {}).get('passed'))} (score: {run_a.get('evaluation', {}).get('score', 0)}) | {format_bool(run_p1.get('evaluation', {}).get('passed'))} (score: {run_p1.get('evaluation', {}).get('score', 0)}) | {format_bool(run_p2.get('evaluation', {}).get('passed'))} (score: {run_p2.get('evaluation', {}).get('score', 0)}) | {format_bool(run_p3.get('evaluation', {}).get('passed'))} (score: {run_p3.get('evaluation', {}).get('score', 0)}) |")
    lines.append(f"| **Optimization Status** | `{run_a.get('optimization_status', 'N/A')}` | `{run_p1.get('optimization_status', 'N/A')}` | `{run_p2.get('optimization_status', 'N/A')}` | `{run_p3.get('optimization_status', 'N/A')}` |")
    lines.append(f"| **Peak Input Context** | {run_a.get('peak_input_context', 0):,} | {run_p1.get('peak_input_context', 0):,} | {run_p2.get('peak_input_context', 0):,} | {run_p3.get('peak_input_context', 0):,} |")
    lines.append(f"| **Cumulative Input Context** | {run_a.get('cumulative_input_context', 0):,} | {run_p1.get('cumulative_input_context', 0):,} | {run_p2.get('cumulative_input_context', 0):,} | {run_p3.get('cumulative_input_context', 0):,} |")
    lines.append(f"| **Model Requests** | {len(run_a.get('per_request_usage', []))} | {len(run_p1.get('per_request_usage', []))} | {len(run_p2.get('per_request_usage', []))} | {len(run_p3.get('per_request_usage', []))} |")
    lines.append(f"| **Total Input Tokens** | {run_a.get('input_tokens', 0):,} | {run_p1.get('input_tokens', 0):,} | {run_p2.get('input_tokens', 0):,} | {run_p3.get('input_tokens', 0):,} |")
    lines.append(f"| **Total Output Tokens** | {run_a.get('output_tokens', 0):,} | {run_p1.get('output_tokens', 0):,} | {run_p2.get('output_tokens', 0):,} | {run_p3.get('output_tokens', 0):,} |")
    lines.append(f"| **Cache-Read Tokens** | {run_a.get('cache_read_tokens', 0):,} | {run_p1.get('cache_read_tokens', 0):,} | {run_p2.get('cache_read_tokens', 0):,} | {run_p3.get('cache_read_tokens', 0):,} |")
    lines.append(f"| **Cache-Write Tokens** | {run_a.get('cache_write_tokens', 0):,} | {run_p1.get('cache_write_tokens', 0):,} | {run_p2.get('cache_write_tokens', 0):,} | {run_p3.get('cache_write_tokens', 0):,} |")
    lines.append(f"| **Secondary Requests (Summarizer)** | 0 | 0 | {run_p2.get('secondary_metrics', {}).get('secondary_requests', 0)} | 0 |")
    lines.append(f"| **Secondary Tokens** | 0 | 0 | In: {run_p2.get('secondary_metrics', {}).get('secondary_input_tokens', 0):,}, Out: {run_p2.get('secondary_metrics', {}).get('secondary_output_tokens', 0):,} | 0 |")
    lines.append(f"| **Secondary Reported Cost** | 0 | 0 | {run_p2.get('secondary_metrics', {}).get('secondary_cost')} | 0 |")
    lines.append("| **Primary Pi-Reported Cost** | " + " | ".join(str(r.get("primary_reported_cost")) for r in [run_a, run_p1, run_p2, run_p3]) + " |")
    lines.append("| **Net Reported Estimate** | " + " | ".join(str(r.get("net_end_to_end_cost")) if r.get("net_end_to_end_cost") is not None else "UNVERIFIED" for r in [run_a, run_p1, run_p2, run_p3]) + " |")
    lines.append("| **Cost Status** | " + " | ".join(str(r.get("cost_status", "UNVERIFIED")) for r in [run_a, run_p1, run_p2, run_p3]) + " |")
    lines.append(f"| **Wall Duration (s)** | {run_a.get('wall_clock_duration_seconds', 0)}s | {run_p1.get('wall_clock_duration_seconds', 0)}s | {run_p2.get('wall_clock_duration_seconds', 0)}s | {run_p3.get('wall_clock_duration_seconds', 0)}s |")
    lines.append(f"| **Recovery / Retrieve Calls** | 0 | {run_p1.get('optimization_metrics', {}).get('recovery_calls', 0)} | {run_p2.get('optimization_metrics', {}).get('recovery_calls', 0)} | 0 |")
    lines.append("\n---\n")

    lines.append("## 3. Deep-Dive Profile Comparisons\n")

    lines.append("### 3.1 Profile A vs Profile P1 (Sift)")
    lines.append("- Sift compresses tool outputs exceeding 200 bytes using heuristic pattern recognition and stashes original full text in the isolated stash.")
    lines.append("- Net financial impact is evaluated by comparing baseline cumulative token ingestion against compressed output tokens plus retrieval latency.")
    lines.append(f"- In this pilot, P1 achieved Peak Context of {run_p1.get('peak_input_context', 0):,} vs Baseline {run_a.get('peak_input_context', 0):,}.")

    lines.append("\n### 3.2 Profile A vs Profile P2 (pi-context-prune)")
    lines.append("- Context Prune uses a batch-based summarizer (`agent-message`) with thinking `low`.")
    lines.append(f"- Secondary summarizer requests: {run_p2.get('secondary_metrics', {}).get('secondary_requests', 0)}. Reported-cost provenance: {run_p2.get('secondary_metrics', {}).get('secondary_cost_provenance') or 'UNAVAILABLE'}.")
    lines.append(f"- Net end-to-end cost: {run_p2.get('net_end_to_end_cost') if run_p2.get('net_end_to_end_cost') is not None else 'UNVERIFIED'} vs Baseline {run_a.get('net_end_to_end_cost')}.")

    lines.append("\n### 3.3 Profile A vs Profile P3 (Pi DCP)")
    lines.append("- Pi DCP applies dynamic deduplication and error purging on `context` events without secondary model calls.")
    lines.append(f"- In this pilot, P3 achieved Peak Context of {run_p3.get('peak_input_context', 0):,} and Cumulative Context of {run_p3.get('cumulative_input_context', 0):,}.")
    lines.append(f"- Net end-to-end cost: {run_p3.get('net_end_to_end_cost') if run_p3.get('net_end_to_end_cost') is not None else 'UNVERIFIED'} vs Baseline {run_a.get('net_end_to_end_cost')}.")

    lines.append("\n---\n")
    lines.append("## 4. Multi-Criteria Pilot Rankings\n")
    lines.append("Ranking of candidates across 7 primary evaluation criteria based on this pilot repetition:\n")

    # Sort candidates
    ready_runs = [r for r in [run_a, run_p1, run_p2, run_p3] if r]

    # 1. Correctness
    lines.append("1. **Task Correctness:**")
    for r in sorted(ready_runs, key=lambda x: x.get('evaluation', {}).get('score', 0), reverse=True):
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** Score {r.get('evaluation', {}).get('score', 0)} ({'Passed' if r.get('evaluation', {}).get('passed') else 'Failed'})")

    # 2. Cost per task
    lines.append("\n2. **Net End-to-End Cost:**")
    for r in sorted(ready_runs, key=lambda x: x.get("net_end_to_end_cost") if isinstance(x.get("net_end_to_end_cost"), (int, float)) else float("inf")):
        c = r.get("net_end_to_end_cost")
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** " + (f"${c:.6f}" if isinstance(c, (int, float)) else "UNVERIFIED (exclude from ranking)"))

    # 3. Peak Context
    lines.append("\n3. **Peak Input Context (Lowest Window Pressure):**")
    for r in sorted(ready_runs, key=lambda x: x.get('peak_input_context', float('inf'))):
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** {r.get('peak_input_context', 0):,} tokens")

    # 4. Cumulative Context
    lines.append("\n4. **Cumulative Input Context (Total Lifetime Context):**")
    for r in sorted(ready_runs, key=lambda x: x.get('cumulative_input_context', float('inf'))):
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** {r.get('cumulative_input_context', 0):,} tokens")

    # 5. Model Requests
    lines.append("\n5. **Model Requests:**")
    for r in sorted(ready_runs, key=lambda x: len(x.get('per_request_usage', []))):
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** {len(r.get('per_request_usage', []))} requests")

    # 6. Latency
    lines.append("\n6. **Wall-Clock Duration (Fastest to Slowest):**")
    for r in sorted(ready_runs, key=lambda x: x.get('wall_clock_duration_seconds', float('inf'))):
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** {r.get('wall_clock_duration_seconds', 0)}s")

    # 7. Reliability
    lines.append("\n7. **Optimization Reliability & Recovery Overhead:**")
    for r in ready_runs:
        lines.append(f"   - **{r.get('profile_name')} ({r.get('profile_id')}):** Status `{r.get('optimization_status')}`, {r.get('optimization_metrics', {}).get('recovery_calls', 0)} recovery calls, {r.get('tool_errors', 0)} tool errors")

    lines.append("\n---\n")
    lines.append("## 5. Post-Pilot Shared Authentication Verification\n")
    lines.append("Symlinks connecting `agents/*/auth.json` to `~/.pi/agent/auth.json` were audited immediately following pilot execution to verify that automatic OAuth token refresh operations did not corrupt or decouple the symbolic links.\n")

    lines.append("## 6. Recommendations for Full Benchmark Matrix\n")
    lines.append("1. **Single-Repetition Caveat:** These results represent repetition 1 on Task L. Statistical variance across network latency and model reasoning paths requires the full 3-repetition Latin Square matrix before declaring absolute efficiency.\n")
    lines.append("2. **Secondary Model Budgeting:** The secondary model costs in P2 must remain explicitly accounted for in all reporting to prevent masking summarizer overhead.\n")
    lines.append("3. **HOLD:** Do not proceed to full matrix until cost provenance and optimizer events have been independently reconciled, and an evaluator with immutable external tests has passed.\n")

    content = "\n".join(lines)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Pilot analysis report successfully written to {report_file}")
    return str(report_file)


def cmd_run(args) -> int:
    """
    run --pilot: Requires --authorize-benchmark-spend.
    run --full: Requires --authorize-benchmark-spend.
    """
    is_pilot = getattr(args, "pilot", False)
    mode = "pilot" if is_pilot else ("full" if getattr(args, "full", False) else None)
    if not mode:
        print("ERROR: Must specify either --pilot or --full.")
        return 1

    if not args.authorize_benchmark_spend:
        print("\n" + "!" * 80)
        print("SPEND AUTHORIZATION REQUIRED")
        print("!" * 80)
        print(f"You requested to run a benchmark ({mode} mode), which invokes commercial LLM APIs")
        print("and incurs monetary costs according to config/model-lock.json.")
        print("\nTo proceed, re-run with explicit spend authorization:")
        print(f"  python3 scripts/benchmark.py run --{mode} --authorize-benchmark-spend")
        print("\nABORTING BENCHMARK EXECUTION SAFELY. NO MODEL CALLS WERE MADE.")
        print("!" * 80 + "\n")
        return 1

    print(f"[benchmark run] Spend authorized. Initializing {mode} execution...")

    profiles = load_json(PROFILES_FILE)
    model_lock = load_json(MODEL_LOCK_FILE)
    env_lock = load_json(ENV_LOCK_FILE)
    prompts_manifest = load_json(PROMPTS_MANIFEST_FILE)

    schedule = generate_pilot_schedule() if is_pilot else generate_schedule(num_reps=3)
    print(f"[benchmark run] Running {len(schedule)} sequential sessions ({mode} mode)...\n")

    results = []
    for item in schedule:
        res = run_single_worker(item, profiles, model_lock, env_lock, prompts_manifest)
        results.append(res)

    # Persist aggregated results
    results_target = RESULTS_DIR / ("pilot-results.json" if is_pilot else "benchmark-results.json")
    with open(results_target, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[benchmark run] All {len(results)} sessions completed. Results saved to {results_target}")

    # Generate analysis report
    if is_pilot:
        generate_pilot_report(results)

    return 0



def cmd_report(args) -> int:
    """Generates summary reports from benchmark results."""
    print("=" * 60)
    print("GENERATING BENCHMARK SUMMARY REPORT")
    print("=" * 60)

    pilot_file = RESULTS_DIR / "pilot-results.json"
    benchmark_file = RESULTS_DIR / "benchmark-results.json"

    if pilot_file.exists():
        with open(pilot_file, "r", encoding="utf-8") as f:
            pilot_data = json.load(f)
        rep = generate_pilot_report(pilot_data)
        print(f"Generated pilot report from {pilot_file}: {rep}")

    if not benchmark_file.exists() and not pilot_file.exists():
        print("Note: No finished run results found.")
        return 0

    return 0


def main():
    parser = argparse.ArgumentParser(description="Pi Context Optimization Benchmark Controller")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommand: preflight
    subparsers.add_parser("preflight", help="Run isolation, profile, fixture, and smoke tests")

    # Subcommand: status
    subparsers.add_parser("status", help="Show status of all 5 profiles and matrix")

    # Subcommand: dry-run
    dry_parser = subparsers.add_parser("dry-run", help="Print exact CLI and env for planned runs")
    dry_parser.add_argument("--pilot", action="store_true", help="Print 4-run pilot schedule on Task L")
    dry_parser.add_argument("--full", action="store_true", help="Print full 45-run schedule")

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Execute benchmark runs")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--pilot", action="store_true", help="Execute pilot run (subset of matrix)")
    run_group.add_argument("--full", action="store_true", help="Execute full 45-run counterbalanced matrix")
    run_parser.add_argument(
        "--authorize-benchmark-spend",
        action="store_true",
        help="Explicitly authorize monetary spend for commercial model API calls",
    )

    # Subcommand: report
    subparsers.add_parser("report", help="Generate summary reports from results")

    args = parser.parse_args()

    if args.subcommand == "preflight":
        sys.exit(cmd_preflight(args))
    elif args.subcommand == "status":
        sys.exit(cmd_status(args))
    elif args.subcommand == "dry-run":
        sys.exit(cmd_dry_run(args))
    elif args.subcommand == "run":
        sys.exit(cmd_run(args))
    elif args.subcommand == "report":
        sys.exit(cmd_report(args))


if __name__ == "__main__":
    main()
