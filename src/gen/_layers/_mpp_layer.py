import dataclasses

import stim

from gen._layers._data import R_ZYX, R_XZY
from gen._layers._layer import Layer
from gen._layers._rotation_layer import RotationLayer


@dataclasses.dataclass
class MppLayer(Layer):
    targets: list[list[stim.GateTarget]] = dataclasses.field(default_factory=list)

    def copy(self) -> "MppLayer":
        return MppLayer(targets=[list(e) for e in self.targets])

    def touched(self) -> set[int]:
        return set(t.value for mpp in self.targets for t in mpp)

    def to_z_basis(self) -> list[Layer]:
        return [self]

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        flat_targets = []
        for group in self.targets:
            for t in group:
                flat_targets.append(t)
                flat_targets.append(stim.target_combiner())
            flat_targets.pop()
        out.append("MPP", flat_targets)
