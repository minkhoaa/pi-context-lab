from typing import List, Callable
from .stream import Chunk


class NormalizeTransform:
    def process(self, chunk: Chunk) -> Chunk:
        # Standardize values in chunk
        for item in chunk.data.get("items", []):
            if "val" in item and isinstance(item["val"], (int, float)):
                item["val"] = float(item["val"])
        return chunk


class TransformPipeline:
    def __init__(self):
        self.transforms: List[Callable[[Chunk], Chunk]] = [NormalizeTransform().process]

    def add_transform(self, fn: Callable[[Chunk], Chunk]):
        self.transforms.append(fn)

    def apply(self, chunk: Chunk) -> Chunk:
        curr = chunk
        for t in self.transforms:
            curr = t(curr)
        return curr
