import dataclasses

import stim

from gen._layers._interact_layer import InteractLayer
from gen._layers._det_obs_annotation_layer import DetObsAnnotationLayer
from gen._layers._shift_coord_annotation_layer import ShiftCoordAnnotationLayer
from gen._layers._layer import Layer


@dataclasses.dataclass
class SwapLayer(Layer):
    targets1: list[int] = dataclasses.field(default_factory=list)
    targets2: list[int] = dataclasses.field(default_factory=list)

    def touched(self) -> set[int]:
        return set(self.targets1 + self.targets2)

    def to_swap_dict(self) -> dict[int, int]:
        d = {}
        for a, b in zip(self.targets1, self.targets2):
            d[a] = b
            d[b] = a
        return d

    def copy(self) -> "SwapLayer":
        return SwapLayer(targets1=list(self.targets1), targets2=list(self.targets2))

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        pairs = []
        for k in range(len(self.targets1)):
            t1 = self.targets1[k]
            t2 = self.targets2[k]
            t1, t2 = sorted([t1, t2])
            pairs.append((t1, t2))
        for pair in sorted(pairs):
            out.append("SWAP", pair)

    def locally_optimized(self, next_layer: Layer | None) -> list[Layer | None]:
        if isinstance(next_layer, InteractLayer):
            from gen._layers._interact_swap_layer import InteractSwapLayer

            i = next_layer.copy()
            i.targets1, i.targets2 = i.targets2, i.targets1
            return [InteractSwapLayer(i_layer=i, swap_layer=self.copy())]
        if isinstance(next_layer, (ShiftCoordAnnotationLayer, DetObsAnnotationLayer)):
            return [next_layer, self]
        if isinstance(next_layer, SwapLayer):
            total_swaps = self.to_swap_dict()
            leftover_swaps = SwapLayer()
            for a, b in zip(next_layer.targets1, next_layer.targets2):
                a2 = total_swaps.get(a)
                b2 = total_swaps.get(b)
                if a2 is None and b2 is None:
                    total_swaps[a] = b
                    total_swaps[b] = a
                elif a2 == b and b2 == a:
                    del total_swaps[a]
                    del total_swaps[b]
                else:
                    leftover_swaps.targets1.append(a)
                    leftover_swaps.targets2.append(b)
            result = []
            if total_swaps:
                new_layer = SwapLayer()
                for k, v in total_swaps.items():
                    if k < v:
                        new_layer.targets1.append(k)
                        new_layer.targets2.append(v)
                result.append(new_layer)
            if leftover_swaps.targets1:
                result.append(leftover_swaps)
            return result
        return [self, next_layer]
