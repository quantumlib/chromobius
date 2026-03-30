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

from typing import Callable
from typing import Iterable
from typing import Literal, List
from functools import partial

import stim

import gen
from clorco.color_code._superdense_planar_color_code_circuits import (
    make_color_code_layout_for_superdense,
)
from gen._core._stabilizer_code import StabilizerCode


def builder_do_cxs(
    builder: gen.Builder,
    code: StabilizerCode,
    centers: Iterable[complex],
    d_control: complex,
    d_target: complex,
    inv: Callable[[complex], bool] = lambda _: False,
) -> None:
    builder.append(
        "CX",
        [
            (c + d_control, c + d_target)[:: -1 if inv(c) else +1]
            for c in centers
            if c + d_control in code.patch.used_set
            if c + d_target in code.patch.used_set
        ],
    )


def make_bell_flagged_color_code_circuit_z_first_half_round_chunk(
    *,
    initialize: bool,
    basis: Literal["X", "Z"],
    base_data_width: int,
) -> gen.Chunk:
    code = make_color_code_layout_for_superdense(
        base_data_width=base_data_width,
    )

    x_ms = [tile.measurement_qubit for tile in code.patch.tiles if tile.basis == "X"]
    z_ms = [tile.measurement_qubit for tile in code.patch.tiles if tile.basis == "Z"]

    builder = gen.Builder.for_qubits(code.patch.used_set)

    do_cxs = partial(builder_do_cxs, builder, code)

    def mf(*qs):
        return builder.lookup_recs(q for q in qs if q in code.patch.measure_set)

    # Construct the first half of the cycle, responsible for the Z checks
    builder.append("RX", x_ms)
    if initialize:
        builder.append(f"R{basis}", code.patch.data_set)
    builder.append("RZ", z_ms)
    builder.tick()

    do_cxs(x_ms, +0, +1)
    builder.tick()
    do_cxs(x_ms, +1j, +0)
    do_cxs(z_ms, +1j, +0)
    builder.tick()
    do_cxs(x_ms, -1, +0)
    do_cxs(z_ms, +1, +0)
    builder.tick()
    do_cxs(x_ms, -1j, +0)
    do_cxs(z_ms, -1j, +0)
    builder.tick()
    do_cxs(x_ms, +0, +1)
    builder.tick()

    builder.append("MX", x_ms)
    builder.append("MZ", z_ms)

    flows = []
    for tile in code.patch.tiles:
        m = tile.measurement_qubit
        if tile.basis == "X":
            # This flow is just for the flag qubit
            # It starts and ends on the X ancilla
            flows.append(
                gen.Flow(
                    measurement_indices=mf(m),
                    center=m,
                    flags=tile.flags | frozenset({"is_flag=True"}),
                )
            )
            if not initialize:
                flows.append(
                    gen.Flow(
                        start=tile.to_data_pauli_string(),
                        end=tile.to_data_pauli_string(),
                        center=m,
                        flags=tile.flags,
                    )
                )
            elif basis == "X":
                flows.append(
                    gen.Flow(
                        end=tile.to_data_pauli_string(),
                        center=m,
                        flags=tile.flags,
                    )
                )

        elif tile.basis == "Z":
            if not initialize:
                flows.append(
                    gen.Flow(
                        start=tile.to_data_pauli_string(),
                        measurement_indices=mf(m),
                        center=m,
                        flags=tile.flags,
                    )
                )
            elif basis == "Z":
                flows.append(
                    gen.Flow(
                        measurement_indices=mf(m),
                        center=m,
                        flags=tile.flags,
                    )
                )
            flows.append(
                gen.Flow(
                    end=tile.to_data_pauli_string(),
                    measurement_indices=mf(m),
                    center=m,
                    flags=tile.flags,
                )
            )

    (obs_x,) = code.observables_x
    (obs_z,) = code.observables_z
    if basis == "X":
        flows.append(
            gen.Flow(
                start=None if initialize else obs_x,
                end=obs_x,
                measurement_indices=[],
                center=-1 - 1j,
                obs_index=0,
            )
        )
    elif basis == "Z":
        flows.append(
            gen.Flow(
                start=None if initialize else obs_z,
                end=obs_z,
                measurement_indices=[],
                center=-1 - 1j,
                obs_index=0,
            )
        )
    return gen.Chunk(
        circuit=builder.circuit,
        flows=flows,
        q2i=builder.q2i,
    )


