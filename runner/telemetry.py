"""
runner/telemetry.py

Telemetry collector and metric calculator for Pi benchmarking.
Computes:
- request_input_context = input + cacheRead + cacheWrite
- Peak reported input context
- Median input context
- Mean input context
- Cumulative input context
- Cache-read and cache-write tokens
- Total cost calculation based on pricing configuration
- Process termination, abort, and timeout safety
"""

import json
import statistics
import threading
from typing import Dict, Any, List, Optional


class TelemetryCollector:
    def __init__(self, pricing_config: Optional[Dict[str, float]] = None):
        """
        pricing_config format (from model-lock.json):
        {
            "prompt_per_1m": 2.50,
            "cache_read_per_1m": 1.25,
            "cache_write_per_1m": 2.50,
            "completion_per_1m": 10.00
        }
        """
        self.pricing = pricing_config or {
            "prompt_per_1m": 2.50,
            "cache_read_per_1m": 1.25,
            "cache_write_per_1m": 2.50,
            "completion_per_1m": 10.00,
        }

        self.session_id: Optional[str] = None
        self.model_id: Optional[str] = None
        self.provider: Optional[str] = None

        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.cache_read_tokens: int = 0
        self.cache_write_tokens: int = 0
        self.total_tokens: int = 0

        self.calculated_cost: float = 0.0
        self.reported_cost: float = 0.0
        self.reported_cost_observed_requests: int = 0
        self.reported_cost_missing_requests: int = 0

        self.tool_calls: Dict[str, int] = {}
        self.tool_errors: int = 0
        self.subagent_calls: int = 0
        self.recovery_calls: int = 0

        # Secondary model metrics (e.g. summarizer in pi-context-prune)
        self.secondary_model_requests: int = 0
        self.secondary_input_tokens: int = 0
        self.secondary_output_tokens: int = 0
        self.secondary_calculated_cost: float = 0.0  # Scenario pricing only
        self.secondary_reported_cost: Optional[float] = None
        self.secondary_cost_provenance: Optional[str] = None
        self.secondary_cache_read_tokens: Optional[int] = None
        self.secondary_cache_write_tokens: Optional[int] = None

        # Optimizer activation tracking
        self.pruning_events: int = 0
        self.compression_events: int = 0
        self.optimization_triggered: bool = False

        self.retry_events: int = 0
        self.compaction_events: int = 0
        self.agent_settled_aborted: bool = False
        self.assistant_stop_reason: Optional[str] = None
        self.termination_reason: str = "unknown"
        self.exit_code: Optional[int] = None
        self.timed_out: bool = False

        self.per_request_usage: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def calculate_cost(self, input_tokens: int, output_tokens: int, cache_read: int, cache_write: int) -> float:
        cost = (
            (input_tokens / 1_000_000.0) * self.pricing.get("prompt_per_1m", 0.0)
            + (cache_read / 1_000_000.0) * self.pricing.get("cache_read_per_1m", 0.0)
            + (cache_write / 1_000_000.0) * self.pricing.get("cache_write_per_1m", 0.0)
            + (output_tokens / 1_000_000.0) * self.pricing.get("completion_per_1m", 0.0)
        )
        return cost

    def process_event(self, event: Dict[str, Any]):
        """Process a single JSON event emitted by Pi (RPC / JSON mode)."""
        with self._lock:
            event_type = event.get("type")

            if event_type == "session":
                self.session_id = event.get("id")

            elif event_type == "message_end":
                msg = event.get("message", {})
                if msg.get("role") == "assistant":
                    usage = msg.get("usage", {})
                    inp = usage.get("input", 0)
                    out = usage.get("output", 0)
                    cr = usage.get("cacheRead", 0)
                    cw = usage.get("cacheWrite", 0)
                    tot = usage.get("totalTokens", inp + out + cr + cw)

                    # Compute request_input_context = input + cacheRead + cacheWrite
                    req_input_ctx = inp + cr + cw

                    # Compute cost for this request
                    req_cost = self.calculate_cost(inp, out, cr, cw)

                    reported_cost_item = 0.0
                    cost_val = usage.get("cost")
                    if isinstance(cost_val, dict):
                        reported_cost_item = cost_val.get("total", 0.0)
                    elif isinstance(cost_val, (int, float)):
                        reported_cost_item = float(cost_val)

                    if isinstance(cost_val, dict) and isinstance(cost_val.get("total"), (int, float)):
                        self.reported_cost_observed_requests += 1
                    elif isinstance(cost_val, (int, float)):
                        self.reported_cost_observed_requests += 1
                    else:
                        self.reported_cost_missing_requests += 1

                    seq_num = len(self.per_request_usage) + 1
                    compaction_before = self.compaction_events > 0

                    self.per_request_usage.append({
                        "seq": seq_num,
                        "input": inp,
                        "output": out,
                        "cacheRead": cr,
                        "cacheWrite": cw,
                        "request_input_context": req_input_ctx,
                        "calculated_cost": req_cost,
                        "reported_cost": reported_cost_item,
                        "model": msg.get("model", self.model_id),
                        "stopReason": msg.get("stopReason"),
                        "compaction_preceded": compaction_before,
                    })

                    self.input_tokens += inp
                    self.output_tokens += out
                    self.cache_read_tokens += cr
                    self.cache_write_tokens += cw
                    self.total_tokens += tot
                    self.calculated_cost += req_cost
                    self.reported_cost += reported_cost_item

                    if msg.get("stopReason"):
                        self.assistant_stop_reason = msg.get("stopReason")
                    if msg.get("model"):
                        self.model_id = msg.get("model")
                    if msg.get("provider"):
                        self.provider = msg.get("provider")

            elif event_type == "compaction_start":
                self.compaction_events += 1

            elif event_type == "compaction_end":
                res = event.get("result", {})
                if res and "usage" in res:
                    c_usage = res["usage"]
                    self.input_tokens += c_usage.get("input", 0)
                    self.output_tokens += c_usage.get("output", 0)
                    self.cache_read_tokens += c_usage.get("cacheRead", 0)
                    self.cache_write_tokens += c_usage.get("cacheWrite", 0)
                    self.total_tokens += c_usage.get("totalTokens", 0)

            elif event_type == "auto_retry_start":
                self.retry_events += 1

            elif event_type == "tool_execution_start":
                t_name = event.get("toolName", "unknown")
                self.tool_calls[t_name] = self.tool_calls.get(t_name, 0) + 1
                if t_name == "subagent":
                    self.subagent_calls += 1
                elif t_name in ("sift_retrieve", "context_tree_query"):
                    self.recovery_calls += 1
                    self.optimization_triggered = True

            elif event_type == "tool_execution_end":
                if event.get("isError"):
                    self.tool_errors += 1
                details = event.get("result", {}).get("details", {})
                if isinstance(details, dict):
                    if details.get("siftCompressed"):
                        self.compression_events += 1
                        self.optimization_triggered = True

            elif event_type in ("custom", "custom_message"):
                # Handle custom extension events (e.g. pi-context-prune stats, summaries)
                custom_type = event.get("customType") or event.get("name")
                if custom_type == "context-prune-stats":
                    data = event.get("data", {})
                    # These fields are CUMULATIVE snapshots, not deltas. They
                    # must not be summed across session entries or multiple scans.
                    self.secondary_model_requests = max(self.secondary_model_requests, int(data.get("callCount") or 0))
                    self.secondary_input_tokens = max(self.secondary_input_tokens, int(data.get("totalInputTokens") or 0))
                    self.secondary_output_tokens = max(self.secondary_output_tokens, int(data.get("totalOutputTokens") or 0))
                    self.secondary_calculated_cost = self.calculate_cost(
                        self.secondary_input_tokens, self.secondary_output_tokens, 0, 0
                    )
                    # Do not present scenario-priced cost as actual/provider cost.
                    # A summarizer that hides its true per-request price MUST be
                    # marked unverified rather than assigned the primary model rate.
                    for key in ("totalCostUSD", "totalCostUsd", "totalCost"):
                        v = data.get(key)
                        if isinstance(v, (int, float)) and v >= 0:
                            if self.secondary_reported_cost is None:
                                self.secondary_reported_cost = float(v)
                            else:
                                self.secondary_reported_cost = max(self.secondary_reported_cost, float(v))
                            self.secondary_cost_provenance = "context-prune-stats." + key
                            break
                    for key, dest in (("totalCacheReadTokens", "secondary_cache_read_tokens"),
                                      ("totalCacheWriteTokens", "secondary_cache_write_tokens")):
                        v = data.get(key)
                        if isinstance(v, (int, float)):
                            prev = getattr(self, dest) or 0
                            setattr(self, dest, max(prev, int(v)))
                    self.pruning_events = max(self.pruning_events, self.secondary_model_requests)
                    if self.secondary_model_requests > 0:
                        self.optimization_triggered = True
                elif custom_type == "context-prune-summary":
                    self.pruning_events += 1
                    self.optimization_triggered = True
                elif custom_type == "pi-dcp-state":
                    self.pruning_events += 1
                    self.optimization_triggered = True

            elif event_type == "agent_settled":
                if event.get("aborted"):
                    self.agent_settled_aborted = True

    def process_jsonl_line(self, line: str):
        line = line.strip()
        if not line:
            return
        try:
            event = json.loads(line)
            self.process_event(event)
        except json.JSONDecodeError:
            pass

    def set_termination(self, exit_code: int, timed_out: bool = False):
        self.exit_code = exit_code
        self.timed_out = timed_out
        if timed_out:
            self.termination_reason = "timeout"
        elif self.agent_settled_aborted:
            self.termination_reason = "aborted"
        elif exit_code == 0:
            self.termination_reason = "completed"
        else:
            self.termination_reason = "process_error"

    def compute_summary(self) -> Dict[str, Any]:
        with self._lock:
            contexts = [r["request_input_context"] for r in self.per_request_usage]
            peak = max(contexts) if contexts else 0
            med = float(statistics.median(contexts)) if contexts else 0.0
            mean_val = float(statistics.mean(contexts)) if contexts else 0.0
            cum_ctx = sum(contexts) if contexts else 0
            # Prior reports wrongly ranked a fixed, speculative price table as
            # actual cost. Pi's per-request usage.cost.total is the authoritative
            # *reported estimate*. It is NOT an invoice for an OAuth subscription.
            primary_cost_verified = (
                self.reported_cost_observed_requests == len(self.per_request_usage)
                and self.reported_cost_missing_requests == 0
                and len(self.per_request_usage) > 0
            )
            primary_reported = round(self.reported_cost, 6) if primary_cost_verified else None
            secondary_cost_verified = (
                self.secondary_model_requests == 0
                or self.secondary_reported_cost is not None
            )
            net_cost = (
                round(primary_reported + (self.secondary_reported_cost or 0.0), 6)
                if primary_cost_verified and secondary_cost_verified else None
            )
            cost_status = (
                "REPORTED_ESTIMATE"
                if net_cost is not None else (
                    "PRIMARY_USAGE_COST_MISSING" if not primary_cost_verified
                    else "SECONDARY_COST_UNVERIFIED"
                )
            )

            return {
                "session_id": self.session_id,
                "model_id": self.model_id,
                "provider": self.provider,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cache_read_tokens": self.cache_read_tokens,
                "cache_write_tokens": self.cache_write_tokens,
                "total_tokens": self.total_tokens,
                "calculated_cost": round(self.calculated_cost, 6),
                "reported_cost": round(self.reported_cost, 6),
                "secondary_metrics": {
                    "secondary_requests": self.secondary_model_requests,
                    "secondary_input_tokens": self.secondary_input_tokens,
                    "secondary_output_tokens": self.secondary_output_tokens,
                    "secondary_cost": self.secondary_reported_cost,
                    "secondary_modeled_cost_at_lock_prices": round(self.secondary_calculated_cost, 6),
                    "secondary_cost_provenance": self.secondary_cost_provenance,
                    "secondary_cache_read_tokens": self.secondary_cache_read_tokens,
                    "secondary_cache_write_tokens": self.secondary_cache_write_tokens,
                },
                "primary_reported_cost": primary_reported,
                "cost_status": cost_status,
                "cost_provenance": {
                    "primary": "pi.message_end.usage.cost.total",
                    "secondary": self.secondary_cost_provenance,
                    "model_lock_rates": "SCENARIO_ONLY_NOT_PROVIDER_BILLING",
                    "missing_primary_request_costs": self.reported_cost_missing_requests,
                },
                "net_end_to_end_cost": net_cost,
                "optimization_metrics": {
                    "optimization_triggered": self.optimization_triggered,
                    "pruning_events": self.pruning_events,
                    "compression_events": self.compression_events,
                    "recovery_calls": self.recovery_calls,
                },
                "context_metrics": {
                    "peak_input_context": peak,
                    "median_input_context": round(med, 1),
                    "mean_input_context": round(mean_val, 1),
                    "cumulative_input_context": cum_ctx,
                    "model_requests": len(self.per_request_usage),
                },
                "peak_input_context": peak,
                "median_input_context": round(med, 1),
                "mean_input_context": round(mean_val, 1),
                "cumulative_input_context": cum_ctx,
                "tool_calls": self.tool_calls,
                "tool_errors": self.tool_errors,
                "subagent_calls": self.subagent_calls,
                "retry_events": self.retry_events,
                "compaction_events": self.compaction_events,
                "agent_settled_aborted": self.agent_settled_aborted,
                "assistant_stop_reason": self.assistant_stop_reason,
                "termination_reason": self.termination_reason,
                "exit_code": self.exit_code,
                "timed_out": self.timed_out,
                "per_request_usage": self.per_request_usage,
            }
