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
from typing import Literal, Callable

from gen._core._pauli_string import PauliString


@dataclasses.dataclass(frozen=True)
class KeyedPauliString:
    key: int
    pauli_string: PauliString

    @property
    def qubits(self) -> dict[complex, Literal['X', 'Y', 'Z']]:
        return self.pauli_string.qubits

    def __lt__(self, other) -> bool:
        if isinstance(other, PauliString):
            return True
        if isinstance(other, KeyedPauliString):
            return (self.key, self.pauli_string) < (other.key, other.pauli_string)
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, PauliString):
            return False
        if isinstance(other, KeyedPauliString):
            return (self.key, self.pauli_string) > (other.key, other.pauli_string)
        return NotImplemented

    def with_transformed_coords(
        self, transform: Callable[[complex], complex]
    ) -> "KeyedPauliString":
        return KeyedPauliString(key=self.key, pauli_string=self.pauli_string.with_transformed_coords(transform))

    def __str__(self):
        return f'(key={self.key}) {self.pauli_string}'