from typing import List, Dict, Any, Optional
from .stream import Chunk
from .metrics import MetricsTracker


class StreamAggregator:
    """Aggregates items from chunks in sequence order."""

    def __init__(self, metrics: Optional[MetricsTracker] = None):
        self.metrics = metrics or MetricsTracker()
        self.collected_items: List[Dict[str, Any]] = []
        self.last_seq: int = 0
        self.reorder_buffer: Dict[int, Chunk] = {}

    def ingest(self, chunk: Chunk):
        """Ingests a chunk.
        
        BUG (Turn 3):
        Under backpressure or multi-batch buffering, chunks can arrive out of order
        (e.g., sequence 2 before sequence 1, or delayed sequences).
        The aggregator naively expects chunk.sequence_id == self.last_seq + 1.
        If chunk.sequence_id != self.last_seq + 1, instead of buffering into reorder_buffer
        and draining in order, it immediately fails and dumps a massive trace:
        'SequenceOrderError: Expected sequence X but got Y'.
        """
        expected_seq = self.last_seq + 1
        if chunk.sequence_id != expected_seq:
            # Bug: fails immediately instead of buffering out-of-order chunks
            err = {
                "error": "SequenceOrderError",
                "expected_seq": expected_seq,
                "received_seq": chunk.sequence_id,
                "reorder_buffer_size": len(self.reorder_buffer),
            }
            self.metrics.dump_trace("aggregator_out_of_order_backpressure", err)
            raise RuntimeError(
                f"Out-of-order chunk received: expected seq {expected_seq}, got {chunk.sequence_id}"
            )

        self.last_seq = chunk.sequence_id
        self.collected_items.extend(chunk.data.get("items", []))
        self.metrics.increment("items_aggregated", len(chunk.data.get("items", [])))

    def total_items(self) -> int:
        return len(self.collected_items)
