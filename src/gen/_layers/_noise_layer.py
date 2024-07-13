import dataclasses

import stim

from gen._layers._layer import Layer


@dataclasses.dataclass
class NoiseLayer(Layer):
    circuit: stim.Circuit = dataclasses.field(default_factory=stim.Circuit)

    def copy(self) -> "NoiseLayer":
        return NoiseLayer(circuit=self.circuit.copy())

    def touched(self) -> set[int]:
        return {
            target.qubit_value
            for instruction in self.circuit
            for target in instruction.targets_copy()
        }

    def requires_tick_before(self) -> bool:
        return False

    def implies_eventual_tick_after(self) -> bool:
        return False

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        out += self.circuit
