import json
import os
import sys
from typing import Any, Dict


class MetricsTracker:
    def __init__(self, log_path: str = "pipeline_debug.log"):
        self.log_path = log_path
        self.counts: Dict[str, int] = {}
        self.verbose_logging = True

    def increment(self, metric: str, amount: int = 1):
        self.counts[metric] = self.counts.get(metric, 0) + amount

    def dump_trace(self, context: str, error_details: Dict[str, Any], payload_sample: Any = None):
        """Dumps structured diagnostic trace upon error.
        In initial state, verbose_logging outputs multi-megabyte diagnostic trace.
        """
        if not self.verbose_logging:
            summary = {
                "status": "ERROR",
                "context": context,
                "error": error_details,
            }
            with open(self.log_path, "a") as f:
                f.write(json.dumps(summary) + "\n")
            return

        # Generates large verbose structured JSON trace (~2-4MB)
        with open(self.log_path, "a") as f:
            header = {
                "status": "FATAL_TRACE",
                "context": context,
                "error": error_details,
                "metrics": self.counts,
            }
            f.write(json.dumps(header) + "\n")

            # Output trace events simulating large pipeline memory / state dumps
            filler_block = "X" * 1024
            for i in range(2500):
                event = {
                    "trace_id": f"trace-{context}-{i:05d}",
                    "index": i,
                    "payload_state": filler_block,
                    "active_metrics": self.counts,
                }
                f.write(json.dumps(event) + "\n")
