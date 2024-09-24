import collections
import dataclasses
from typing import Union, Any, Literal, Iterable, Callable

import stim

import gen
from gen._core import KeyedPauliString, MeasurementTracker, Builder, AtLayer, sorted_complex
from gen._flows._chunk import Chunk
from gen._flows._chunk_loop import ChunkLoop
from gen._flows._chunk_reflow import ChunkReflow
from gen._flows._flow import PauliString, Flow


def magic_init_for_chunk(
    chunk: Chunk,
    *,
    single_kept_obs_basis: str | None = None,
) -> Chunk:
    builder = Builder(
        q2i=chunk.q2i,
        circuit=stim.Circuit(),
        tracker=MeasurementTracker(),
    )
    index = 0
    flows = []
    discards = []
    for flow in chunk.flows:
        if flow.start:
            if flow.obs_index is not None and single_kept_obs_basis is not None and set(flow.start.qubits.values()) != set(single_kept_obs_basis):
                discards.append((flow.start, flow.obs_index))
            else:
                builder.measure_pauli_string(flow.start, key=AtLayer(index, "solo"))
                flows.append(
                    Flow(
                        center=flow.center,
                        end=flow.start,
                        measurement_indices=[index],
                        obs_index=flow.obs_index,
                        flags=flow.flags,
                    )
                )
                index += 1

    return Chunk(
        circuit=builder.circuit,
        q2i=builder.q2i,
        flows=flows,
        discarded_outputs=discards,
    )


def magic_measure_for_chunk(
    chunk: Chunk,
    *,
    single_kept_obs_basis: str | None = None,
) -> Chunk:
    return magic_measure_for_flows(chunk.flows, single_kept_obs_basis=single_kept_obs_basis)


def magic_measure_for_flows(
    flows: list[Flow],
    *,
    single_kept_obs_basis: str | None = None,
) -> Chunk:
    all_qubits = sorted_complex({q for flow in flows for q in (flow.end.qubits or [])})
    q2i = {q: i for i, q in enumerate(all_qubits)}
    builder = Builder(
        q2i=q2i,
        circuit=stim.Circuit(),
        tracker=MeasurementTracker(),
    )
    index = 0
    out_flows = []
    discards = []
    for flow in flows:
        if flow.end:
            if flow.obs_index is not None and single_kept_obs_basis is not None and set(flow.end.qubits.values()) != set(single_kept_obs_basis):
                discards.append((flow.start, flow.obs_index))
            else:
                key = AtLayer(index, "solo")
                builder.measure_pauli_string(flow.end, key=key)
                out_flows.append(
                    Flow(
                        center=flow.center,
                        start=flow.end,
                        measurement_indices=[index],
                        obs_index=flow.obs_index,
                        flags=flow.flags,
                    )
                )
                index += 1

    return Chunk(
        circuit=builder.circuit,
        q2i=builder.q2i,
        flows=out_flows,
        discarded_inputs=discards,
    )


def _append_circuit_with_reindexed_qubits_to_circuit(
    *,
    circuit: stim.Circuit,
    old_q2i: dict[complex, int],
    new_q2i: dict[complex, int],
    out: stim.Circuit,
) -> None:
    i2i = {i: new_q2i[q] for q, i in old_q2i.items()}

    for inst in circuit:
        if isinstance(inst, stim.CircuitRepeatBlock):
            block = stim.Circuit()
            _append_circuit_with_reindexed_qubits_to_circuit(
                circuit=inst.body_copy(),
                old_q2i=old_q2i,
                new_q2i=new_q2i,
                out=block,
            )
            out.append(
                stim.CircuitRepeatBlock(repeat_count=inst.repeat_count, body=block)
            )
        elif isinstance(inst, stim.CircuitInstruction):
            if inst.name == "QUBIT_COORDS":
                continue
            targets = []
            for t in inst.targets_copy():
                if t.is_qubit_target:
                    targets.append(i2i[t.value])
                elif t.is_x_target:
                    targets.append(stim.target_x(i2i[t.value]))
                elif t.is_y_target:
                    targets.append(stim.target_y(i2i[t.value]))
                elif t.is_z_target:
                    targets.append(stim.target_z(i2i[t.value]))
                elif t.is_combiner:
                    targets.append(t)
                elif t.is_measurement_record_target:
                    targets.append(t)
                else:
                    raise NotImplementedError(f"{inst=}")
            out.append(inst.name, targets, inst.gate_args_copy())
        else:
            raise NotImplementedError(f"{inst=}")


