from typing import Iterable, Union, TYPE_CHECKING

from gen._core import Patch

if TYPE_CHECKING:
    from gen._flows._chunk import Chunk


class ChunkLoop:
    def __init__(self, chunks: Iterable[Union['Chunk', 'ChunkLoop']], repetitions: int):
        self.chunks = tuple(chunks)
        self.repetitions = repetitions

    @property
    def magic(self) -> bool:
        return any(c.magic for c in self.chunks)

    def verify(self):
        for c in self.chunks:
            c.verify()
        for k in range(len(self.chunks)):
            before: Chunk = self.chunks[k - 1]
            after: Chunk = self.chunks[k]
            after_in = {}
            before_out = {}
            for flow in before.flows:
                if flow.end:
                    before_out[flow.end] = flow.obs_index
            for flow in after.flows:
                if flow.start:
                    after_in[flow.start] = flow.obs_index
            for ps in before.discarded_outputs:
                after_in.pop(ps)
            for ps in after.discarded_inputs:
                before_out.pop(ps)
            if after_in != before_out:
                raise ValueError("Flows don't match between chunks.")

    def __mul__(self, other: int) -> "ChunkLoop":
        return self.with_repetitions(other * self.repetitions)

    def with_repetitions(self, new_repetitions: int) -> "ChunkLoop":
        return ChunkLoop(chunks=self.chunks, repetitions=new_repetitions)

    def mpp_init_chunk(self) -> "Chunk":
        return self.chunks[0].mpp_init_chunk()

    def mpp_end_chunk(self) -> "Chunk":
        return self.chunks[-1].mpp_end_chunk()

    def start_patch(self) -> Patch:
        return self.chunks[0].start_patch()

    def end_patch(self) -> Patch:
        return self.chunks[-1].end_patch()

    def tick_count(self) -> int:
        return sum(e.tick_count() for e in self.chunks) * self.repetitions

    def flattened(self) -> list["Chunk"]:
        return [e for c in self.chunks for e in c.flattened()]
