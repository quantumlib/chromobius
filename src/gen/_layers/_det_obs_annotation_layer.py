# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dataclasses

import stim

from gen._layers._layer import Layer


@dataclasses.dataclass
class DetObsAnnotationLayer(Layer):
    circuit: stim.Circuit = dataclasses.field(default_factory=stim.Circuit)

    def with_rec_targets_shifted_by(self, shift: int) -> 'DetObsAnnotationLayer':
        result = DetObsAnnotationLayer()
        for inst in self.circuit:
            result.circuit.append(inst.name, [
                stim.target_rec(t.value + shift)
                for t in inst.targets_copy()
            ], inst.gate_args_copy())
        return result

    def copy(self) -> "DetObsAnnotationLayer":
        return DetObsAnnotationLayer(circuit=self.circuit.copy())

    def touched(self) -> set[int]:
        return set()

    def requires_tick_before(self) -> bool:
        return False

    def implies_eventual_tick_after(self) -> bool:
        return False

    def append_into_stim_circuit(self, out: stim.Circuit) -> None:
        out += self.circuit
