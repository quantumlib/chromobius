import stim

import gen


def test_make_phenom_circuit_for_stabilizer_code():
    patch = gen.Patch(
        [
            gen.Tile(
                bases="Z",
                ordered_data_qubits=[0, 1, 1j, 1 + 1j],
                measurement_qubit=0.5 + 0.5j,
            ),
            gen.Tile(
                bases="X",
                ordered_data_qubits=[0, 1],
                measurement_qubit=0.5,
            ),
            gen.Tile(
                bases="X",
                ordered_data_qubits=[0 + 1j, 1 + 1j],
                measurement_qubit=0.5 + 1j,
            ),
        ]
    )
    obs_x = gen.PauliString({0: "X", 1j: "X"})
    obs_z = gen.PauliString({0: "Z", 1: "Z"})

    assert gen.StabilizerCode(
        patch=patch,
        observables_x=[obs_x],
        observables_z=[obs_z],
    ).make_phenom_circuit(
        noise=gen.NoiseRule(flip_result=0.125, after={"DEPOLARIZE1": 0.25}),
        rounds=100,
    ) == stim.Circuit("""
        QUBIT_COORDS(0, -1) 0
        QUBIT_COORDS(0, 0) 1
        QUBIT_COORDS(0, 1) 2
        QUBIT_COORDS(1, 0) 3
        QUBIT_COORDS(1, 1) 4
        MPP X0*X1*X2 Z0*Z1*Z3 X1*X3 Z1*Z2*Z3*Z4 X2*X4
        DEPOLARIZE1(0.25) 1 2 3 4
        OBSERVABLE_INCLUDE(0) rec[-5]
        OBSERVABLE_INCLUDE(1) rec[-4]
        TICK
        REPEAT 100 {
            MPP(0.125) X1*X3 Z1*Z2*Z3*Z4 X2*X4
            DEPOLARIZE1(0.25) 1 2 3 4
            DETECTOR(0.5, 0, 0) rec[-6] rec[-3]
            DETECTOR(0.5, 0.5, 0) rec[-5] rec[-2]
            DETECTOR(0.5, 1, 0) rec[-4] rec[-1]
            SHIFT_COORDS(0, 0, 1)
            TICK
        }
        MPP X0*X1*X2 Z0*Z1*Z3 X1*X3 Z1*Z2*Z3*Z4 X2*X4
        OBSERVABLE_INCLUDE(0) rec[-5]
        OBSERVABLE_INCLUDE(1) rec[-4]
        DETECTOR(0.5, 0, 0) rec[-8] rec[-3]
        DETECTOR(0.5, 0.5, 0) rec[-7] rec[-2]
        DETECTOR(0.5, 1, 0) rec[-6] rec[-1]
        SHIFT_COORDS(0, 0, 1)
        TICK
    """)


def test_make_code_capacity_circuit_for_stabilizer_code():
    patch = gen.Patch(
        [
            gen.Tile(
                bases="Z",
                ordered_data_qubits=[0, 1, 1j, 1 + 1j],
                measurement_qubit=0.5 + 0.5j,
            ),
            gen.Tile(
                bases="X",
                ordered_data_qubits=[0, 1],
                measurement_qubit=0.5,
            ),
            gen.Tile(
                bases="X",
                ordered_data_qubits=[0 + 1j, 1 + 1j],
                measurement_qubit=0.5 + 1j,
            ),
        ]
    )
    obs_x = gen.PauliString({0: "X", 1j: "X"})
    obs_z = gen.PauliString({0: "Z", 1: "Z"})

    assert gen.StabilizerCode(
        patch=patch,
        observables_x=[obs_x],
        observables_z=[obs_z],
    ).make_code_capacity_circuit(
        noise=gen.NoiseRule(after={"DEPOLARIZE1": 0.25}),
    ) == stim.Circuit("""
        QUBIT_COORDS(0, -1) 0
        QUBIT_COORDS(0, 0) 1
        QUBIT_COORDS(0, 1) 2
        QUBIT_COORDS(1, 0) 3
        QUBIT_COORDS(1, 1) 4
        MPP X0*X1*X2 Z0*Z1*Z3 X1*X3 Z1*Z2*Z3*Z4 X2*X4
        DEPOLARIZE1(0.25) 1 2 3 4
        OBSERVABLE_INCLUDE(0) rec[-5]
        OBSERVABLE_INCLUDE(1) rec[-4]
        TICK
        MPP X0*X1*X2 Z0*Z1*Z3 X1*X3 Z1*Z2*Z3*Z4 X2*X4
        OBSERVABLE_INCLUDE(0) rec[-5]
        OBSERVABLE_INCLUDE(1) rec[-4]
        DETECTOR(0.5, 0, 0) rec[-8] rec[-3]
        DETECTOR(0.5, 0.5, 0) rec[-7] rec[-2]
        DETECTOR(0.5, 1, 0) rec[-6] rec[-1]
        SHIFT_COORDS(0, 0, 1)
        TICK
    """)


def test_from_patch_with_inferred_observables():
    code = gen.StabilizerCode.from_patch_with_inferred_observables(
        gen.Patch(
            [
                gen.Tile(
                    bases="XZZX", ordered_data_qubits=[0, 1, 2, 3], measurement_qubit=0
                ),
                gen.Tile(
                    bases="XZZX", ordered_data_qubits=[1, 2, 3, 4], measurement_qubit=1
                ),
                gen.Tile(
                    bases="XZZX", ordered_data_qubits=[2, 3, 4, 0], measurement_qubit=2
                ),
                gen.Tile(
                    bases="XZZX", ordered_data_qubits=[3, 4, 0, 1], measurement_qubit=3
                ),
            ]
        )
    )
    code.verify()
    assert len(code.observables_x) == len(code.observables_z) == 1