class _ChunkCompileState:
    def __init__(
        self,
        *,
        open_flows: dict[PauliString | KeyedPauliString, Union[Flow, Literal["discard"]]],
        measure_offset: int,
    ):
        self.open_flows = open_flows
        self.measure_offset = measure_offset

    def verify(self):
        for (k1, k2), v in self.open_flows.items():
            assert isinstance(k1, (PauliString, KeyedPauliString))
            assert v == "discard" or isinstance(v, Flow)

    def __str__(self) -> str:
        lines = []
        lines.append("_ChunkCompileState {")

        lines.append("    discard_flows {")
        for key, flow in self.open_flows.items():
            if flow == "discard":
                lines.append(f"        {key}")
        lines.append("    }")

        lines.append("    det_flows {")
        for key, flow in self.open_flows.items():
            if flow != "discard" and flow.obs_index is None:
                lines.append(f"        {flow.end}, ms={flow.measurement_indices}")
        lines.append("    }")

        lines.append("    obs_flows {")
        for key, flow in self.open_flows.items():
            if flow != "discard" and flow.obs_index is not None:
                lines.append(f"        {flow.end}: ms={flow.measurement_indices}")
        lines.append("    }")

        lines.append(f"    measure_offset = {self.measure_offset}")
        lines.append("}")
        return '\n'.join(lines)


def _compile_chunk_reflow_into_circuit(
    *,
    chunk_reflow: ChunkReflow,
    state: _ChunkCompileState,
) -> _ChunkCompileState:
    next_flows: dict[PauliString | KeyedPauliString, Union[Flow, Literal["discard"]]] = {}
    for output, inputs in chunk_reflow.out2in.items():
        measurements = set()
        centers = []
        flags = set()
        discarded = False
        for inp_key in inputs:
            if inp_key not in state.open_flows:
                msg = []
                msg.append(f"Missing reflow input: {inp_key=}")
                msg.append("Needed inputs {")
                for ps in inputs:
                    msg.append(f"    {ps}")
                msg.append("}")
                msg.append("Actual inputs {")
                for ps in state.open_flows.keys():
                    msg.append(f"    {ps}")
                msg.append("}")
                raise ValueError('\n'.join(msg))
            inp = state.open_flows[inp_key]
            if inp == 'discard':
                discarded = True
            else:
                assert isinstance(inp, Flow)
                assert not inp.start
                measurements ^= frozenset(inp.measurement_indices)
                centers.append(inp.center)
                flags |= inp.flags
        next_flows[output] = 'discard' if discarded else gen.Flow(
            start=None,
            end=output.pauli_string if isinstance(output, KeyedPauliString) else output,
            measurement_indices=tuple(sorted(measurements)),
            obs_index=output.key if isinstance(output, KeyedPauliString) else None,
            flags=flags,
            center=sum(centers) / len(centers),
        )
    for k, v in state.open_flows.items():
        if k in chunk_reflow.removed_inputs:
            continue
        assert k not in next_flows
        next_flows[k] = v

    return _ChunkCompileState(
        measure_offset=state.measure_offset,
        open_flows=next_flows,
    )


