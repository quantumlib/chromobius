import dataclasses
from typing import TYPE_CHECKING, Literal

import stim

from gen._layers._data import INVERSE_PERMUTATIONS
from gen._layers._layer import Layer

if TYPE_CHECKING:
    from gen._layers._rotation_layer import RotationLayer


@dataclasses.dataclass
class FeedbackLayer(Layer):
    controls: list[stim.GateTarget] = dataclasses.field(default_factory=list)
    targets: list[int] = dataclasses.field(default_factory=list)
    bases: list[Literal["X", "Y", "Z"]] = dataclasses.field(default_factory=list)

    def with_rec_targets_shifted_by(self, shift: int) -> 'FeedbackLayer':
        result = self.copy()
        result.controls = [stim.target_rec(t.value + shift) for t in result.controls]
        return result

    def copy(self) -> "FeedbackLayer":
        return FeedbackLayer(
            targets=list(self.targets),
            controls=list(self.controls),
            bases=list(self.bases),
        )

    def touched(self) -> set[int]:
        return set(self.targets)

    def requires_tick_before(self) -> bool:
        return False

    def implies_eventual_tick_after(self) -> bool:
        return False

    def before(self, layer: "RotationLayer") -> "FeedbackLayer":
        return FeedbackLayer(
            controls=list(self.controls),
            targets=list(self.targets),
            bases=[
                _basis_before_rotation(b, layer.rotations.get(t, 0))
                for b, t in zip(self.bases, self.targets)
            ],
        )

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        for c, t, b in zip(self.controls, self.targets, self.bases):
            out.append("C" + b, [c, t])


def _basis_before_rotation(
    basis: Literal["X", "Y", "Z"], rotation: int
) -> Literal["X", "Y", "Z"]:
    return INVERSE_PERMUTATIONS[rotation][basis]
