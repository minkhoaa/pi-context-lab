import sys
import argparse
from pipeline_engine.stream import DataStream
from pipeline_engine.transformers import TransformPipeline
from pipeline_engine.buffer import ChunkBuffer
from pipeline_engine.aggregator import StreamAggregator
from pipeline_engine.metrics import MetricsTracker


def run_pipeline(item_count: int = 12, simulate_backpressure: bool = False, log_file: str = "pipeline_debug.log"):
    """Runs data pipeline over item_count items."""
    metrics = MetricsTracker(log_path=log_file)
    raw_data = [{"id": i, "val": i * 10} for i in range(item_count)]

    stream = DataStream(raw_data, chunk_size=5)
    pipeline = TransformPipeline()
    buffer = ChunkBuffer(capacity=10, metrics=metrics)
    aggregator = StreamAggregator(metrics=metrics)

    print(f"Starting pipeline processing for {item_count} items...")
    # Step 1: Stream to Buffer
    chunks = list(stream.generate_chunks())
    for chunk in chunks:
        transformed = pipeline.apply(chunk)
        buffer.push(transformed)

    # Step 2: Buffer to Aggregator
    buffered_chunks = []
    while not buffer.is_empty():
        c = buffer.pop()
        if c:
            buffered_chunks.append(c)

    if simulate_backpressure and len(buffered_chunks) >= 2:
        # Simulate backpressure reordering where chunk 2 arrives before chunk 1
        buffered_chunks[0], buffered_chunks[1] = buffered_chunks[1], buffered_chunks[0]

    for c in buffered_chunks:
        aggregator.ingest(c)

    print(f"Pipeline completed successfully. Total aggregated items: {aggregator.total_items()}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Pipeline Engine Runner")
    parser.add_argument("--items", type=int, default=12, help="Number of items to process")
    parser.add_argument("--backpressure", action="store_true", help="Simulate backpressure out-of-order delivery")
    parser.add_argument("--log", type=str, default="pipeline_debug.log", help="Log output path")
    args = parser.parse_args()

    try:
        run_pipeline(item_count=args.items, simulate_backpressure=args.backpressure, log_file=args.log)
    except Exception as e:
        print(f"Pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