def _compile_chunk_into_circuit_many_repetitions(
    *,
    chunk_loop: ChunkLoop,
    state: _ChunkCompileState,
    include_detectors: bool,
    ignore_errors: bool,
    out_circuit: stim.Circuit,
    q2i: dict[complex, int],
    flow_to_extra_coords_func: Callable[[Flow], Iterable[float]],
) -> _ChunkCompileState:
    if chunk_loop.repetitions == 0:
        return state
    if chunk_loop.repetitions == 1:
        return _compile_chunk_into_circuit_sequence(
            chunks=chunk_loop.chunks,
            state=state,
            include_detectors=include_detectors,
            ignore_errors=ignore_errors,
            out_circuit=out_circuit,
            q2i=q2i,
            flow_to_extra_coords_func=flow_to_extra_coords_func,
        )
    assert chunk_loop.repetitions > 1

    no_reps_loop = chunk_loop.with_repetitions(1)
    circuits = []
    measure_offset_start_of_loop = state.measure_offset
    while len(circuits) < chunk_loop.repetitions:
        fully_in_loop = (
            len(circuits) > 0
            and min(
                [
                    m
                    for flow in state.open_flows.values()
                    if isinstance(flow, Flow)
                    for m in flow.measurement_indices
                ],
                default=measure_offset_start_of_loop,
            )
            >= measure_offset_start_of_loop
        )

        circuits.append(stim.Circuit())
        state = _compile_chunk_into_circuit(
            chunk=no_reps_loop,
            state=state,
            include_detectors=include_detectors,
            ignore_errors=ignore_errors,
            out_circuit=circuits[-1],
            q2i=q2i,
            flow_to_extra_coords_func=flow_to_extra_coords_func,
        )

        if fully_in_loop:
            # The circuit is guaranteed to repeat now. Don't do each iteration individually.
            finish_reps = chunk_loop.repetitions - len(circuits) + 1
            while len(circuits) > 1 and circuits[-1] == circuits[-2]:
                finish_reps += 1
                circuits.pop()
            circuits[-1] *= finish_reps
            break

    # Fuse iterations that happened to be equal.
    k = 0
    while k < len(circuits):
        k2 = k + 1
        while k2 < len(circuits) and circuits[k2] == circuits[k]:
            k2 += 1
        out_circuit += circuits[k] * (k2 - k)
        k = k2

    return state


def _compile_chunk_into_circuit_sequence(
    *,
    chunks: Iterable[Union[Chunk, ChunkLoop]],
    state: _ChunkCompileState,
    include_detectors: bool,
    ignore_errors: bool,
    out_circuit: stim.Circuit,
    q2i: dict[complex, int],
    flow_to_extra_coords_func: Callable[[Flow], Iterable[float]],
) -> _ChunkCompileState:
    for sub_chunk in chunks:
        state = _compile_chunk_into_circuit(
            chunk=sub_chunk,
            state=state,
            include_detectors=include_detectors,
            ignore_errors=ignore_errors,
            out_circuit=out_circuit,
            q2i=q2i,
            flow_to_extra_coords_func=flow_to_extra_coords_func,
        )
    return state


