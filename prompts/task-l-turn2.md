# Task L - Turn 2: Implement Initial Repair in Buffer

Continue working on `pipeline_engine` in `fixtures/task-l`.

### Objective
1. Implement your repair in `pipeline_engine/buffer.py` to allow final chunks (`chunk.is_last == True`) or partial chunks where count <= expected_size to be accepted.
2. Verify that `test_stage2_buffer_push_various_sizes` in `tests/test_pipeline.py` passes.
3. Run `python3 -m pipeline_engine.run --items 12` to confirm the chunk mismatch error is resolved.
