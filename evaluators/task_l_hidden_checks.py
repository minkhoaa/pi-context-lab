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
    return Chunk(sequence_id=seq, data={"items": [{"id": i} for i in range(n)], "count": n}, batch_tag=f"b{seq}", is_last=is_last)

class HiddenTaskL(unittest.TestCase):
    def test_stream_exact(self):
        self.assertEqual([(c.sequence_id, c.data["count"]) for c in DataStream([{"id":i} for i in range(12)],5).generate_chunks()],[(1,5),(2,5),(3,2)])
    def test_accept_final_partial(self):
        b=ChunkBuffer(capacity=5)
        self.assertTrue(b.push(chunk(1,2,True)))
        self.assertEqual(len(b.queue),1)
    def test_accept_full_chunk(self):
        self.assertTrue(ChunkBuffer().push(chunk(1,5)))
    def test_reject_oversized(self):
        b=ChunkBuffer()
        with self.assertRaises((ValueError,TypeError)):
            b.push(chunk(1,6,True))
    def test_reject_zero_or_negative_count(self):
        for n in (0,-1):
            with self.subTest(n=n):
                with self.assertRaises((ValueError,TypeError)):
                    ChunkBuffer().push(chunk(1,n,True))
    def test_count_matches_payload(self):
        b=ChunkBuffer()
        bad=Chunk(sequence_id=1,data={"count":3,"items":[{"id":1}]} ,batch_tag="bad",is_last=True)
        with self.assertRaises((ValueError,TypeError)):
            b.push(bad)
    def test_capacity(self):
        b=ChunkBuffer(capacity=1)
        self.assertTrue(b.push(chunk(1,5)))
        self.assertFalse(b.push(chunk(2,5)))
        self.assertEqual(len(b.queue),1)
    def test_pop_order(self):
        b=ChunkBuffer(capacity=4)
        b.push(chunk(1,5));b.push(chunk(2,3,True))
        self.assertEqual([b.pop().sequence_id,b.pop().sequence_id],[1,2])
        self.assertIsNone(b.pop())
    def test_out_of_order(self):
        a=StreamAggregator()
        a.ingest(chunk(3,1));a.ingest(chunk(1,1));a.ingest(chunk(2,1))
        self.assertEqual(a.total_items(),3)
        self.assertEqual([x["id"] for x in a.collected_items],[0,0,0])
    def test_no_premature_order(self):
        a=StreamAggregator()
        a.ingest(chunk(2,1))
        self.assertEqual(a.total_items(),0)
        a.ingest(chunk(1,1))
        self.assertEqual(a.total_items(),2)
    def test_duplicate_rejected_or_ignored(self):
        a=StreamAggregator()
        a.ingest(chunk(1,1))
        try:
            a.ingest(chunk(1,1))
        except (ValueError,RuntimeError):
            pass
        self.assertEqual(a.total_items(),1)
    def test_large_reverse_sequence(self):
        a=StreamAggregator()
        for n in range(16,0,-1):
            a.ingest(chunk(n,1))
        self.assertEqual(a.total_items(),16)
    def test_compact_logging(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"trace.log"
            m=MetricsTracker(log_path=str(p))
            m.dump_trace("test",{"error":"boom"})
            self.assertLess(p.stat().st_size,50*1024)

if __name__=="__main__":
    unittest.main(verbosity=2)