def _compile_chunk_into_circuit_atomic(
    *,
    chunk: Chunk,
    state: _ChunkCompileState,
    include_detectors: bool,
    ignore_errors: bool,
    out_circuit: stim.Circuit,
    q2i: dict[complex, int],
    flow_to_extra_coords_func: Callable[[Flow], Iterable[float]],
) -> _ChunkCompileState:
    prev_flows = dict(state.open_flows)
    next_flows: dict[PauliString | KeyedPauliString, Union[Flow, Literal["discard"]]] = {}
    dumped_flows: list[Flow] = []
    if include_detectors:
        for flow in chunk.flows:
            flow = Flow(
                center=flow.center,
                start=flow.start,
                end=flow.end,
                obs_index=flow.obs_index,
                measurement_indices=[
                    m + state.measure_offset for m in flow.measurement_indices
                ],
                flags=flow.flags,
            )
            if flow.start:
                prev = prev_flows.pop(flow.key_start, None)
                if prev is None:
                    if ignore_errors:
                        continue
                    else:
                        lines = [
                            "A flow input wasn't satisfied.",
                            f"   Expected input: {flow.key_start}",
                            f"   Available inputs:",
                        ]
                        for prev_avail in prev_flows.keys():
                            lines.append(f"       {prev_avail}")
                        raise ValueError('\n'.join(lines))
                elif prev == "discard":
                    if flow.end:
                        next_flows[flow.key_end] = "discard"
                    continue
                flow = prev.concat(flow, 0)
            if flow.end:
                if flow.obs_index is not None and flow.measurement_indices:
                    dumped_flows.append(flow)
                    flow = Flow(
                        start=flow.start,
                        end=flow.end,
                        obs_index=flow.obs_index,
                        center=flow.center,
                    )
                next_flows[flow.key_end] = flow
            else:
                dumped_flows.append(flow)
        for discarded in chunk.discarded_inputs:
            prev_flows.pop(discarded, None)
        for discarded in chunk.discarded_outputs:
            assert discarded not in next_flows
            next_flows[discarded] = "discard"
        unused_output = False
        for flow, val in prev_flows.items():
            if val != "discard" and not ignore_errors:
                unused_output = True
        if unused_output:
            lines = ["Some flow outputs were unused:"]
            for flow, val in prev_flows.items():
                if val != "discard" and not ignore_errors:
                    lines.append(f"   {flow}")
            raise ValueError('\n'.join(lines))

    new_measure_offset = state.measure_offset + chunk.circuit.num_measurements
    _append_circuit_with_reindexed_qubits_to_circuit(
        circuit=chunk.circuit, out=out_circuit, old_q2i=chunk.q2i, new_q2i=q2i
    )
    if include_detectors:
        det_offset_within_circuit = max([e[2] + 1 for e in chunk.circuit.get_detector_coordinates().values()], default=0)
        if det_offset_within_circuit > 0:
            out_circuit.append("SHIFT_COORDS", [], (0, 0, det_offset_within_circuit))
        coord_use_counts = collections.Counter()
        for flow in dumped_flows:
            targets = []
            for m in flow.measurement_indices:
                targets.append(stim.target_rec(m - new_measure_offset))
            if flow.obs_index is None:
                dt = coord_use_counts[flow.center]
                coord_use_counts[flow.center] += 1
                coords = (flow.center.real, flow.center.imag, dt) + tuple(flow_to_extra_coords_func(flow))
                out_circuit.append("DETECTOR", targets, coords)
            else:
                out_circuit.append("OBSERVABLE_INCLUDE", targets, flow.obs_index)
        det_offset = max(coord_use_counts.values(), default=0)
        if det_offset > 0:
            out_circuit.append("SHIFT_COORDS", [], (0, 0, det_offset))
    if len(out_circuit) > 0 and out_circuit[-1].name != "TICK":
        out_circuit.append("TICK")

    return _ChunkCompileState(
        measure_offset=new_measure_offset,
        open_flows=next_flows,
    )


@dataclasses.dataclass
class _EditFlow:
    inp: stim.PauliString
    meas: set[int]
    out: stim.PauliString
    key: int | None


def solve_flow_auto_measurements(*, flows: Iterable[Flow], circuit: stim.Circuit, q2i: dict[complex, int]) -> tuple[Flow, ...]:
    flows = tuple(flows)
    if all(flow.measurement_indices != 'auto' for flow in flows):
        return flows

    table: list[_EditFlow] = []
    num_qubits = circuit.num_qubits
    for flow in circuit.flow_generators():
        inp = flow.input_copy()
        out = flow.output_copy()
        if len(inp) == 0:
            inp = stim.PauliString(num_qubits)
        if len(out) == 0:
            out = stim.PauliString(num_qubits)
        table.append(_EditFlow(
            inp=inp,
            meas=set(flow.measurements_copy()),
            out=out,
            key=None,
        ))

    for k in range(len(flows)):
        if flows[k].measurement_indices == 'auto':
            inp = stim.PauliString(num_qubits)
            for q, p in flows[k].start.qubits.items():
                inp[q2i[q]] = p
            out = stim.PauliString(num_qubits)
            for q, p in flows[k].end.qubits.items():
                out[q2i[q]] = p
            table.append(_EditFlow(inp=inp, meas=set(), out=out, key=k))

    num_solved = 0

    def partial_elim(predicate: Callable[[_EditFlow], bool]):
        nonlocal num_solved
        for k in range(num_solved, len(table)):
            if predicate(table[k]):
                pivot = k
                break
        else:
            return

        for k in range(len(table)):
            if k != pivot and predicate(table[k]):
                table[k].inp *= table[pivot].inp
                table[k].meas ^= table[pivot].meas
                table[k].out *= table[pivot].out
        t0 = table[pivot]
        t1 = table[num_solved]
        table[pivot] = t1
        table[num_solved] = t0
        num_solved += 1

    for q in range(num_qubits):
        partial_elim(lambda f: f.inp[q] & 1)
        partial_elim(lambda f: f.inp[q] & 2)
    for q in range(num_qubits):
        partial_elim(lambda f: f.out[q] & 1)
        partial_elim(lambda f: f.out[q] & 2)

    flows = list(flows)
    for t in table:
        if t.key is not None:
            if t.inp.weight > 0 or t.out.weight > 0:
                raise ValueError(f"Failed to solve {flows[t.key]}")
            flows[t.key] = flows[t.key].with_edits(measurement_indices=t.meas)
    return tuple(flows)