def make_bell_flagged_color_code_circuit_x_second_half_round_chunk(
    *,
    initialize: bool,
    basis: Literal["X", "Z"],
    base_data_width: int,
) -> gen.Chunk:
    code = make_color_code_layout_for_superdense(
        base_data_width=base_data_width,
    )

    x_ms = [tile.measurement_qubit for tile in code.patch.tiles if tile.basis == "X"]
    z_ms = [tile.measurement_qubit for tile in code.patch.tiles if tile.basis == "Z"]

    builder = gen.Builder.for_qubits(code.patch.used_set)

    do_cxs = partial(builder_do_cxs, builder, code)

    def mf(*qs):
        return builder.lookup_recs(q for q in qs if q in code.patch.measure_set)

    # Construct the second half of the cycle, responsible for the X checks
    builder.append("RX", x_ms)
    builder.append("RZ", z_ms)
    builder.tick()
    do_cxs(x_ms, +0, +1)
    builder.tick()
    do_cxs(x_ms, +0, +1j)
    do_cxs(z_ms, +0, +1j)
    builder.tick()
    do_cxs(x_ms, +0, -1)
    do_cxs(z_ms, +0, +1)
    builder.tick()
    do_cxs(x_ms, +0, -1j)
    do_cxs(z_ms, +0, -1j)
    builder.tick()
    do_cxs(x_ms, +0, +1)
    builder.tick()
    builder.append("MX", x_ms)
    builder.append("MZ", z_ms)

    flows = []
    for tile in code.patch.tiles:
        m = tile.measurement_qubit
        if tile.basis == "X":
            if not initialize or basis == "X":
                flows.append(
                    gen.Flow(
                        start=tile.to_data_pauli_string(),
                        measurement_indices=mf(m),
                        center=m,
                        flags=tile.flags,
                    )
                )
            flows.append(
                gen.Flow(
                    end=tile.to_data_pauli_string(),
                    measurement_indices=mf(m),
                    center=m,
                    flags=tile.flags,
                )
            )
        elif tile.basis == "Z":
            # First flow is for the flag qubit
            flows.append(
                gen.Flow(
                    measurement_indices=mf(m),
                    center=m,
                    flags=tile.flags | frozenset({"is_flag=True"}),
                )
            )
            flows.append(
                gen.Flow(
                    start=tile.to_data_pauli_string(),
                    end=tile.to_data_pauli_string(),
                    measurement_indices=[],
                    center=m,
                    flags=tile.flags,
                )
            )

    (obs_x,) = code.observables_x
    (obs_z,) = code.observables_z
    if basis == "X":
        flows.append(
            gen.Flow(
                start=obs_x,
                end=obs_x,
                measurement_indices=[],
                center=-1 - 1j,
                obs_index=0,
            )
        )
    elif basis == "Z":
        flows.append(
            gen.Flow(
                start=obs_z,
                end=obs_z,
                measurement_indices=[],
                center=-1 - 1j,
                obs_index=0,
            )
        )
    return gen.Chunk(
        circuit=builder.circuit,
        flows=flows,
        q2i=builder.q2i,
    )


def make_bell_flagged_color_code_circuit_round_chunks(
    *,
    initialize: bool,
    basis: Literal["X", "Z"],
    base_data_width: int,
) -> List[gen.Chunk]:
    z_chunk = make_bell_flagged_color_code_circuit_z_first_half_round_chunk(
        initialize=initialize, basis=basis, base_data_width=base_data_width
    )

    x_chunk = make_bell_flagged_color_code_circuit_x_second_half_round_chunk(
        initialize=initialize, basis=basis, base_data_width=base_data_width
    )

    return [z_chunk, x_chunk]


def f2c(flow: gen.Flow) -> list[float]:
    c = 0
    if "color=r" in flow.flags:
        c += 0
    elif "color=g" in flow.flags:
        c += 1
    elif "color=b" in flow.flags:
        c += 2
    else:
        raise NotImplementedError(f"{flow=}")

    if "is_flag=True" in flow.flags:
        if "basis=X" in flow.flags:
            c += 9
        elif "basis=Z" in flow.flags:
            c += 6
        else:
            raise NotImplementedError(f"{flow=}")
    else:
        if "basis=X" in flow.flags:
            c += 0
        elif "basis=Z" in flow.flags:
            c += 3
        else:
            raise NotImplementedError(f"{flow=}")
    return [c]


def make_bell_flagged_color_code_circuit(
    *,
    base_data_width: int,
    basis: Literal["X", "Z"],
    rounds: int,
) -> stim.Circuit:
    assert rounds >= 2

    first_round_chunks = make_bell_flagged_color_code_circuit_round_chunks(
        initialize=True,
        basis=basis,
        base_data_width=base_data_width,
    )
    mid_round_chunks = make_bell_flagged_color_code_circuit_round_chunks(
        initialize=False,
        basis=basis,
        base_data_width=base_data_width,
    )
    end_round_chunks = [
        first_round_chunks[1].time_reversed(),
        first_round_chunks[0].time_reversed(),
    ]

    return gen.compile_chunks_into_circuit(
        [
            *first_round_chunks,
            gen.ChunkLoop(mid_round_chunks, repetitions=rounds - 2),
            *end_round_chunks,
        ],
        flow_to_extra_coords_func=f2c,
    )
