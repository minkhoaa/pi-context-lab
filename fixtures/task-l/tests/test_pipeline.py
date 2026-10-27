import unittest
import os
from pipeline_engine.stream import DataStream, Chunk
from pipeline_engine.buffer import ChunkBuffer
from pipeline_engine.aggregator import StreamAggregator
from pipeline_engine.transformers import TransformPipeline
from pipeline_engine.metrics import MetricsTracker


class TestPipelineEngine(unittest.TestCase):
    def setUp(self):
        self.log_file = "test_pipeline.log"
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        self.metrics = MetricsTracker(log_path=self.log_file)

    def tearDown(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def test_stage1_stream_and_transform(self):
        """Test stream chunking and normalization."""
        data = [{"id": 1, "val": 10}, {"id": 2, "val": 20}]
        stream = DataStream(data, chunk_size=2)
        chunks = list(stream.generate_chunks())
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].sequence_id, 1)

        pipeline = TransformPipeline()
        transformed = pipeline.apply(chunks[0])
        self.assertEqual(transformed.data["items"][0]["val"], 10.0)

    def test_stage2_buffer_push_various_sizes(self):
        """Test buffer handling full and partial chunks."""
        buf = ChunkBuffer(capacity=5, metrics=self.metrics)
        c1 = Chunk(sequence_id=1, data={"items": [{"id": i} for i in range(5)], "count": 5}, batch_tag="b1")
        self.assertTrue(buf.push(c1))

        # Partial final chunk with 2 items
        c2 = Chunk(sequence_id=2, data={"items": [{"id": 10}, {"id": 11}], "count": 2}, batch_tag="b2", is_last=True)
        # Fails currently in buffer.py because count != 5
        self.assertTrue(buf.push(c2))

    def test_stage3_aggregator_out_of_order_backpressure(self):
        """Test aggregator handling chunks arriving out of order under backpressure."""
        agg = StreamAggregator(metrics=self.metrics)
        c1 = Chunk(sequence_id=1, data={"items": [{"id": 1}], "count": 1}, batch_tag="b1")
        c2 = Chunk(sequence_id=2, data={"items": [{"id": 2}], "count": 1}, batch_tag="b2")

        # Arrival: sequence 2 first, then sequence 1
        agg.ingest(c2)
        agg.ingest(c1)
        self.assertEqual(agg.total_items(), 2)


if __name__ == "__main__":
    unittest.main()
