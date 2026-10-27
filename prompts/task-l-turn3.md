# Task L - Turn 3: Diagnose Out-of-Order Backpressure Failure and Fix Aggregator

Continue working on `pipeline_engine` in `fixtures/task-l`.

### Objective
1. Run pipeline with simulated backpressure reordering:
   `python3 -m pipeline_engine.run --items 12 --backpressure`
2. Inspect the failure: out-of-order sequence arrival causes a `SequenceOrderError` and generates a massive trace log.
3. Update `pipeline_engine/aggregator.py` to buffer out-of-order chunks in `reorder_buffer` and sequentially drain them as missing sequences arrive.
4. Run `python3 -m pipeline_engine.run --items 12 --backpressure` and confirm it succeeds.
