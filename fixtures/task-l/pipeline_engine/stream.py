import dataclasses
from typing import Iterator, List, Dict, Any


@dataclasses.dataclass
class Chunk:
    sequence_id: int
    data: Dict[str, Any]
    batch_tag: str
    is_last: bool = False


class DataStream:
    def __init__(self, raw_items: List[Dict[str, Any]], chunk_size: int = 5):
        self.raw_items = raw_items
        self.chunk_size = chunk_size

    def generate_chunks(self) -> Iterator[Chunk]:
        """Yields chunks of data items."""
        total = len(self.raw_items)
        if total == 0:
            return

        seq = 0
        for i in range(0, total, self.chunk_size):
            slice_items = self.raw_items[i : i + self.chunk_size]
            seq += 1
            is_last = (i + self.chunk_size) >= total
            yield Chunk(
                sequence_id=seq,
                data={"items": slice_items, "count": len(slice_items)},
                batch_tag=f"batch-{seq}",
                is_last=is_last,
            )
