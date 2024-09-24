from typing import Iterable, Callable, Any, TYPE_CHECKING
from typing import Sequence

import stim

from gen._core._measurement_tracker import MeasurementTracker, AtLayer
from gen._core._pauli_string import PauliString
from gen._core._util import complex_key, sorted_complex


SYMMETRIC_GATES = {
    "CZ",
    "XCX",
    "YCY",
    "ZCZ",
    "SWAP",
    "ISWAP",
    "ISWAP_DAG",
    "SQRT_XX",
    "SQRT_YY",
    "SQRT_ZZ",
    "SQRT_XX_DAG",
    "SQRT_YY_DAG",
    "SQRT_ZZ_DAG",
    "DEPOLARIZE2",
}


class Builder:
    """Helper class for building stim circuits.

    Handles qubit indexing (complex -> int conversion).
    Handles measurement tracking (naming results and referring to them by name).
    """

    def __init__(
        self,
        *,
        q2i: dict[complex, int],
        circuit: stim.Circuit,
        tracker: MeasurementTracker,
    ):
        self.q2i = q2i
        self.circuit = circuit
        self.tracker = tracker

    @staticmethod
    def for_qubits(
        qubits: Iterable[complex],
        *,
        to_circuit_coord_data: Callable[[complex], complex] = lambda e: e,
    ) -> "Builder":
        q2i = {q: i for i, q in enumerate(sorted_complex(set(qubits)))}
        circuit = stim.Circuit()
        for q, i in q2i.items():
            c = to_circuit_coord_data(q)
            circuit.append("QUBIT_COORDS", [i], [c.real, c.imag])
        return Builder(
            q2i=q2i,
            circuit=circuit,
            tracker=MeasurementTracker(),
        )

    def lookup_rec(self, key: Any) -> list[int]:
        return self.tracker.lookup_recs([key])

    def lookup_recs(self, keys: Iterable[Any]) -> list[int]:
        return self.tracker.lookup_recs(keys)

    def append(self,
               gate: str,
               targets: Iterable[complex | Sequence[complex]],
               *,
               arg: Any = None,
               measure_key_func: Callable[[complex | tuple[complex, complex]], Any] = lambda e: e) -> None:
        if not targets:
            return

        data = stim.gate_data(gate)
        if data.is_two_qubit_gate:
            for target in targets:
                if not hasattr(target, '__len__') or len(target) != 2 or target[0] not in self.q2i or target[1] not in self.q2i:
                    raise ValueError(f"{gate=} is a two-qubit gate, but {target=} isn't two complex numbers in q2i.")

            # Canonicalize gate and target pairs.
            targets = [tuple(pair) for pair in targets]
            targets = sorted(targets, key=lambda pair: (self.q2i[pair[0]], self.q2i[pair[1]]))
            if gate in SYMMETRIC_GATES:
                targets = [sorted(pair, key=self.q2i.__getitem__) for pair in targets]
            elif gate == "XCZ":
                targets = [pair[::-1] for pair in targets]
                gate = "CX"
            elif gate == "YCZ":
                targets = [pair[::-1] for pair in targets]
                gate = "CY"
            elif gate == "SWAPCX":
                targets = [pair[::-1] for pair in targets]
                gate = "CXSWAP"

            self.circuit.append(gate, [self.q2i[q] for pair in targets for q in pair], arg)
        elif data.is_single_qubit_gate:
            for target in targets:
                if target not in self.q2i:
                    raise ValueError(f"{gate=} is a single-qubit gate, but {target=} isn't in indexed.")
            targets = sorted(targets, key=self.q2i.__getitem__)

            self.circuit.append(gate, [self.q2i[q] for q in targets], arg)
        else:
            raise NotImplementedError(f'{gate=}')

        if data.produces_measurements:
            for target in targets:
                self.tracker.record_measurement(key=measure_key_func(target))

    def shift_coords(self, *, dp: complex = 0, dt: int):
        self.circuit.append("SHIFT_COORDS", [], [dp.real, dp.imag, dt])

    def demolition_measure_with_feedback_passthrough(
        self,
        xs: Iterable[complex] = (),
        ys: Iterable[complex] = (),
        zs: Iterable[complex] = (),
        *,
        measure_key_func: Callable[[complex], Any] = lambda e: e,
    ) -> None:
        """Performs demolition measurements that look like measurements w.r.t. detectors.

        This is done by adding feedback operations that flip the demolished qubits depending
        on the measurement result. This feedback can then later be removed using
        stim.Circuit.with_inlined_feedback. The benefit is that it can be easier to
        programmatically create the detectors using the passthrough measurements, and
        then they can be automatically converted.
        """
        self.append("MX", xs, measure_key_func=measure_key_func)
        self.append("MY", ys, measure_key_func=measure_key_func)
        self.append("MZ", zs, measure_key_func=measure_key_func)
        self.tick()
        self.append("RX", xs)
        self.append("RY", ys)
        self.append("RZ", zs)
        for qs, b in [(xs, "Z"), (ys, "X"), (zs, "X")]:
            for q in qs:
                self.classical_paulis(
                    control_keys=[measure_key_func(q)],
                    targets=[q],
                    basis=b,
                )

    def measure_pauli_string(
        self,
        observable: PauliString,
        *,
        noise: float | None = None,
        key: Any | None,
    ):
        """Adds an MPP operation to measure the given pauli string.

        Args:
            observable: A gen.PauliString to measure.
            key: The value used to refer to the result later.
            noise: Optional measurement flip probability argument to add to the measurement.
        """
        targets = []
        for q in sorted_complex(observable.qubits):
            b = observable.qubits[q]
            if b == "X":
                m = stim.target_x
            elif b == "Y":
                m = stim.target_y
            elif b == "Z":
                m = stim.target_z
            else:
                raise NotImplementedError(f"{b=}")
            targets.append(m(self.q2i[q]))
            targets.append(stim.target_combiner())

        if targets:
            if noise == 0:
                noise = None
            targets.pop()
            self.circuit.append("MPP", targets, noise)
            if key is not None:
                self.tracker.record_measurement(key)
        elif key is not None:
            self.tracker.make_measurement_group([], key=key)

    def detector(
        self,
        keys: Iterable[Any],
        *,
        pos: complex | None,
        t: float = 0,
        extra_coords: Iterable[float] = (),
        mark_as_post_selected: bool = False,
        ignore_non_existent: bool = False,
    ) -> None:
        if pos is not None:
            coords = [pos.real, pos.imag, t] + list(extra_coords)
            if mark_as_post_selected:
                coords.append(1)
        else:
            if list(extra_coords):
                raise ValueError("pos is None but extra_coords is not empty")
            if mark_as_post_selected:
                raise ValueError("pos is None and mark_as_post_selected")
            coords = None

        if ignore_non_existent:
            keys = [k for k in keys if k in self.tracker.recorded]
        targets = self.tracker.current_measurement_record_targets_for(keys)
        if targets is not None:
            self.circuit.append("DETECTOR", targets, coords)

    def obs_include(self, keys: Iterable[Any], *, obs_index: int) -> None:
        ms = self.tracker.current_measurement_record_targets_for(keys)
        if ms:
            self.circuit.append(
                "OBSERVABLE_INCLUDE",
                ms,
                obs_index,
            )

    def tick(self) -> None:
        self.circuit.append("TICK")

    def cz(self, pairs: list[tuple[complex, complex]]) -> None:
        sorted_pairs = []
        for a, b in pairs:
            if complex_key(a) > complex_key(b):
                a, b = b, a
            sorted_pairs.append((a, b))
        sorted_pairs = sorted(
            sorted_pairs, key=lambda e: (complex_key(e[0]), complex_key(e[1]))
        )
        for a, b in sorted_pairs:
            self.circuit.append("CZ", [self.q2i[a], self.q2i[b]])

    def swap(self, pairs: list[tuple[complex, complex]]) -> None:
        sorted_pairs = []
        for a, b in pairs:
            if complex_key(a) > complex_key(b):
                a, b = b, a
            sorted_pairs.append((a, b))
        sorted_pairs = sorted(
            sorted_pairs, key=lambda e: (complex_key(e[0]), complex_key(e[1]))
        )
        for a, b in sorted_pairs:
            self.circuit.append("SWAP", [self.q2i[a], self.q2i[b]])

    def classical_paulis(
        self, *, control_keys: Iterable[Any], targets: Iterable[complex], basis: str
    ) -> None:
        gate = f"C{basis}"
        indices = [self.q2i[q] for q in sorted_complex(targets)]
        for rec in self.tracker.current_measurement_record_targets_for(control_keys):
            for i in indices:
                self.circuit.append(gate, [rec, i])
