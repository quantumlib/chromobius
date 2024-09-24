from typing import Optional

import stim


class Layer:
    def copy(self) -> "Layer":
        raise NotImplementedError()

    def touched(self) -> set[int]:
        raise NotImplementedError()

    def to_z_basis(self) -> list["Layer"]:
        return [self]

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        raise NotImplementedError()

    def locally_optimized(
        self, next_layer: Optional["Layer"]
    ) -> list[Optional["Layer"]]:
        return [self, next_layer]

    def is_vacuous(self) -> bool:
        return False

    def requires_tick_before(self) -> bool:
        return True

    def implies_eventual_tick_after(self) -> bool:
        return True
