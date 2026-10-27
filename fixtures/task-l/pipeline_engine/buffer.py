from typing import List, Optional
from .stream import Chunk
from .metrics import MetricsTracker


class ChunkBuffer:
    """Buffers chunks received from stream, enforcing capacity and chunk validation."""

    def __init__(self, capacity: int = 10, metrics: Optional[MetricsTracker] = None):
        self.capacity = capacity
        self.metrics = metrics or MetricsTracker()
        self.queue: List[Chunk] = []

    def push(self, chunk: Chunk) -> bool:
        """Pushes a chunk into buffer.
        
        BUG (Turn 1/2):
        The buffer incorrectly checks chunk size expectation:
        It expects chunk.data['count'] to strictly equal expected_chunk_size = 5.
        However, the stream's final chunk or boundary chunk may have fewer items (count < 5).
        When count != 5, it raises a mismatch error or dumps trace and rejects the chunk.
        """
        expected_size = 5
        # Bug: Doesn't allow chunks with size <= expected_size when chunk.is_last is True
        # Instead, it strictly asserts count == expected_size
        actual_count = chunk.data.get("count", 0)
        if actual_count != expected_size:
            err = {
                "error": "ChunkSizeMismatch",
                "sequence_id": chunk.sequence_id,
                "expected": expected_size,
                "actual": actual_count,
                "is_last": chunk.is_last,
            }
            self.metrics.dump_trace("buffer_push_chunk_mismatch", err)
            raise ValueError(f"Stream chunk mismatch at sequence {chunk.sequence_id}: expected {expected_size}, got {actual_count}")

        if len(self.queue) >= self.capacity:
            return False

        self.queue.append(chunk)
        self.metrics.increment("chunks_buffered")
        return True

    def pop(self) -> Optional[Chunk]:
        if not self.queue:
            return None
        return self.queue.pop(0)

    def is_empty(self) -> bool:
        return len(self.queue) == 0
