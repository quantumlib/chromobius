import functools
from typing import Iterable, Optional, Callable

from gen._core._tile import Tile


def test_basis():
    tile = Tile(bases="XYZX", measurement_qubit=0, ordered_data_qubits=(1, 2, None, 3))
    assert tile.basis is None

    tile = Tile(bases="XXZX", measurement_qubit=0, ordered_data_qubits=(1, 2, None, 3))
    assert tile.basis == "X"

    tile = Tile(bases="XXX", measurement_qubit=0, ordered_data_qubits=(1, 2, 3))
    assert tile.basis == "X"

    tile = Tile(bases="ZZZ", measurement_qubit=0, ordered_data_qubits=(1, 2, 3))
    assert tile.basis == "Z"

    tile = Tile(bases="ZXZ", measurement_qubit=0, ordered_data_qubits=(1, 2, 3))
    assert tile.basis == None
