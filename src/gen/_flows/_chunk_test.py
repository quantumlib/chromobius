import stim

import gen


def test_inverse_flows():
    chunk = gen.Chunk(
        circuit=stim.Circuit("""
            R 0 1 2 3 4
            CX 2 0
            M 0
        """),
        q2i={0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
        flows=[
            gen.Flow(
                center=0,
                start=gen.PauliString({}),
                measurement_indices=[0],
                end=gen.PauliString({1: "Z"}),
            ),
        ],
    )

    inverted = chunk.time_reversed()
    inverted.verify()
    assert len(inverted.flows) == len(chunk.flows)
    assert inverted.circuit == stim.Circuit(
        """
        R 0
        CX 2 0
        M 4 3 2 1 0
    """
    )


def test_inverse_circuit():
    chunk = gen.Chunk(
        circuit=stim.Circuit(
            """
            R 0 1 2 3 4
            CX 2 0 3 4
            X 1
            M 0
        """
        ),
        q2i={0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
        flows=[],
    )

    inverted = chunk.time_reversed()
    inverted.verify()
    assert len(inverted.flows) == len(chunk.flows)
    assert inverted.circuit == stim.Circuit(
        """
        M 0
        X 1
        CX 3 4 2 0
        M 4 3 2 1 0
    """
    )


def test_with_flows_postselected():
    chunk = gen.Chunk(
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
    assert chunk.with_flows_postselected(lambda f: False) == chunk
    assert chunk.with_flows_postselected(lambda f: True) != chunk
    assert chunk.with_flows_postselected(lambda f: f.center == 1) == chunk
    assert chunk.with_flows_postselected(lambda f: f.center == 0) == gen.Chunk(
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
            ).postselected()
        ],
    )


def test_reflow():
    xx = gen.PauliString({0: 'X', 1: 'X'})
    yy = gen.PauliString({0: 'Y', 1: 'Y'})
    zz = gen.PauliString({0: 'Z', 1: 'Z'})
    chunk1 = gen.Chunk(
        q2i={0: 0, 1: 1},
        circuit=stim.Circuit("""
            MPP X0*X1
            MPP Z0*Z1
        """),
        flows=[
            gen.Flow(
                end=xx,
                measurement_indices=[0],
                center=0,
            ),
            gen.Flow(
                end=zz,
                measurement_indices=[1],
                center=0,
            ),
        ],
    )
    chunk2 = gen.Chunk(
        q2i={0: 0, 1: 1},
        circuit=stim.Circuit("""
            MPP Y0*Y1
        """),
        flows=[
            gen.Flow(
                start=yy,
                measurement_indices=[0],
                center=0,
            ),
        ],
        discarded_inputs=[xx]
    )
    reflow = gen.ChunkReflow({yy: [xx, zz], xx: [xx]})
    chunk1.verify()
    chunk2.verify()
    reflow.verify()
    gen.compile_chunks_into_circuit([chunk1, reflow, chunk2])


def test_from_circuit_with_mpp_boundaries_simple():
    chunk = gen.Chunk.from_circuit_with_mpp_boundaries(stim.Circuit("""
        QUBIT_COORDS(1, 2) 0
        MPP X0
        H 0
        MPP Z0
        DETECTOR rec[-1] rec[-2]
    """))
    chunk.verify()
    assert chunk == gen.Chunk(
        q2i={1 + 2j: 0},
        flows=[
            gen.Flow(
                start=gen.PauliString(xs=[1 + 2j]),
                end=gen.PauliString(zs=[1 + 2j]),
                measurement_indices=(),
                obs_index=None,
                center=1 + 2j,
            )
        ],
        circuit=stim.Circuit("""
            H 0
        """),
    )

    chunk = gen.Chunk.from_circuit_with_mpp_boundaries(stim.Circuit("""
        QUBIT_COORDS(1, 2) 0
        MR 0
        MR 0
        DETECTOR rec[-1]
    """))
    chunk.verify()
    assert chunk == gen.Chunk(
        q2i={1 + 2j: 0},
        flows=[],
        circuit=stim.Circuit("""
            MR 0
            MR 0
            DETECTOR rec[-1]
        """),
    )

    chunk = gen.Chunk.from_circuit_with_mpp_boundaries(stim.Circuit("""
        QUBIT_COORDS(1, 2) 0
        QUBIT_COORDS(1, 3) 1
        MPP X0
        TICK
        CX 0 1
        TICK
        H 0
        MX 1
        TICK
        MPP Z0
        DETECTOR rec[-1] rec[-2] rec[-3]
    """))
    chunk.verify()
    assert chunk == gen.Chunk(
        q2i={1 + 2j: 0, 1 + 3j: 1},
        flows=[
            gen.Flow(
                start=gen.PauliString(xs=[1 + 2j]),
                end=gen.PauliString(zs=[1 + 2j]),
                measurement_indices=(0,),
                obs_index=None,
                center=1 + 2j,
            )
        ],
        circuit=stim.Circuit("""
            CX 0 1
            TICK
            H 0
            MX 1
        """),
    )

    chunk = gen.Chunk.from_circuit_with_mpp_boundaries(stim.Circuit("""
        QUBIT_COORDS(1, 2) 0
        QUBIT_COORDS(1, 3) 1
        MPP X0
        OBSERVABLE_INCLUDE(0) rec[-1]
        TICK
        CX 0 1
        TICK
        MX 1
        OBSERVABLE_INCLUDE(0) rec[-1]
        H 0
        TICK
        MPP Z0
        OBSERVABLE_INCLUDE(0) rec[-1]
    """))
    chunk.verify()
    assert chunk == gen.Chunk(
        q2i={1 + 2j: 0, 1 + 3j: 1},
        flows=[
            gen.Flow(
                start=gen.PauliString(xs=[1 + 2j]),
                end=gen.PauliString(zs=[1 + 2j]),
                measurement_indices=(0,),
                obs_index=0,
                center=1 + 2j,
            )
        ],
        circuit=stim.Circuit("""
            CX 0 1
            TICK
            MX 1
            H 0
        """),
    )


def test_from_circuit_with_mpp_boundaries_complex():
    chunk = gen.Chunk.from_circuit_with_mpp_boundaries(stim.Circuit("""
        QUBIT_COORDS(0, 0) 0
        QUBIT_COORDS(0, 1) 1
        QUBIT_COORDS(1, 0) 2
        QUBIT_COORDS(1, 1) 3
        QUBIT_COORDS(1, 2) 4
        QUBIT_COORDS(2, 0) 5
        QUBIT_COORDS(2, 1) 6
        QUBIT_COORDS(2, 2) 7
        QUBIT_COORDS(2, 3) 8
        QUBIT_COORDS(3, 0) 9
        QUBIT_COORDS(3, 1) 10
        QUBIT_COORDS(3, 2) 11
        QUBIT_COORDS(3, 3) 12
        QUBIT_COORDS(4, 0) 13
        QUBIT_COORDS(4, 1) 14
        QUBIT_COORDS(4, 2) 15
        QUBIT_COORDS(4, 3) 16
        QUBIT_COORDS(5, 3) 17
        #!pragma POLYGON(0,0,1,0.25) 11 15 9 6
        #!pragma POLYGON(0,1,0,0.25) 8 11 6 3
        #!pragma POLYGON(1,0,0,0.25) 8 17 15 11
        #!pragma POLYGON(1,0,0,0.25) 3 6 9 0
        TICK
        R 0 9 15 11 6 3 17 8 7 5 16 14
        RX 4 2 10 12
        TICK
        CX 4 7 2 5 12 16 10 14
        TICK
        CX 2 3 5 6 10 11 14 15 7 8
        TICK
        CX 2 0 10 6 12 8 7 11 5 9 16 17
        TICK
        CX 4 3 10 9 12 11 7 6 16 15
        TICK
        CX 4 7 2 5 10 14 12 16
        TICK
        M 7 5 16 14
        MX 4 2 10 12
        DETECTOR(2, 2, 0) rec[-8]
        DETECTOR(2, 0, 0) rec[-7]
        DETECTOR(4, 3, 0) rec[-6]
        DETECTOR(4, 1, 0) rec[-5]
        TICK
        R 7 5 16 14
        RX 4 2 10 12
        TICK
        CX 4 7 2 5 12 16 10 14
        TICK
        CX 2 3 5 6 10 11 14 15 7 8
        TICK
        CX 2 0 10 6 12 8 7 11 5 9 16 17
        TICK
        CX 4 3 10 9 12 11 7 6 16 15
        TICK
        CX 4 7 2 5 10 14 12 16
        TICK
        M 7 5 16 14
        MX 4 2 10 12
        MY 17
        DETECTOR(2, 2, 1) rec[-9]
        DETECTOR(2, 0, 1) rec[-8]
        DETECTOR(4, 3, 1) rec[-7]
        DETECTOR(4, 1, 1) rec[-6]
        DETECTOR(1, 2, 1) rec[-5] rec[-13]
        DETECTOR(1, 0, 1) rec[-4] rec[-12]
        DETECTOR(3, 1, 1) rec[-3] rec[-11]
        DETECTOR(3, 3, 1) rec[-2] rec[-10]
        TICK
        #!pragma POLYGON(0,0,1,0.25) 11 15 9 6
        #!pragma POLYGON(0,1,0,0.25) 8 11 6 3
        #!pragma POLYGON(1,0,0,0.25) 3 6 9 0
        #!pragma POLYGON(1,1,0,0.25) 9 13 11 6
        TICK
        R 13
        RX 14 10 5 2 7 1
        S 15 11 8 3 9 6 0
        TICK
        CX 14 15 1 0 10 9 7 8 5 6 2 3
        TICK
        CX 3 1 6 7 10 14
        TICK
        CX 6 3 10 11 15 14
        TICK
        CX 6 10 14 13
        TICK
        MX 6
        DETECTOR(3, 3, 2) rec[-1] rec[-2] rec[-7] rec[-8] rec[-10] rec[-11] rec[-13] rec[-15] rec[-16] rec[-18]
        TICK
        #!pragma POLYGON(0,0,1,0.25) 9 13 11 6
        #!pragma POLYGON(0,1,0,0.25) 8 11 6 3
        #!pragma POLYGON(1,0,0,0.25) 3 6 9 0
        #!pragma POLYGON(1,1,0,0.25) 11 15 9 6
        TICK
        RX 6
        TICK
        CX 6 10 15 14
        TICK
        CX 6 3 10 11 14 13
        TICK
        CX 3 1 6 7 10 14
        TICK
        CX 1 0 10 9 7 8 14 13 5 6 2 3
        TICK
        MX 14 10 5 2 7 1 15
        S 6 11 13 9 8 3 0
        DETECTOR(3, 1, 3) rec[-6]
        DETECTOR(1, 0, 3) rec[-4]
        DETECTOR(2, 2, 3) rec[-3]
        DETECTOR(0, 1, 3) rec[-2]
        DETECTOR(2, 1, 3) rec[-1] rec[-2] rec[-3] rec[-4] rec[-5] rec[-6] rec[-7] rec[-8]
        DETECTOR(4, 2, 3) rec[-1] rec[-7]
        TICK
        #!pragma POLYGON(0,0,1,0.25) 13 9 6 11
        #!pragma POLYGON(0,1,0,0.25) 8 11 6 3
        #!pragma POLYGON(1,0,0,0.25) 3 6 9 0
        TICK
        MPP X8*X11*X6*X3
        DETECTOR(1, 2, 4) rec[-1] rec[-6] rec[-14]
        TICK
        MPP X13*X9*X6*X11
        DETECTOR(3, 1, 5) rec[-1] rec[-3] rec[-7] rec[-13]
        TICK
        MPP X9*X0*X3*X6
        DETECTOR(1, 0, 6) rec[-1] rec[-8] rec[-15]
        TICK
        MPP Z8*Z11*Z6*Z3
        DETECTOR(2, 0, 7) rec[-1] rec[-20] rec[-21] rec[-28] rec[-29]
        TICK
        MPP Z9*Z0*Z3*Z6
        DETECTOR(2, 2, 8) rec[-1] rec[-22] rec[-30]
        TICK
        MPP Z13*Z9*Z6*Z11
        DETECTOR(4, 1, 9) rec[-1] rec[-20] rec[-21] rec[-28] rec[-29]
        TICK
        MPP Y13*Y9*Y0*Y6*Y3*Y8*Y11
        OBSERVABLE_INCLUDE(0) rec[-1] rec[-9] rec[-10] rec[-13] rec[-14]
    """))
    chunk.verify()
    assert len(chunk.flows) == 7
    assert all(not e.start for e in chunk.flows)
    assert chunk.circuit.num_detectors == 25 - 6
    assert chunk.circuit == stim.Circuit("""
        R 0 9 15 11 6 3 17 8 7 5 16 14
        RX 4 2 10 12
        TICK
        CX 4 7 2 5 12 16 10 14
        TICK
        CX 2 3 5 6 10 11 14 15 7 8
        TICK
        CX 2 0 10 6 12 8 7 11 5 9 16 17
        TICK
        CX 4 3 10 9 12 11 7 6 16 15
        TICK
        CX 4 7 2 5 10 14 12 16
        TICK
        M 7 5 16 14
        MX 4 2 10 12
        DETECTOR(2, 2, 0) rec[-8]
        DETECTOR(2, 0, 0) rec[-7]
        DETECTOR(4, 3, 0) rec[-6]
        DETECTOR(4, 1, 0) rec[-5]
        TICK
        R 7 5 16 14
        RX 4 2 10 12
        TICK
        CX 4 7 2 5 12 16 10 14
        TICK
        CX 2 3 5 6 10 11 14 15 7 8
        TICK
        CX 2 0 10 6 12 8 7 11 5 9 16 17
        TICK
        CX 4 3 10 9 12 11 7 6 16 15
        TICK
        CX 4 7 2 5 10 14 12 16
        TICK
        M 7 5 16 14
        MX 4 2 10 12
        MY 17
        DETECTOR(2, 2, 1) rec[-9]
        DETECTOR(2, 0, 1) rec[-8]
        DETECTOR(4, 3, 1) rec[-7]
        DETECTOR(4, 1, 1) rec[-6]
        DETECTOR(1, 2, 1) rec[-5] rec[-13]
        DETECTOR(1, 0, 1) rec[-4] rec[-12]
        DETECTOR(3, 1, 1) rec[-3] rec[-11]
        DETECTOR(3, 3, 1) rec[-2] rec[-10]
        TICK
        TICK
        R 13
        RX 14 10 5 2 7 1
        S 15 11 8 3 9 6 0
        TICK
        CX 14 15 1 0 10 9 7 8 5 6 2 3
        TICK
        CX 3 1 6 7 10 14
        TICK
        CX 6 3 10 11 15 14
        TICK
        CX 6 10 14 13
        TICK
        MX 6
        DETECTOR(3, 3, 2) rec[-1] rec[-2] rec[-7] rec[-8] rec[-10] rec[-11] rec[-13] rec[-15] rec[-16] rec[-18]
        TICK
        TICK
        RX 6
        TICK
        CX 6 10 15 14
        TICK
        CX 6 3 10 11 14 13
        TICK
        CX 3 1 6 7 10 14
        TICK
        CX 1 0 10 9 7 8 14 13 5 6 2 3
        TICK
        MX 14 10 5 2 7 1 15
        S 6 11 13 9 8 3 0
        DETECTOR(3, 1, 3) rec[-6]
        DETECTOR(1, 0, 3) rec[-4]
        DETECTOR(2, 2, 3) rec[-3]
        DETECTOR(0, 1, 3) rec[-2]
        DETECTOR(2, 1, 3) rec[-1] rec[-2] rec[-3] rec[-4] rec[-5] rec[-6] rec[-7] rec[-8]
        DETECTOR(4, 2, 3) rec[-1] rec[-7]
    """)
