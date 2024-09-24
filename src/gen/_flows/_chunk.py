import pathlib
from typing import Iterable, Callable, Optional, Any, Literal, TYPE_CHECKING, Union

import sinter
import stim

from gen._core import Patch, StabilizerCode, KeyedPauliString, PauliString, NoiseModel
from gen._flows._circuit_util import circuit_with_xz_flipped, circuit_to_dem_target_measurement_records_map
from gen._flows._flow import Flow
from gen._flows._test_util import assert_has_same_set_of_items_as
from gen._util import stim_circuit_with_transformed_coords, write_file

if TYPE_CHECKING:
    from gen._flows._chunk_loop import ChunkLoop
    from gen._flows._chunk_interface import ChunkInterface


class Chunk:
    """A circuit chunk with accompanying stabilizer flow assertions."""

    def __init__(
        self,
        circuit: stim.Circuit,
        q2i: dict[complex, int],
        flows: Iterable[Flow],
        discarded_inputs: Iterable[PauliString | KeyedPauliString] = (),
        discarded_outputs: Iterable[PauliString | KeyedPauliString] = (),
    ):
        """
        Args:
            circuit: The circuit implementing the chunk's functionality.
            q2i: The coordinate-to-index mapping used by the circuit.
            flows: A series of stabilizer flows that the circuit implements.
            discarded_inputs: Explicitly rejected in flows. For example, a data
                measurement chunk might reject flows for stabilizers from the
                anticommuting basis. If they are not rejected, then compilation
                will fail when attempting to combine this chunk with a preceding
                chunk that has those stabilizers from the anticommuting basis
                flowing out.
            discarded_outputs: Explicitly rejected out flows. For example, an
                initialization chunk might reject flows for stabilizers from the
                anticommuting basis. If they are not rejected, then compilation
                will fail when attempting to combine this chunk with a following
                chunk that has those stabilizers from the anticommuting basis
                flowing in.
        """
        from gen._flows._flow_util import solve_flow_auto_measurements

        self.q2i = q2i
        self.circuit = circuit
        self.flows = solve_flow_auto_measurements(flows=flows, circuit=circuit, q2i=q2i)
        self.discarded_inputs = tuple(discarded_inputs)
        self.discarded_outputs = tuple(discarded_outputs)
        assert all(isinstance(e, (PauliString, KeyedPauliString)) for e in self.discarded_inputs)
        assert all(isinstance(e, (PauliString, KeyedPauliString)) for e in self.discarded_outputs)

    def __add__(self, other: 'Chunk') -> 'Chunk':
        from gen._flows._flow_util import compile_chunks_into_circuit
        new_circuit = compile_chunks_into_circuit([self, other], ignore_errors=True)
        new_q2i = {x + 1j*y: i for i, (x, y) in new_circuit.get_final_qubit_coordinates().items()}

        end2flow = {}
        for flow in self.flows:
            if flow.end:
                end2flow[(flow.end, flow.obs_index)] = flow
        for key in self.discarded_outputs:
            end2flow[key] = 'discard'

        nm1 = self.circuit.num_measurements
        nm2 = other.circuit.num_measurements

        new_flows = []
        new_discarded_outputs = list(other.discarded_outputs)
        new_discarded_inputs = list(self.discarded_inputs)

        for key in self.discarded_inputs:
            prev_flow = end2flow.pop(key)
            if prev_flow is None:
                raise ValueError("Incompatible chunks.")
            if prev_flow != 'discard' and prev_flow.start:
                new_discarded_inputs.append((prev_flow.start, prev_flow.obs_index))

        for flow in other.flows:
            if not flow.start:
                new_flows.append(flow.with_edits(
                    measurement_indices=[m % nm2 + nm1 for m in flow.measurement_indices],
                )),
                continue

            prev_flow = end2flow.pop((flow.start, flow.obs_index))
            if prev_flow is None:
                raise ValueError("Incompatible chunks.")

            if prev_flow == 'discard':
                if flow.end:
                    new_discarded_outputs.append((flow.end, flow.obs_index))
                continue

            new_flows.append(flow.with_edits(
                start=prev_flow.start,
                measurement_indices=[m % nm1 for m in prev_flow.measurement_indices] + [m % nm2 + nm1 for m in flow.measurement_indices],
                flags=flow.flags | prev_flow.flags,
            ))

        return Chunk(
            circuit=new_circuit,
            q2i=new_q2i,
            flows=new_flows,
            discarded_inputs=new_discarded_inputs,
            discarded_outputs=new_discarded_outputs,
        )

    def __repr__(self) -> str:
        lines = ['gen.Chunk(']
        lines.append(f'    q2i={self.q2i!r},'),
        lines.append(f'    circuit={self.circuit!r},'.replace('\n', '\n    ')),
        if self.flows:
            lines.append(f'    flows={self.flows!r},'),
        if self.discarded_inputs:
            lines.append(f'    discarded_inputs={self.discarded_inputs!r},'),
        if self.discarded_outputs:
            lines.append(f'    discarded_outputs={self.discarded_outputs!r},'),
        lines.append(')')
        return '\n'.join(lines)

    def with_noise(self, noise: NoiseModel | float) -> 'Chunk':
        if isinstance(noise, float):
            noise = NoiseModel.uniform_depolarizing(1e-3)
        return self.with_edits(
            circuit=noise.noisy_circuit(self.circuit),
        )

    def with_obs_flows_as_det_flows(self) -> 'Chunk':
        return self.with_edits(
            flows=[
                flow.with_edits(obs_index=None)
                for flow in self.flows
            ],
        )

    @staticmethod
    def from_circuit_with_mpp_boundaries(circuit: stim.Circuit) -> 'Chunk':
        allowed = {
            'TICK',
            'OBSERVABLE_INCLUDE',
            'DETECTOR',
            'MPP',
            'QUBIT_COORDS',
            'SHIFT_COORDS',
        }
        start = 0
        end = len(circuit)
        while start < len(circuit) and circuit[start].name in allowed:
            start += 1
        while end > 0 and circuit[end - 1].name in allowed:
            end -= 1
        while end < len(circuit) and circuit[end].name != 'MPP':
            end += 1
        while end > 0 and circuit[end - 1].name == 'TICK':
            end -= 1
        if end <= start:
            raise ValueError("end <= start")

        prefix, body, suffix = circuit[:start], circuit[start:end], circuit[end:]
        start_tick = prefix.num_ticks
        end_tick = start_tick + body.num_ticks + 1
        c = stim.Circuit()
        c += prefix
        c.append('TICK')
        c += body
        c.append('TICK')
        c += suffix
        det_regions = c.detecting_regions(ticks=[start_tick, end_tick])
        records = circuit_to_dem_target_measurement_records_map(c)
        pn = prefix.num_measurements
        record_range = range(pn, pn + body.num_measurements)

        q2i = {qr + qi*1j: i for i, (qr, qi) in circuit.get_final_qubit_coordinates().items()}
        i2q = {i: q for q, i in q2i.items()}
        dropped_detectors = set()

        flows = []
        for target, items in det_regions.items():
            if target.is_relative_detector_id():
                dropped_detectors.add(target.val)
            start_ps: stim.PauliString = items.get(start_tick, stim.PauliString(0))
            start = PauliString({i2q[i]: '_XYZ'[start_ps[i]] for i in start_ps.pauli_indices()})

            end_ps: stim.PauliString = items.get(end_tick, stim.PauliString(0))
            end = PauliString({i2q[i]: '_XYZ'[end_ps[i]] for i in end_ps.pauli_indices()})

            flows.append(Flow(
                start=start,
                end=end,
                measurement_indices=[m - record_range.start for m in records[target] if m in record_range],
                obs_index=None if target.is_relative_detector_id() else target.val,
                center=(sum(start.qubits.keys()) + sum(end.qubits.keys())) / (len(start.qubits) + len(end.qubits)),
            ))

        kept = stim.Circuit()
        num_d = prefix.num_detectors
        for inst in body.flattened():
            if inst.name == 'DETECTOR':
                if num_d not in dropped_detectors:
                    kept.append(inst)
                num_d += 1
            elif inst.name != 'OBSERVABLE_INCLUDE':
                kept.append(inst)

        return Chunk(
            q2i=q2i,
            flows=flows,
            circuit=kept,
        )

    def _interface(
            self,
            side: Literal['start', 'end'],
            *,
            skip_discards: bool = False,
            skip_passthroughs: bool = False,
    ) -> tuple[PauliString | KeyedPauliString, ...]:
        if side == 'start':
            include_start = True
            include_end = False
        elif side == 'end':
            include_start = False
            include_end = True
        else:
            raise NotImplementedError(f'{side=}')

        result = []
        for flow in self.flows:
            if include_start and flow.start and not (skip_passthroughs and flow.end):
                result.append((flow.start, flow.obs_index))
            if include_end and flow.end and not (skip_passthroughs and flow.start):
                result.append((flow.end, flow.obs_index))
        if include_start and not skip_discards:
            result.extend(self.discarded_inputs)
        if include_end and not skip_discards:
            result.extend(self.discarded_outputs)

        result_set = set()
        collisions = set()
        for item in result:
            if item in result_set:
                collisions.add(item)
            result_set.add(item)

        if collisions:
            msg = [f"{side} interface had collisions:"]
            for a, b in sorted(collisions):
                msg.append(f"    {a}, obs_index={b}")
            raise ValueError("\n".join(msg))

        return tuple(sorted(result_set))

    def with_edits(
            self,
            *,
            circuit: stim.Circuit | None = None,
            q2i: dict[complex, int] | None = None,
            flows: Iterable[Flow] | None = None,
            discarded_inputs: Iterable[PauliString | KeyedPauliString] | None = None,
            discarded_outputs: Iterable[PauliString | KeyedPauliString] | None = None,
    ) -> 'Chunk':
        return Chunk(
            circuit=self.circuit if circuit is None else circuit,
            q2i=self.q2i if q2i is None else q2i,
            flows=self.flows if flows is None else flows,
            discarded_inputs=self.discarded_inputs if discarded_inputs is None else discarded_inputs,
            discarded_outputs=self.discarded_outputs if discarded_outputs is None else discarded_outputs,
        )

    def __eq__(self, other):
        if not isinstance(other, Chunk):
            return NotImplemented
        return (
            self.q2i == other.q2i
            and self.circuit == other.circuit
            and self.flows == other.flows
            and self.discarded_inputs == other.discarded_inputs
            and self.discarded_outputs == other.discarded_outputs
        )

    def write_viewer(
        self, path: str | pathlib.Path, *, patch: Optional[Patch] = None
    ) -> None:
        from gen import stim_circuit_html_viewer

        if patch is None:
            patch = self.start_interface()
            if len(patch.ports) == 0:
                patch = self.end_interface()
        write_file(path, stim_circuit_html_viewer(self.circuit, patch=patch))

    def with_flows_postselected(
        self, flow_predicate: Callable[[Flow], bool]
    ) -> 'Chunk':
        return Chunk(
            circuit=self.circuit,
            q2i=self.q2i,
            flows=[
                flow.postselected() if flow_predicate(flow) else flow
                for flow in self.flows
            ],
            discarded_inputs=self.discarded_inputs,
            discarded_outputs=self.discarded_outputs,
        )

    def __mul__(self, other: int) -> "ChunkLoop":
        from gen._flows._chunk_loop import ChunkLoop
        return ChunkLoop([self], repetitions=other)

    def with_repetitions(self, repetitions: int) -> "ChunkLoop":
        from gen._flows._chunk_loop import ChunkLoop
        return ChunkLoop([self], repetitions=repetitions)

    def verify(
        self,
        *,
        expected_in: Union['ChunkInterface', 'StabilizerCode', None] = None,
        expected_out: Union['ChunkInterface', 'StabilizerCode', None] = None,
        should_measure_all_code_stabilizers: bool = False,
    ):
        """Checks that this chunk's circuit actually implements its flows."""
        __tracebackhide__ = True

        assert not should_measure_all_code_stabilizers or expected_in is not None or should_measure_all_code_stabilizers is not None
        assert isinstance(self.circuit, stim.Circuit)
        assert isinstance(self.q2i, dict)
        assert isinstance(self.flows, tuple)
        assert isinstance(self.discarded_inputs, tuple)
        assert isinstance(self.discarded_outputs, tuple)
        assert all(isinstance(e, Flow) for e in self.flows)
        assert all(isinstance(e, (PauliString, KeyedPauliString)) for e in self.discarded_inputs)
        assert all(isinstance(e, (PauliString, KeyedPauliString)) for e in self.discarded_outputs)

        for key, group in sinter.group_by(
            self.flows, key=lambda flow: (flow.start, flow.obs_index)
        ).items():
            if key[0] and len(group) > 1:
                raise ValueError(f"Multiple flows with same non-empty end: {group}")
        for key, group in sinter.group_by(
            self.flows, key=lambda flow: (flow.end, flow.obs_index)
        ).items():
            if key[0] and len(group) > 1:
                raise ValueError(f"Multiple flows with same non-empty end: {group}")

        stim_flows = []
        for flow in self.flows:
            inp = stim.PauliString(len(self.q2i))
            out = stim.PauliString(len(self.q2i))
            for q, p in flow.start.qubits.items():
                inp[self.q2i[q]] = p
            for q, p in flow.end.qubits.items():
                out[self.q2i[q]] = p
            stim_flows.append(stim.Flow(
                input=inp,
                output=out,
                measurements=flow.measurement_indices,
            ))
        if not self.circuit.has_all_flows(stim_flows, unsigned=True):
            msg = ["Circuit lacks the following flows:"]
            for k in range(len(stim_flows)):
                if not self.circuit.has_flow(stim_flows[k], unsigned=True):
                    msg.append('    ' + str(self.flows[k]))
            raise ValueError('\n'.join(msg))

        if expected_in is not None:
            if isinstance(expected_in, StabilizerCode):
                expected_in = expected_in.as_interface()
            assert_has_same_set_of_items_as(
                self.start_interface().with_discards_as_ports().ports,
                expected_in.with_discards_as_ports().ports,
                "self.start_interface().with_discards_as_ports().ports",
                "expected_in.with_discards_as_ports().ports",
            )
            if should_measure_all_code_stabilizers:
                assert_has_same_set_of_items_as(
                    self.start_interface(skip_passthroughs=True).without_discards().without_keyed().ports,
                    expected_in.without_discards().without_keyed().ports,
                    "self.start_interface(skip_passthroughs=True).without_discards().without_keyed().ports",
                    "expected_in.without_discards().without_keyed().ports",
                )
        else:
            # Creating the interface checks for collisions
            self.start_interface()

        if expected_out is not None:
            if isinstance(expected_out, StabilizerCode):
                expected_out = expected_out.as_interface()
            assert_has_same_set_of_items_as(
                self.end_interface().with_discards_as_ports().ports,
                expected_out.with_discards_as_ports().ports,
                "self.end_interface().with_discards_as_ports().ports",
                "expected_out.with_discards_as_ports().ports",
            )
            if should_measure_all_code_stabilizers:
                assert_has_same_set_of_items_as(
                    self.end_interface(skip_passthroughs=True).without_discards().without_keyed().ports,
                    expected_out.without_discards().without_keyed().ports,
                    "self.end_interface(skip_passthroughs=True).without_discards().without_keyed().ports",
                    "expected_out.without_discards().without_keyed().ports",
                )
        else:
            # Creating the interface checks for collisions
            self.end_interface()

    def time_reversed(self) -> 'Chunk':
        """Checks that this chunk's circuit actually implements its flows."""

        stim_flows = []
        for flow in self.flows:
            inp = stim.PauliString(len(self.q2i))
            out = stim.PauliString(len(self.q2i))
            for q, p in flow.start.qubits.items():
                inp[self.q2i[q]] = p
            for q, p in flow.end.qubits.items():
                out[self.q2i[q]] = p
            stim_flows.append(stim.Flow(
                input=inp,
                output=out,
                measurements=flow.measurement_indices,
            ))
        rev_circuit, rev_flows = self.circuit.time_reversed_for_flows(stim_flows)
        nm = rev_circuit.num_measurements
        return Chunk(
            circuit=rev_circuit,
            q2i=self.q2i,
            flows=[
                Flow(
                    center=flow.center,
                    start=flow.end,
                    end=flow.start,
                    measurement_indices=[m + nm for m in rev_flow.measurements_copy()],
                    flags=flow.flags,
                    obs_index=flow.obs_index,
                )
                for flow, rev_flow in zip(self.flows, rev_flows, strict=True)
            ],
            discarded_inputs=self.discarded_outputs,
            discarded_outputs=self.discarded_inputs,
        )

    def with_xz_flipped(self) -> 'Chunk':
        return Chunk(
            q2i=self.q2i,
            circuit=circuit_with_xz_flipped(self.circuit),
            flows=[flow.with_xz_flipped() for flow in self.flows],
            discarded_inputs=[(p.with_xz_flipped(), k) for p, k in self.discarded_inputs],
            discarded_outputs=[(p.with_xz_flipped(), k) for p, k in self.discarded_outputs],
        )

    def with_transformed_coords(
        self, transform: Callable[[complex], complex]
    ) -> 'Chunk':
        return Chunk(
            q2i={transform(q): i for q, i in self.q2i.items()},
            circuit=stim_circuit_with_transformed_coords(self.circuit, transform),
            flows=[flow.with_transformed_coords(transform) for flow in self.flows],
            discarded_inputs=[p.with_transformed_coords(transform) for p in self.discarded_inputs],
            discarded_outputs=[p.with_transformed_coords(transform) for p in self.discarded_outputs],
        )

    def flattened(self) -> list['Chunk']:
        """This is here for duck-type compatibility with ChunkLoop."""
        return [self]

    def mpp_init_chunk(self) -> 'Chunk':
        return self.start_interface().mpp_init_chunk()

    def mpp_end_chunk(self) -> 'Chunk':
        return self.end_interface().mpp_end_chunk()

    def start_interface(self, *, skip_passthroughs: bool = False) -> 'ChunkInterface':
        from gen._flows._chunk_interface import ChunkInterface
        return ChunkInterface(
            ports=[
                flow.key_start
                for flow in self.flows
                if flow.start
                if not (skip_passthroughs and flow.end)
            ],
            discards=self.discarded_inputs,
        )

    def end_interface(self, *, skip_passthroughs: bool = False) -> 'ChunkInterface':
        from gen._flows._chunk_interface import ChunkInterface
        return ChunkInterface(
            ports=[
                flow.key_end
                for flow in self.flows
                if flow.end
                if not (skip_passthroughs and flow.start)
            ],
            discards=self.discarded_outputs,
        )

    def tick_count(self) -> int:
        return self.circuit.num_ticks + 1
