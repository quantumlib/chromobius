import functools
from typing import Iterable, Callable, TYPE_CHECKING

from gen._core import Patch, Tile, StabilizerCode, KeyedPauliString, PauliString
from gen._flows._test_util import assert_has_same_set_of_items_as

if TYPE_CHECKING:
    from gen._flows._chunk import Chunk
    from gen._flows._chunk_interface import ChunkInterface


class ChunkReflow:
    def __init__(
            self,
            out2in: dict[PauliString | KeyedPauliString, list[PauliString | KeyedPauliString]],
            discard_in: Iterable[PauliString | KeyedPauliString] = (),
    ):
        self.out2in = out2in
        self.discard_in = tuple(discard_in)
        assert isinstance(self.out2in, dict)
        for k, vs in self.out2in.items():
            assert isinstance(k, (PauliString, KeyedPauliString)), k
            assert isinstance(vs, list)
            for v in vs:
                assert isinstance(v, (PauliString, KeyedPauliString))

    def with_transformed_coords(
            self, transform: Callable[[complex], complex]
    ) -> "ChunkReflow":
        return ChunkReflow(
            out2in={
                kp.with_transformed_coords(transform): [
                    vp.with_transformed_coords(transform)
                    for vp in vs
                ]
                for kp, vs in self.out2in.items()
            },
            discard_in=[
                kp.with_transformed_coords(transform)
                for kp in self.discard_in
            ]
        )

    def start_interface(self) -> 'ChunkInterface':
        from gen._flows._chunk_interface import ChunkInterface
        return ChunkInterface(
            ports={v for vs in self.out2in.values() for v in vs},
            discards=self.discard_in,
        )

    def end_interface(self) -> 'ChunkInterface':
        from gen._flows._chunk_interface import ChunkInterface
        return ChunkInterface(
            ports=self.out2in.keys(),
            discards=self.discard_in,
        )

    def start_code(self) -> StabilizerCode:
        tiles = []
        xs = []
        zs = []
        for ps, obs in self.removed_inputs:
            if obs is None:
                tiles.append(
                    Tile(
                        ordered_data_qubits=ps.qubits.keys(),
                        bases="".join(ps.qubits.values()),
                        measurement_qubit=list(ps.qubits.keys())[0],
                    )
                )
            else:
                bases = set(ps.qubits.values())
                if bases == {'X'}:
                    xs.append(ps)
                else:
                    zs.append(ps)
        return StabilizerCode(patch=Patch(tiles), observables_x=xs, observables_z=zs)

    def start_patch(self) -> Patch:
        tiles = []
        for ps, obs in self.removed_inputs:
            if obs is None:
                tiles.append(
                    Tile(
                        ordered_data_qubits=ps.qubits.keys(),
                        bases="".join(ps.qubits.values()),
                        measurement_qubit=list(ps.qubits.keys())[0],
                    )
                )
        return Patch(tiles)

    def end_patch(self) -> Patch:
        tiles = []
        for ps, obs in self.out2in.keys():
            if obs is None:
                tiles.append(
                    Tile(
                        ordered_data_qubits=ps.qubits.keys(),
                        bases="".join(ps.qubits.values()),
                        measurement_qubit=list(ps.qubits.keys())[0],
                    )
                )
        return Patch(tiles)

    def mpp_init_chunk(self) -> 'Chunk':
        return self.start_interface().mpp_init_chunk()

    def mpp_end_chunk(self, *, kept_obs_basis: str | None = None) -> 'Chunk':
        return self.end_interface().mpp_end_chunk()

    @functools.cached_property
    def removed_inputs(self) -> frozenset[PauliString | KeyedPauliString]:
        return frozenset(
            v
            for vs in self.out2in.values()
            for v in vs
        ) | frozenset(self.discard_in)

    def verify(
            self,
            *,
            expected_in: StabilizerCode | None = None,
            expected_out: StabilizerCode | None = None,
    ):
        assert isinstance(self.out2in, dict)
        for k, vs in self.out2in.items():
            assert isinstance(k, (PauliString, KeyedPauliString)), k
            assert isinstance(vs, list)
            for v in vs:
                assert isinstance(v, (PauliString, KeyedPauliString))

        for k, vs in self.out2in.items():
            acc = PauliString({})
            for v in vs:
                acc *= PauliString(v)
            if acc != PauliString(k):
                lines = ["A reflow output wasn't equal to the product of its inputs."]
                lines.append(f"   Output: {k}")
                lines.append(f"   Difference: {PauliString(k) * acc}")
                lines.append(f"   Inputs:")
                for v in vs:
                    lines.append(f"        {v}")
                raise ValueError('\n'.join(lines))

        if expected_in is not None:
            if isinstance(expected_in, StabilizerCode):
                expected_in = expected_in.as_interface()
            assert_has_same_set_of_items_as(
                self.start_interface().with_discards_as_ports().ports,
                expected_in.with_discards_as_ports().ports,
                "self.start_interface().with_discards_as_ports().ports",
                "expected_in.with_discards_as_ports().ports",
            )

        if expected_out is not None:
            if isinstance(expected_out, StabilizerCode):
                expected_out = expected_out.as_interface()
            assert_has_same_set_of_items_as(
                self.end_interface().with_discards_as_ports().ports,
                expected_out.with_discards_as_ports().ports,
                "self.end_interface().with_discards_as_ports().ports",
                "expected_out.with_discards_as_ports().ports",
            )

        if len(self.out2in) != len(self.removed_inputs):
            msg = []
            msg.append("Number of outputs != number of distinct inputs.")
            msg.append("Outputs {")
            for ps, obs in self.out2in:
                msg.append(f"    {ps}, obs={obs}")
            msg.append("}")
            msg.append("Distinct inputs {")
            for ps, obs in self.removed_inputs:
                msg.append(f"    {ps}, obs={obs}")
            msg.append("}")
            raise ValueError('\n'.join(msg))
