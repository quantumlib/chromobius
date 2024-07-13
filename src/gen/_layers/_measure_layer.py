import dataclasses
from typing import Optional, Set

import stim

from gen._layers._data import R_ZYX, R_XYZ, R_XZY
from gen._layers._layer import Layer
from gen._layers._rotation_layer import RotationLayer


@dataclasses.dataclass
class MeasureLayer(Layer):
    targets: list[int] = dataclasses.field(default_factory=list)
    bases: list[str] = dataclasses.field(default_factory=list)

    def copy(self) -> "MeasureLayer":
        return MeasureLayer(targets=list(self.targets), bases=list(self.bases))

    def touched(self) -> set[int]:
        return set(self.targets)

    def to_z_basis(self) -> list["Layer"]:
        rot = RotationLayer(
            {
                q: R_XYZ if b == "Z" else R_ZYX if b == "X" else R_XZY
                for q, b in zip(self.targets, self.bases)
            }
        )
        return [
            rot,
            MeasureLayer(targets=list(self.targets), bases=["Z"] * len(self.targets)),
            rot.copy(),
        ]

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        for t, b in zip(self.targets, self.bases):
            out.append("M" + b, [t])

    def locally_optimized(self, next_layer: Layer | None) -> list[Layer | None]:
        if isinstance(next_layer, MeasureLayer) and set(self.targets).isdisjoint(
            next_layer.targets
        ):
            return [
                MeasureLayer(
                    targets=self.targets + next_layer.targets,
                    bases=self.bases + next_layer.bases,
                )
            ]
        if isinstance(next_layer, RotationLayer) and set(self.targets).isdisjoint(
                next_layer.rotations
        ):
            return [next_layer, self]
        return [self, next_layer]
