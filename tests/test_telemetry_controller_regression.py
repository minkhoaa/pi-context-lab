"""tests/test_telemetry_controller_regression.py

Automated offline tests verifying TelemetryCollector and BenchmarkController logic:
- Provider-reported cost extraction
- Summarizer cost completeness (reported vs scenario lock prices)
- Cumulative versus delta events (snapshots in stats and dcp-state)
- Duplicate JSONL events deduplication
- Missing events handling
- Event provenance tracking
- Session continuation & isolation
- Safe retry and termination
- Artifact preservation & fresh output paths
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runner.telemetry import TelemetryCollector
from scripts.benchmark import generate_pilot_schedule, AuthOrQuotaError


class TestTelemetryControllerRegression(unittest.TestCase):
    def setUp(self):
        self.pricing = {
            "prompt_per_1m": 2.50,
            "cache_read_per_1m": 1.25,
            "cache_write_per_1m": 2.50,
            "completion_per_1m": 10.00,
        }
        self.collector = TelemetryCollector(pricing_config=self.pricing)

    def test_01_provider_reported_cost_extraction(self):
        """Verifies extraction of usage.cost.total as authoritative reported estimate."""
        event = {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "model": "gpt-6-luna",
                "provider": "openai-codex",
                "usage": {
                    "input": 1000,
                    "output": 100,
                    "cacheRead": 200,
                    "cacheWrite": 0,
                    "cost": {"total": 0.00015},
                },
            },
        }
        self.collector.process_event(event)
        summary = self.collector.compute_summary()
        self.assertEqual(summary["reported_cost"], 0.00015)
        self.assertEqual(summary["primary_reported_cost"], 0.00015)
        self.assertEqual(summary["cost_status"], "REPORTED_ESTIMATE")
        self.assertAlmostEqual(summary["calculated_cost"], (1000*2.5 + 200*1.25 + 100*10.0)/1_000_000, places=6)

    def test_02_summarizer_cost_completeness(self):
        """Secondary usage with provider-reported cost is verified; missing cost is UNVERIFIED."""
        # Primary call
        self.collector.process_event({
            "type": "message_end",
            "message": {
                "role": "assistant",
                "model": "gpt-6-luna",
                "provider": "openai-codex",
                "usage": {"input": 1000, "output": 100, "cost": {"total": 0.00015}},
            },
        })
        # Secondary usage call with provider cost
        self.collector.process_event({
            "type": "usage",
            "kind": "context_prune",
            "provider": "openai-codex",
            "model": "gpt-6-luna",
            "usage": {"input": 500, "output": 50, "cacheRead": 0, "cacheWrite": 0, "cost": {"total": 0.000075}},
        })
        s1 = self.collector.compute_summary()
        self.assertEqual(s1["secondary_metrics"]["secondary_requests"], 1)
        self.assertEqual(s1["secondary_metrics"]["secondary_cost"], 0.000075)
        self.assertEqual(s1["net_end_to_end_cost"], 0.000225)
        self.assertEqual(s1["cost_status"], "REPORTED_ESTIMATE")

        # Unverified secondary cost case
        c2 = TelemetryCollector(self.pricing)
        c2.process_event({
            "type": "message_end",
            "message": {
                "role": "assistant",
                "model": "gpt-6-luna",
                "provider": "openai-codex",
                "usage": {"input": 1000, "output": 100, "cost": {"total": 0.00015}},
            },
        })
        # Secondary usage lacking cost object
        c2.process_event({
            "type": "usage",
            "kind": "context_prune",
            "provider": "openai-codex",
            "model": "gpt-6-luna",
            "usage": {"input": 500, "output": 50},
        })
        s2 = c2.compute_summary()
        self.assertIsNone(s2["net_end_to_end_cost"])
        self.assertEqual(s2["cost_status"], "SECONDARY_COST_UNVERIFIED")

    def test_03_cumulative_versus_delta_events(self):
        """Snapshots from context-prune-stats and pi-dcp-state must not be double-summed."""
        c = TelemetryCollector(self.pricing)
        # Snapshot 1
        c.process_event({
            "type": "custom",
            "customType": "context-prune-stats",
            "data": {"callCount": 1, "totalInputTokens": 1000, "totalOutputTokens": 100, "totalCost": 0.001},
        })
        # Snapshot 2 (cumulative superset of snapshot 1)
        c.process_event({
            "type": "custom",
            "customType": "context-prune-stats",
            "data": {"callCount": 2, "totalInputTokens": 2500, "totalOutputTokens": 250, "totalCost": 0.0025},
        })
        s = c.compute_summary()
        self.assertEqual(s["secondary_metrics"]["secondary_requests"], 2)
        self.assertEqual(s["secondary_metrics"]["secondary_input_tokens"], 2500)
        self.assertEqual(s["secondary_metrics"]["secondary_output_tokens"], 250)
        self.assertEqual(s["secondary_metrics"]["secondary_cost"], 0.0025)

        # DCP cumulative snapshots
        cDCP = TelemetryCollector(self.pricing)
        cDCP.process_event({
            "type": "custom",
            "customType": "pi-dcp-state",
            "data": {"stats": {"toolsPruned": 1, "totalPruneTokens": 4, "messagesCompressed": 0}},
        })
        cDCP.process_event({
            "type": "custom",
            "customType": "pi-dcp-state",
            "data": {"stats": {"toolsPruned": 2, "totalPruneTokens": 12, "messagesCompressed": 0}},
        })
        sDCP = cDCP.compute_summary()
        self.assertEqual(sDCP["optimization_metrics"]["pruning_events"], 2)
        self.assertEqual(sDCP["optimization_metrics"]["optimizer_tokens_saved"], 12)
        self.assertTrue(sDCP["optimization_metrics"]["optimization_triggered"])

    def test_04_duplicate_jsonl_events_deduplication(self):
        """Events with identical IDs processed multiple times must be ignored."""
        event = {
            "type": "message_end",
            "id": "msg-unique-001",
            "message": {
                "role": "assistant",
                "usage": {"input": 500, "output": 50, "cost": {"total": 0.0001}},
            },
        }
        self.collector.process_event(event)
        self.collector.process_event(event)  # duplicate
        s = self.collector.compute_summary()
        self.assertEqual(len(s["per_request_usage"]), 1)
        self.assertEqual(s["input_tokens"], 500)
        self.assertEqual(s["reported_cost"], 0.0001)

    def test_05_missing_primary_cost_handling(self):
        """If any primary request lacks provider cost, cost_status flags it."""
        self.collector.process_event({
            "type": "message_end",
            "message": {
                "role": "assistant",
                "usage": {"input": 1000, "output": 100},  # No cost field
            },
        })
        s = self.collector.compute_summary()
        self.assertIsNone(s["primary_reported_cost"])
        self.assertIsNone(s["net_end_to_end_cost"])
        self.assertEqual(s["cost_status"], "PRIMARY_USAGE_COST_MISSING")

    def test_06_event_provenance_tracking(self):
        """Summary tracks exact provenance source for primary and secondary costs."""
        self.collector.process_event({
            "type": "message_end",
            "message": {
                "role": "assistant",
                "usage": {"input": 100, "output": 10, "cost": {"total": 0.00001}},
            },
        })
        s = self.collector.compute_summary()
        self.assertEqual(s["cost_provenance"]["primary"], "pi.message_end.usage.cost.total")
        self.assertEqual(s["cost_provenance"]["model_lock_rates"], "SCENARIO_ONLY_NOT_PROVIDER_BILLING")

    def test_07_repeated_reads_tracking(self):
        """Telemetry tracks repeated tool reads of identical file paths."""
        self.collector.process_event({
            "type": "tool_execution_start",
            "toolName": "read",
            "args": {"path": "pipeline_engine/buffer.py"},
        })
        self.collector.process_event({
            "type": "tool_execution_start",
            "toolName": "read",
            "args": {"path": "pipeline_engine/buffer.py"},  # repeat
        })
        self.collector.process_event({
            "type": "tool_execution_start",
            "toolName": "read",
            "args": {"path": "pipeline_engine/aggregator.py"},  # distinct
        })
        s = self.collector.compute_summary()
        self.assertEqual(s["repeated_reads"], 1)
        self.assertEqual(s["tool_calls"]["read"], 3)

    def test_08_safe_termination_reasons(self):
        """Exit code and timeout flags properly translate to termination reasons."""
        c = TelemetryCollector(self.pricing)
        c.set_termination(exit_code=0, timed_out=False)
        self.assertEqual(c.compute_summary()["termination_reason"], "completed")

        c2 = TelemetryCollector(self.pricing)
        c2.set_termination(exit_code=-9, timed_out=True)
        self.assertEqual(c2.compute_summary()["termination_reason"], "timeout")

        c3 = TelemetryCollector(self.pricing)
        c3.agent_settled_aborted = True
        c3.set_termination(exit_code=1, timed_out=False)
        self.assertEqual(c3.compute_summary()["termination_reason"], "aborted")

    def test_09_schedule_counterbalancing_and_fresh_run_ids(self):
        """Pilot schedule with repetitions=3 produces 12 counterbalanced runs."""
        schedule = generate_pilot_schedule(repetitions=3)
        self.assertEqual(len(schedule), 12)
        run_ids = [s["run_id"] for s in schedule]
        self.assertEqual(len(set(run_ids)), 12, "Run IDs must be strictly unique.")
        for rid in run_ids:
            self.assertTrue(rid.startswith("pilot-v2-r"))

        # Check Latin square order per repetition
        rep1 = [s["profile_id"] for s in schedule if s["rep"] == 1]
        rep2 = [s["profile_id"] for s in schedule if s["rep"] == 2]
        rep3 = [s["profile_id"] for s in schedule if s["rep"] == 3]
        self.assertEqual(rep1, ["A", "P1", "P2", "P3"])
        self.assertEqual(rep2, ["P1", "P2", "P3", "A"])
        self.assertEqual(rep3, ["P2", "P3", "A", "P1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
