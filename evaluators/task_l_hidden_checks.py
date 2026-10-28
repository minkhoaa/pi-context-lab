"""Immutable Task L checks executed from outside the worker workspace.

The runner sets PYTHONPATH to the copied candidate workspace. Workers cannot edit
this suite because the file is stored in the evaluator directory.
"""
import unittest
import tempfile
from pathlib import Path
from pipeline_engine.stream import Chunk, DataStream
from pipeline_engine.buffer import ChunkBuffer
from pipeline_engine.aggregator import StreamAggregator
from pipeline_engine.metrics import MetricsTracker


def chunk(seq, n, is_last=False):
    return Chunk(
        sequence_id=seq,
        data={"items": [{"id": i} for i in range(n)], "count": n},
        batch_tag=f"b{seq}",
        is_last=is_last,
    )


class HiddenTaskL(unittest.TestCase):
    # 1. Stream exact chunk generation
    def test_stream_exact(self):
        self.assertEqual(
            [(c.sequence_id, c.data["count"]) for c in DataStream([{"id": i} for i in range(12)], 5).generate_chunks()],
            [(1, 5), (2, 5), (3, 2)],
        )

    # 2. Partial final chunks
    def test_accept_final_partial(self):
        b = ChunkBuffer(capacity=5)
        self.assertTrue(b.push(chunk(1, 2, True)))
        self.assertEqual(len(b.queue), 1)

    def test_accept_final_partial_various_sizes(self):
        for n in (1, 3, 4):
            with self.subTest(n=n):
                b = ChunkBuffer(capacity=5)
                self.assertTrue(b.push(chunk(1, n, is_last=True)))
                self.assertEqual(len(b.queue), 1)

    def test_accept_full_chunk(self):
        self.assertTrue(ChunkBuffer().push(chunk(1, 5)))

    # 3. Oversized and inconsistent chunks
    def test_reject_oversized(self):
        b = ChunkBuffer()
        for size in (6, 10):
            with self.subTest(size=size):
                with self.assertRaises((ValueError, TypeError)):
                    b.push(chunk(1, size, is_last=True))

    def test_reject_negative_count(self):
        for n in (-1, -5):
            with self.subTest(n=n):
                with self.assertRaises((ValueError, TypeError)):
                    ChunkBuffer().push(chunk(1, n, True))

    def test_reject_non_integer_count(self):
        b = ChunkBuffer()
        bad = Chunk(sequence_id=1, data={"count": "5", "items": [{"id": 0}]}, batch_tag="bad", is_last=True)
        with self.assertRaises((ValueError, TypeError)):
            b.push(bad)

    def test_count_matches_payload(self):
        b = ChunkBuffer()
        # Count claims 3, but only 1 item
        bad1 = Chunk(sequence_id=1, data={"count": 3, "items": [{"id": 1}]}, batch_tag="bad", is_last=True)
        with self.assertRaises((ValueError, TypeError)):
            b.push(bad1)
        # Count claims 1, but 3 items
        bad2 = Chunk(sequence_id=2, data={"count": 1, "items": [{"id": 1}, {"id": 2}, {"id": 3}]}, batch_tag="bad", is_last=True)
        with self.assertRaises((ValueError, TypeError)):
            b.push(bad2)

    # 4. Buffer capacity
    def test_capacity(self):
        b = ChunkBuffer(capacity=1)
        self.assertTrue(b.push(chunk(1, 5)))
        self.assertFalse(b.push(chunk(2, 5)))
        self.assertEqual(len(b.queue), 1)

    def test_capacity_multistep(self):
        b = ChunkBuffer(capacity=2)
        self.assertTrue(b.push(chunk(1, 5)))
        self.assertTrue(b.push(chunk(2, 5)))
        self.assertFalse(b.push(chunk(3, 5)))
        p1 = b.pop()
        self.assertEqual(p1.sequence_id, 1)
        self.assertTrue(b.push(chunk(3, 5)))
        self.assertEqual([b.pop().sequence_id, b.pop().sequence_id], [2, 3])

    def test_pop_order(self):
        b = ChunkBuffer(capacity=4)
        b.push(chunk(1, 5))
        b.push(chunk(2, 3, True))
        self.assertEqual([b.pop().sequence_id, b.pop().sequence_id], [1, 2])
        self.assertIsNone(b.pop())

    # 5. Out-of-order aggregation
    def test_out_of_order(self):
        a = StreamAggregator()
        a.ingest(chunk(3, 1))
        a.ingest(chunk(1, 1))
        a.ingest(chunk(2, 1))
        self.assertEqual(a.total_items(), 3)
        self.assertEqual([x["id"] for x in a.collected_items], [0, 0, 0])

    def test_out_of_order_interleaved(self):
        a = StreamAggregator()
        for seq in (1, 4, 2, 5, 3):
            a.ingest(chunk(seq, 1))
        self.assertEqual(a.total_items(), 5)

    def test_no_premature_order(self):
        a = StreamAggregator()
        a.ingest(chunk(2, 1))
        self.assertEqual(a.total_items(), 0)
        a.ingest(chunk(1, 1))
        self.assertEqual(a.total_items(), 2)

    # 6. Duplicate sequences
    def test_duplicate_rejected_or_ignored(self):
        a = StreamAggregator()
        a.ingest(chunk(1, 1))
        try:
            a.ingest(chunk(1, 1))
        except (ValueError, RuntimeError):
            pass
        self.assertEqual(a.total_items(), 1)

    def test_duplicate_in_reorder_buffer(self):
        a = StreamAggregator()
        a.ingest(chunk(1, 1))
        a.ingest(chunk(3, 1))
        try:
            a.ingest(chunk(3, 1))
        except (ValueError, RuntimeError):
            pass
        a.ingest(chunk(2, 1))
        self.assertEqual(a.total_items(), 3)

    # 7. Backpressure execution
    def test_large_reverse_sequence(self):
        a = StreamAggregator()
        for n in range(16, 0, -1):
            a.ingest(chunk(n, 1))
        self.assertEqual(a.total_items(), 16)

    def test_backpressure_scrambled(self):
        a = StreamAggregator()
        order = [5, 2, 8, 1, 4, 7, 3, 6]
        for seq in order:
            a.ingest(chunk(seq, 1))
        self.assertEqual(a.total_items(), 8)

    # 8. Excessive debug logging
    def test_compact_logging(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "trace.log"
            m = MetricsTracker(log_path=str(p))
            m.dump_trace("test", {"error": "boom"})
            self.assertLess(p.stat().st_size, 50 * 1024)

    # 9. Adversarial / edge cases
    def test_empty_buffer_pop(self):
        b = ChunkBuffer()
        self.assertIsNone(b.pop())

    def test_empty_aggregator_total(self):
        a = StreamAggregator()
        self.assertEqual(a.total_items(), 0)

    def test_zero_count_handling(self):
        # Discrepancy documented: turn 2 prompt allows chunks where count <= expected_size.
        # Candidate either rejects count=0 with ValueError or accepts empty chunk cleanly without crashing.
        b = ChunkBuffer()
        try:
            result = b.push(chunk(1, 0, True))
            self.assertIn(result, (True, False))
        except (ValueError, TypeError):
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
