import stim

import gen
from gen._flows._flow_util import solve_flow_auto_measurements


def test_magic_init_for_chunk():
    chunk = gen.Chunk(
        circuit=stim.Circuit(),
        q2i={0: 0, 1j: 1, 2j: 2},
        flows=[
            gen.Flow(
                center=0,
                start=gen.PauliString({0: "X", 1j: "Y", 2j: "Z"}),
            ),
            gen.Flow(
                center=0,
                start=gen.PauliString({0: "Y", 1j: "X", 2j: "Z"}),
                obs_index=1,
            ),
        ],
    )
    c2 = chunk.mpp_init_chunk()
    c2.verify()


def test_compile_postselected_chunks():
    chunk1 = gen.Chunk(
        circuit=stim.Circuit(
            """
            R 0
        """
        ),
        q2i={0: 0},
        flows=[
            gen.Flow(
                center=0,
                end=gen.PauliString({0: "Z"}),
            )
        ],
    )
    chunk2 = gen.Chunk(
        circuit=stim.Circuit(
            """
            M 0
        """
        ),
        q2i={0: 0},
        flows=[
            gen.Flow(
                center=0,
                end=gen.PauliString({0: "Z"}),
                measurement_indices=[0],
            ),
            gen.Flow(
                center=0,
                start=gen.PauliString({0: "Z"}),
                measurement_indices=[0],
            ),
        ],
    )
    chunk3 = gen.Chunk(
        circuit=stim.Circuit(
            """
            MR 0
        """
        ),
        q2i={0: 0},
        flows=[
            gen.Flow(
                center=0,
                start=gen.PauliString({0: "Z"}),
                measurement_indices=[0],
            )
        ],
    )

    assert gen.compile_chunks_into_circuit(
        [
            chunk1,
            chunk2,
            chunk3,
        ]
    ).flattened() == stim.Circuit(
        """
        QUBIT_COORDS(0, 0) 0
        R 0
        TICK
        M 0
        DETECTOR(0, 0, 0) rec[-1]
        TICK
        MR 0
        DETECTOR(0, 0, 1) rec[-2] rec[-1]
        TICK
    """
    )

    assert gen.compile_chunks_into_circuit(
        [
            chunk1.with_flows_postselected(lambda f: True),
            chunk2,
            chunk3,
        ]
    ).flattened() == stim.Circuit(
        """
        QUBIT_COORDS(0, 0) 0
        R 0
        TICK
        M 0
        DETECTOR(0, 0, 0, 999) rec[-1]
        TICK
        MR 0
        DETECTOR(0, 0, 1) rec[-2] rec[-1]
        TICK
    """
    )

    assert gen.compile_chunks_into_circuit(
        [
            chunk1,
            chunk2.with_flows_postselected(lambda f: True),
            chunk3,
        ]
    ).flattened() == stim.Circuit(
        """
        QUBIT_COORDS(0, 0) 0
        R 0
        TICK
        M 0
        DETECTOR(0, 0, 0, 999) rec[-1]
        TICK
        MR 0
        DETECTOR(0, 0, 1, 999) rec[-2] rec[-1]
        TICK
    """
    )

    assert gen.compile_chunks_into_circuit(
        [
            chunk1,
            chunk2,
            chunk3.with_flows_postselected(lambda f: True),
        ]
    ).flattened() == stim.Circuit(
        """
        QUBIT_COORDS(0, 0) 0
        R 0
        TICK
        M 0
        DETECTOR(0, 0, 0) rec[-1]
        TICK
        MR 0
        DETECTOR(0, 0, 1, 999) rec[-2] rec[-1]
        TICK
    """
    )

    assert gen.compile_chunks_into_circuit(
        [
            chunk1,
            chunk2.with_flows_postselected(lambda f: f.start),
            chunk3,
        ]
    ).flattened() == stim.Circuit(
        """
        QUBIT_COORDS(0, 0) 0
        R 0
        TICK
        M 0
        DETECTOR(0, 0, 0, 999) rec[-1]
        TICK
        MR 0
        DETECTOR(0, 0, 1) rec[-2] rec[-1]
        TICK
    """
    )


def test_solve_flow_auto_measurements():
    assert solve_flow_auto_measurements(
        flows=[gen.Flow(start=gen.PauliString({'Z': [0 + 1j, 2 + 1j]}), measurement_indices='auto', center=-1, flags={'X'})],
        circuit=stim.Circuit("""
            R 1
            CX 0 1 2 1
            M 1
        """),
        q2i={0 + 1j: 0, 1 + 1j: 1, 2 + 1j: 2},
    ) == (
        gen.Flow(start=gen.PauliString({'Z': [0 + 1j, 2 + 1j]}), measurement_indices=[0], center=-1, flags={'X'}),
    )