def _compile_chunk_into_circuit(
    *,
    chunk: Union[Chunk, ChunkLoop, ChunkReflow],
    state: _ChunkCompileState,
    include_detectors: bool,
    ignore_errors: bool,
    out_circuit: stim.Circuit,
    q2i: dict[complex, int],
    flow_to_extra_coords_func: Callable[[Flow], Iterable[float]],
) -> _ChunkCompileState:
    if isinstance(chunk, ChunkReflow):
        return _compile_chunk_reflow_into_circuit(
            chunk_reflow=chunk,
            state=state,
        )
    elif isinstance(chunk, ChunkLoop):
        return _compile_chunk_into_circuit_many_repetitions(
            chunk_loop=chunk,
            state=state,
            include_detectors=include_detectors,
            ignore_errors=ignore_errors,
            out_circuit=out_circuit,
            q2i=q2i,
            flow_to_extra_coords_func=flow_to_extra_coords_func,
        )
    elif isinstance(chunk, Chunk):
        return _compile_chunk_into_circuit_atomic(
            chunk=chunk,
            state=state,
            include_detectors=include_detectors,
            ignore_errors=ignore_errors,
            out_circuit=out_circuit,
            q2i=q2i,
            flow_to_extra_coords_func=flow_to_extra_coords_func,
        )
    else:
        raise NotImplementedError(f'{chunk=}')


def _fail_if_flags(flow: Flow):
    flags = flow.flags
    if len(flags) == 1 and 'postselect' in flags:
        return 999,
    if flags:
        raise ValueError(f"Flow has {flags=}, but `flow_to_extra_coords_func` wasn't specified.")
    return ()


def compile_chunks_into_circuit(
    chunks: list[Union[Chunk, ChunkLoop]],
    *,
    include_detectors: bool = True,
    ignore_errors: bool = False,
    add_magic_boundaries: bool = False,
    flow_to_extra_coords_func: Callable[[Flow], Iterable[float]] = _fail_if_flags,
) -> stim.Circuit:
    all_qubits = set()
    if add_magic_boundaries:
        chunks = [chunks[0].mpp_init_chunk(), *chunks, chunks[-1].mpp_end_chunk()]

    def _compute_all_qubits(sub_chunk: Union[Chunk, ChunkLoop, ChunkReflow]):
        nonlocal all_qubits
        if isinstance(sub_chunk, ChunkLoop):
            for sub_sub_chunk in sub_chunk.chunks:
                _compute_all_qubits(sub_sub_chunk)
        elif isinstance(sub_chunk, Chunk):
            all_qubits |= sub_chunk.q2i.keys()
        elif isinstance(sub_chunk, ChunkReflow):
            pass
        else:
            raise NotImplementedError(f"{sub_chunk=}")

    for c in chunks:
        _compute_all_qubits(c)

    q2i = {q: i for i, q in enumerate(sorted_complex(set(all_qubits)))}
    full_circuit = stim.Circuit()
    for q, i in q2i.items():
        full_circuit.append("QUBIT_COORDS", i, [q.real, q.imag])

    state = _ChunkCompileState(open_flows={}, measure_offset=0)
    for k, chunk in enumerate(chunks):
        state = _compile_chunk_into_circuit(
            chunk=chunk,
            state=state,
            include_detectors=include_detectors,
            ignore_errors=ignore_errors,
            out_circuit=full_circuit,
            q2i=q2i,
            flow_to_extra_coords_func=flow_to_extra_coords_func,
        )
    if include_detectors:
        if state.open_flows:
            if not ignore_errors:
                raise ValueError("Unterminated")
    return full_circuit
