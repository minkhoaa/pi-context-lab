#!/usr/bin/env python3
"""
scripts/smoke-local.py

Offline synthetic telemetry parser test.
Feeds a synthetic JSONL session with multi-turn tool calls and token usages into the telemetry collector.
Verifies computation of:
  * request_input_context = input + cacheRead + cacheWrite
  * Peak reported input context
  * Median input context
  * Cumulative input context
  * Cache-read and cache-write tokens
  * Total cost calculation based on pricing config
  * Process termination and timeout safety
"""

import sys
import json
from pathlib import Path

# Ensure pi-context-lab is in sys.path
sys.path.insert(0, str(Path("/home/khoa/pi-context-lab")))

from runner.telemetry import TelemetryCollector

MODEL_LOCK_PATH = Path("/home/khoa/pi-context-lab/config/model-lock.json")


def run_smoke_test() -> bool:
    print("[smoke-local] Starting offline synthetic telemetry test...")

    with open(MODEL_LOCK_PATH, "r", encoding="utf-8") as f:
        lock_data = json.load(f)

    pricing = lock_data.get("pricing", {
        "prompt_per_1m": 2.50,
        "cache_read_per_1m": 1.25,
        "cache_write_per_1m": 2.50,
        "completion_per_1m": 10.00,
    })

    collector = TelemetryCollector(pricing_config=pricing)

    # Synthetic JSONL events simulating a multi-turn session
    synthetic_events = [
        {"type": "session", "id": "smoke-test-session-001"},
        {"type": "tool_execution_start", "toolName": "read"},
        {"type": "tool_execution_end", "toolName": "read", "isError": False},
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "model": "gpt-6-luna",
                "provider": "openai-codex",
                "stopReason": "toolUse",
                "usage": {
                    "input": 1000,
                    "output": 200,
                    "cacheRead": 500,
                    "cacheWrite": 100,
                    "totalTokens": 1800,
                },
            },
        },
        {"type": "tool_execution_start", "toolName": "edit"},
        {"type": "tool_execution_end", "toolName": "edit", "isError": False},
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "model": "gpt-6-luna",
                "provider": "openai-codex",
                "stopReason": "toolUse",
                "usage": {
                    "input": 2000,
                    "output": 400,
                    "cacheRead": 1200,
                    "cacheWrite": 300,
                    "totalTokens": 3900,
                },
            },
        },
        {"type": "tool_execution_start", "toolName": "bash"},
        {"type": "tool_execution_end", "toolName": "bash", "isError": True},
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "model": "gpt-6-luna",
                "provider": "openai-codex",
                "stopReason": "stop",
                "usage": {
                    "input": 1500,
                    "output": 300,
                    "cacheRead": 2500,
                    "cacheWrite": 0,
                    "totalTokens": 4300,
                },
            },
        },
        {"type": "tool_execution_start", "toolName": "sift_retrieve"},
        {"type": "tool_execution_end", "toolName": "sift_retrieve", "isError": False, "result": {"details": {"found": True, "siftCompressed": True}}},
        {
            "type": "custom",
            "customType": "context-prune-stats",
            "data": {
                "callCount": 2,
                "totalInputTokens": 1500,
                "totalOutputTokens": 200,
                "totalCost": 0.00575
            }
        },
        {"type": "agent_settled", "aborted": False},
    ]

    for event in synthetic_events:
        collector.process_jsonl_line(json.dumps(event))

    collector.set_termination(exit_code=0, timed_out=False)
    summary = collector.compute_summary()

    all_ok = True

    # 1. Verify per-request request_input_context = input + cacheRead + cacheWrite
    # Turn 1: 1000 + 500 + 100 = 1600
    # Turn 2: 2000 + 1200 + 300 = 3500
    # Turn 3: 1500 + 2500 + 0 = 4000
    expected_req_contexts = [1600, 3500, 4000]
    actual_req_contexts = [r["request_input_context"] for r in summary["per_request_usage"]]

    if actual_req_contexts != expected_req_contexts:
        print(f"FAIL: request_input_context mismatch: expected {expected_req_contexts}, got {actual_req_contexts}")
        all_ok = False
    else:
        print(f"PASS: request_input_context per request verified: {actual_req_contexts}")

    # 2. Peak reported input context = max(1600, 3500, 4000) = 4000
    expected_peak = 4000
    actual_peak = summary["peak_input_context"]
    if actual_peak != expected_peak:
        print(f"FAIL: Peak input context mismatch: expected {expected_peak}, got {actual_peak}")
        all_ok = False
    else:
        print(f"PASS: Peak reported input context verified: {actual_peak}")

    # 3. Median input context = median([1600, 3500, 4000]) = 3500.0
    expected_median = 3500.0
    actual_median = summary["median_input_context"]
    if actual_median != expected_median:
        print(f"FAIL: Median input context mismatch: expected {expected_median}, got {actual_median}")
        all_ok = False
    else:
        print(f"PASS: Median input context verified: {actual_median}")

    # 4. Cumulative input context = 1600 + 3500 + 4000 = 9100
    expected_cum = 9100
    actual_cum = summary["cumulative_input_context"]
    if actual_cum != expected_cum:
        print(f"FAIL: Cumulative input context mismatch: expected {expected_cum}, got {actual_cum}")
        all_ok = False
    else:
        print(f"PASS: Cumulative input context verified: {actual_cum}")

    # 5. Cache-read and cache-write tokens
    # cache_read = 500 + 1200 + 2500 = 4200
    # cache_write = 100 + 300 + 0 = 400
    expected_cr = 4200
    expected_cw = 400
    if summary["cache_read_tokens"] != expected_cr or summary["cache_write_tokens"] != expected_cw:
        print(f"FAIL: Cache tokens mismatch: expected ({expected_cr}, {expected_cw}), got ({summary['cache_read_tokens']}, {summary['cache_write_tokens']})")
        all_ok = False
    else:
        print(f"PASS: Cache-read ({summary['cache_read_tokens']}) and cache-write ({summary['cache_write_tokens']}) tokens verified.")

    # 6. Total cost calculation based on pricing config:
    # prompt_per_1m: 2.50 -> input total: 1000 + 2000 + 1500 = 4500 -> 4500 * 2.5 / 1M = 0.01125
    # cache_read_per_1m: 1.25 -> cr total: 4200 * 1.25 / 1M = 0.00525
    # cache_write_per_1m: 2.50 -> cw total: 400 * 2.5 / 1M = 0.00100
    # completion_per_1m: 10.00 -> output total: 200 + 400 + 300 = 900 -> 900 * 10.0 / 1M = 0.00900
    # Expected total cost = 0.01125 + 0.00525 + 0.00100 + 0.00900 = 0.026500
    expected_cost = 0.0265
    actual_cost = summary["calculated_cost"]
    if abs(actual_cost - expected_cost) > 1e-6:
        print(f"FAIL: Calculated cost mismatch: expected {expected_cost}, got {actual_cost}")
        all_ok = False
    else:
        print(f"PASS: Total cost calculated correctly: ${actual_cost:.6f}")

    # 7. Tool calls and tool errors verification
    if summary["tool_calls"] != {"read": 1, "edit": 1, "bash": 1, "sift_retrieve": 1} or summary["tool_errors"] != 1:
        print(f"FAIL: Tool calls/errors mismatch: {summary['tool_calls']}, errors={summary['tool_errors']}")
        all_ok = False
    else:
        print(f"PASS: Tool calls and errors verified: {summary['tool_calls']}, errors: {summary['tool_errors']}")

    # 7b. Secondary model and recovery verification
    opt = summary["optimization_metrics"]
    sec = summary["secondary_metrics"]
    if opt["recovery_calls"] != 1 or not opt["optimization_triggered"]:
        print(f"FAIL: Optimization recovery tracking mismatch: {opt}")
        all_ok = False
    else:
        print(f"PASS: Recovery calls ({opt['recovery_calls']}) and optimization trigger verified.")

    if sec["secondary_requests"] != 2 or sec["secondary_input_tokens"] != 1500:
        print(f"FAIL: Secondary model metrics mismatch: {sec}")
        all_ok = False
    else:
        print(f"PASS: Secondary model calls ({sec['secondary_requests']}) and tokens verified.")

    # 8. Process termination and timeout safety verification
    if summary["termination_reason"] != "completed" or summary["exit_code"] != 0:
        print(f"FAIL: Termination reason mismatch: expected completed/0, got {summary['termination_reason']}/{summary['exit_code']}")
        all_ok = False

    # Test timeout safety case
    timeout_collector = TelemetryCollector(pricing_config=pricing)
    timeout_collector.set_termination(exit_code=-9, timed_out=True)
    t_sum = timeout_collector.compute_summary()
    if t_sum["termination_reason"] != "timeout" or not t_sum["timed_out"]:
        print(f"FAIL: Timeout handling verification failed: {t_sum}")
        all_ok = False
    else:
        print("PASS: Timeout and termination safety correctly handled.")

    if all_ok:
        print("\n[smoke-local] ALL TELEMETRY SMOKE CHECKS PASSED.")
        return True
    else:
        print("\n[smoke-local] TELEMETRY SMOKE CHECKS FAILED.")
        return False


if __name__ == "__main__":
    ok = run_smoke_test()
    sys.exit(0 if ok else 1)
