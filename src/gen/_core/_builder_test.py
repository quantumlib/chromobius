import stim

import gen


def test_builder_init():
    builder = gen.Builder.for_qubits([0, 1j, 3 + 2j])
    assert builder.circuit == stim.Circuit(
        """
        QUBIT_COORDS(0, 0) 0
        QUBIT_COORDS(0, 1) 1
        QUBIT_COORDS(3, 2) 2
    """
    )
