from gen._flows._flow import Flow
from gen._core._pauli_string import PauliString


def test_with_xz_flipped():
    assert Flow(
        start=PauliString({1: "X", 2: "Z"}),
        center=0,
    ).with_xz_flipped() == Flow(
        start=PauliString({1: "Z", 2: "X"}),
        center=0,
    )
