import collections
import functools
import itertools
import pathlib
from typing import Iterable, Literal, Any, Callable, Sequence, Union, \
    TYPE_CHECKING

import stim

import gen
from gen._core._builder import Builder, AtLayer
from gen._core._noise import NoiseRule
from gen._core._patch import Patch
from gen._core._pauli_string import PauliString
from gen._core._util import sorted_complex
from gen._core._keyed_pauli_string import KeyedPauliString
from gen._util import write_file

if TYPE_CHECKING:
    from gen._flows._chunk import Chunk
    from gen._flows._flow import Flow
    from gen._flows._chunk_interface import ChunkInterface


class StabilizerCode:
    """This class stores the stabilizers and observables of a stabilizer code.

    The exact semantics of the class are somewhat loose. For example, by default
    this class doesn't verify that its fields actually form a valid stabilizer
    code. This is so that the class can be used as a sort of useful data dumping
    ground even in cases where what is being built isn't a stabilizer code. For
    example, you can store a gauge code in the fields... it's just that methods
    like 'make_code_capacity_circuit' will no longer work.

    The stabilizers are defined by the 'tiles' of the code's 'patch'. Each tile
    defines data qubits and a measurement qubit. The measurement qubit is also a
    very loose concept; it may literally represent a single ancilla qubit used
    for measuring the stabilizer or it may be more like a unique key identifying
    the tile with no relation to any real qubit.
    """

    def __init__(
        self,
        *,
        patch: Patch | None = None,
        observables_x: Iterable[PauliString] = (),
        observables_z: Iterable[PauliString] = (),
    ):
        self.patch = Patch([]) if patch is None else patch
        self.observables_x: tuple[PauliString, ...] = tuple(observables_x)
        self.observables_z: tuple[PauliString, ...] = tuple(observables_z)

    def x_basis_subset(self) -> 'StabilizerCode':
        return StabilizerCode(
            patch=self.patch.with_only_x_tiles(),
            observables_x=self.observables_x,
        )

    def z_basis_subset(self) -> 'StabilizerCode':
        return StabilizerCode(
            patch=self.patch.with_only_z_tiles(),
            observables_x=self.observables_x if not self.observables_z else (),
            observables_z=self.observables_z,
        )

    @property
    def tiles(self) -> tuple['gen.Tile', ...]:
        return self.patch.tiles

    def find_distance(self, *, max_search_weight: int) -> int:
        return len(self.find_logical_error(max_search_weight=max_search_weight))

    def find_logical_error(self, *, max_search_weight: int) -> list[stim.ExplainedError]:
        circuit = self.make_code_capacity_circuit(noise=1e-3)
        if max_search_weight == 2:
            return circuit.shortest_graphlike_error()
        return circuit.search_for_undetectable_logical_errors(
            dont_explore_edges_with_degree_above=max_search_weight,
            dont_explore_detection_event_sets_with_size_above=max_search_weight,
            dont_explore_edges_increasing_symptom_degree=False,
            canonicalize_circuit_errors=True,
        )

    def with_observables_from_basis(self, basis: Literal['X', 'Y', 'Z']) -> 'StabilizerCode':
        if basis == 'X':
            return gen.StabilizerCode(
                patch=self.patch,
                observables_x=self.observables_x,
                observables_z=[],
            )
        elif basis == 'Y':
            return gen.StabilizerCode(
                patch=self.patch,
                observables_x=[x * z for x, z in zip(self.observables_x, self.observables_z)],
                observables_z=[],
            )
        elif basis == 'Z':
            return gen.StabilizerCode(
                patch=self.patch,
                observables_x=[],
                observables_z=self.observables_z,
            )
        else:
            raise NotImplementedError(f'{basis=}')

    def mpp_init_chunk(self) -> 'Chunk':
        return self.mpp_chunk(flow_style='init')

    def mpp_end_chunk(self) -> 'Chunk':
        return self.mpp_chunk(flow_style='end')

    def mpp_chunk(
            self,
            *,
            noise: float | NoiseRule | None = None,
            flow_style: Literal['passthrough', 'end', 'init'] = 'passthrough',
            resolve_anticommutations: bool = False,
    ) -> 'Chunk':
        assert flow_style in ['init', 'end', 'passthrough']
        if resolve_anticommutations:
            observables, immune = self.entangled_observables(ancilla_qubits_for_xz_pairs=None)
            immune = set(immune)
        else:
            observables = self.observables_x + self.observables_z
            immune = set()

        from gen._flows import Flow, Chunk
        builder = Builder.for_qubits(self.data_set | immune)
        flows = []
        discards = []

        if noise is None or noise == 0:
            noise = NoiseRule()
        elif isinstance(noise, (float, int)):
            noise = NoiseRule(before={'DEPOLARIZE1': noise}, flip_result=noise)

        for k, obs in enumerate(observables):
            if flow_style != 'passthrough':
                builder.measure_pauli_string(obs, key=f'obs{k}')
            flows.append(Flow(
                center=-1,
                start=None if flow_style == 'init' else obs,
                end=None if flow_style == 'end' else obs,
                measurement_indices=builder.lookup_rec(f'obs{k}') if flow_style != 'passthrough' else (),
                obs_index=k,
            ))

        for gate, strength in noise.before.items():
            builder.append(gate, self.data_set, arg=strength)
        for m, tile in enumerate(self.patch.tiles):
            if tile.data_set:
                ps = tile.to_data_pauli_string()
                builder.measure_pauli_string(ps, key=f'det{m}', noise=noise.flip_result)
                if flow_style != 'init':
                    flows.append(Flow(
                        center=tile.measurement_qubit,
                        start=ps,
                        measurement_indices=builder.lookup_rec(f'det{m}'),
                        flags=tile.flags,
                    ))
                if flow_style != 'end':
                    flows.append(Flow(
                        center=tile.measurement_qubit,
                        end=ps,
                        measurement_indices=builder.lookup_rec(f'det{m}'),
                        flags=tile.flags,
                    ))
        for gate, strength in noise.after.items():
            builder.append(gate, self.data_set, arg=strength)

        return Chunk(
            circuit=builder.circuit,
            q2i=builder.q2i,
            flows=flows,
            discarded_inputs=discards,
        )

    def as_interface(self) -> 'ChunkInterface':
        from gen._flows._chunk_interface import ChunkInterface
        ports = []
        for tile in self.patch.tiles:
            if tile.data_set:
                ports.append(tile.to_data_pauli_string())
        for k, ps in enumerate(self.observables_x):
            ports.append(KeyedPauliString(pauli_string=ps, key=k))
        for k, ps in enumerate(self.observables_z):
            ports.append(KeyedPauliString(pauli_string=ps, key=k))
        return ChunkInterface(ports=ports, discards=[])

    def with_edits(
            self,
            *,
            patch: Patch | None = None,
            observables_x: Iterable[PauliString] | None = None,
            observables_z: Iterable[PauliString] | None = None,
    ) -> 'StabilizerCode':
        return StabilizerCode(
            patch=self.patch if patch is None else patch,
            observables_x=self.observables_x if observables_x is None else observables_x,
            observables_z=self.observables_z if observables_z is None else observables_z,
        )

    @functools.cached_property
    def data_set(self) -> frozenset[complex]:
        result = set(self.patch.data_set)
        for obs in self.observables_x, self.observables_z:
            for e in obs:
                result |= e.qubits.keys()
        return frozenset(result)

    @functools.cached_property
    def measure_set(self) -> frozenset[complex]:
        return self.patch.measure_set

    @functools.cached_property
    def used_set(self) -> frozenset[complex]:
        result = set(self.patch.used_set)
        for obs in self.observables_x, self.observables_z:
            for e in obs:
                result |= e.qubits.keys()
        return frozenset(result)

    @staticmethod
    def from_patch_with_inferred_observables(patch: Patch) -> "StabilizerCode":
        q2i = {q: i for i, q in enumerate(sorted_complex(patch.data_set))}
        i2q = {i: q for q, i in q2i.items()}

        stabilizers: list[stim.PauliString] = []
        for tile in patch.tiles:
            stabilizer = stim.PauliString(len(q2i))
            for p, q in zip(tile.bases, tile.ordered_data_qubits):
                if q is not None:
                    stabilizer[q2i[q]] = p
            stabilizers.append(stabilizer)

        stabilizer_set: set[str] = set(str(e) for e in stabilizers)
        solved_tableau = stim.Tableau.from_stabilizers(
            stabilizers,
            allow_redundant=True,
            allow_underconstrained=True,
        )

        obs_xs = []
        obs_zs = []

        k: int = len(solved_tableau)
        while k > 0 and str(solved_tableau.z_output(k - 1)) not in stabilizer_set:
            k -= 1
            obs_xs.append(
                PauliString.from_stim_pauli_string(
                    solved_tableau.x_output(k)
                ).with_transformed_coords(i2q.__getitem__)
            )
            obs_zs.append(
                PauliString.from_stim_pauli_string(
                    solved_tableau.z_output(k)
                ).with_transformed_coords(i2q.__getitem__)
            )

        return StabilizerCode(patch=patch, observables_x=obs_xs, observables_z=obs_zs)

    def with_epr_observables(self) -> 'StabilizerCode':
        r = min([e.real for e in self.patch.used_set], default=0)
        new_obs_x = []
        new_obs_z = []
        for k in range(min(len(self.observables_x), len(self.observables_z))):
            if self.observables_x[k].anticommutes(self.observables_z[k]):
                new_obs_x.append(self.observables_x[k] * PauliString({r - 0.25 - 0.25j: 'X'}))
                new_obs_z.append(self.observables_z[k] * PauliString({r - 0.25 - 0.25j: 'Z'}))
                r -= 1
            else:
                new_obs_x.append(self.observables_x[k])
                new_obs_z.append(self.observables_z[k])
        return StabilizerCode(patch=self.patch, observables_x=new_obs_x, observables_z=new_obs_z)

    def entangled_observables(
        self, ancilla_qubits_for_xz_pairs: Sequence[complex] | None
    ) -> tuple[list[PauliString], list[complex]]:
        """Makes XZ observables commute by entangling them with ancilla qubits.

        This is useful when attempting to test all observables simultaneously.
        As long as noise is not applied to the ancilla qubits, the observables
        returned by this method cover the same noise as the original observables
        but the returned observables can be simultaneously measured.
        """
        num_common = min(len(self.observables_x), len(self.observables_z))
        if ancilla_qubits_for_xz_pairs is None:
            a = (
                min(q.real for q in self.patch.data_set)
                + min(q.imag for q in self.patch.data_set) * 1j
                - 1j
            )
            ancilla_qubits_for_xz_pairs = [a + k for k in range(num_common)]
        else:
            assert len(ancilla_qubits_for_xz_pairs) == num_common
        observables = []
        for k, obs in enumerate(self.observables_x):
            if k < len(ancilla_qubits_for_xz_pairs):
                a = ancilla_qubits_for_xz_pairs[k]
                obs = obs * PauliString({a: "X"})
            observables.append(obs)
        for k, obs in enumerate(self.observables_z):
            if k < len(ancilla_qubits_for_xz_pairs):
                a = ancilla_qubits_for_xz_pairs[k]
                obs = obs * PauliString({a: "Z"})
            observables.append(obs)
        return observables, list(ancilla_qubits_for_xz_pairs)

    def verify(self) -> None:
        """Verifies observables and stabilizers relate as a stabilizer code.

        All stabilizers should commute with each other.
        All stabilizers should commute with all observables.
        Same-index X and Z observables should anti-commute.
        All other observable pairs should commute.
        """

        q2tiles = collections.defaultdict(list)
        for tile in self.patch.tiles:
            for q in tile.data_set:
                q2tiles[q].append(tile)
        for tile1 in self.patch.tiles:
            overlapping = {
                tile2
                for q in tile1.data_set
                for tile2 in q2tiles[q]
            }
            for tile2 in overlapping:
                t1 = tile1.to_data_pauli_string()
                t2 = tile2.to_data_pauli_string()
                if not t1.commutes(t2):
                    raise ValueError(
                        f"Tile stabilizer {t1=} anticommutes with tile stabilizer {t2=}."
                    )

        for tile in self.patch.tiles:
            t = tile.to_data_pauli_string()
            for obs in self.observables_x + self.observables_z:
                if not obs.commutes(t):
                    raise ValueError(
                        f"Tile stabilizer {tile=} anticommutes with {obs=}."
                    )
        all_obs = self.observables_x + self.observables_z
        anticommuting_pairs = set()
        for k in range(min(len(self.observables_x), len(self.observables_z))):
            anticommuting_pairs.add((k, k + len(self.observables_x)))
        for k1 in range(len(all_obs)):
            for k2 in range(k1 + 1, len(all_obs)):
                obs1 = all_obs[k1]
                obs2 = all_obs[k2]
                if (k1, k2) in anticommuting_pairs:
                    if obs1.commutes(obs2):
                        raise ValueError(
                            f"X/Z observable pair commutes: {obs1=}, {obs2=}."
                        )
                else:
                    if not obs1.commutes(obs2):
                        raise ValueError(
                            f"Unpaired observables should commute: {obs1=}, {obs2=}."
                        )

    def with_xz_flipped(self) -> 'StabilizerCode':
        return StabilizerCode(
            patch=self.patch.with_xz_flipped(),
            observables_x=[obs_x.with_xz_flipped() for obs_x in self.observables_x],
            observables_z=[obs_z.with_xz_flipped() for obs_z in self.observables_z],
        )

    def write_svg(
        self,
        path: str | pathlib.Path,
        *,
        show_order: bool | Literal["undirected", "3couplerspecial"] = False,
        show_measure_qubits: bool = False,
        show_data_qubits: bool = True,
        system_qubits: Iterable[complex] = (),
        opacity: float = 1,
        show_coords: bool = True,
        show_obs: bool = True,
        other: Union[None, 'StabilizerCode', 'Patch', Iterable[Union['StabilizerCode', 'Patch']]] = None,
        tile_color_func: Callable[['gen.Tile'], str] | None = None,
        rows: int | None = None,
        cols: int | None = None,
        find_logical_err_max_weight: int | None = None,
    ) -> None:
        flat = [self]
        if isinstance(other, (StabilizerCode, Patch)):
            flat.append(other)
        elif other is not None:
            flat.extend(other)

        from gen._viz_patch_svg import patch_svg_viewer
        viewer = patch_svg_viewer(
            patches=flat,
            show_obs=show_obs,
            show_measure_qubits=show_measure_qubits,
            show_data_qubits=show_data_qubits,
            show_order=show_order,
            find_logical_err_max_weight=find_logical_err_max_weight,
            expected_points=system_qubits,
            opacity=opacity,
            show_coords=show_coords,
            tile_color_func=tile_color_func,
            cols=cols,
            rows=rows,
        )
        write_file(path, viewer)

    def with_transformed_coords(
        self, coord_transform: Callable[[complex], complex]
    ) -> "StabilizerCode":
        return StabilizerCode(
            patch=self.patch.with_transformed_coords(coord_transform),
            observables_x=[
                e.with_transformed_coords(coord_transform) for e in self.observables_x
            ],
            observables_z=[
                e.with_transformed_coords(coord_transform) for e in self.observables_z
            ],
        )

    def make_code_capacity_circuit(
        self,
        *,
        noise: float | NoiseRule,
        extra_coords_func: Callable[['Flow'], Iterable[float]] = lambda _: (),
    ) -> stim.Circuit:
        if isinstance(noise, (int, float)):
            noise = NoiseRule(after={"DEPOLARIZE1": noise})
        if noise.flip_result:
            raise ValueError(f"{noise=} includes measurement noise.")
        chunk1 = self.mpp_chunk(noise=NoiseRule(after=noise.after), flow_style='init', resolve_anticommutations=True)
        chunk3 = self.mpp_chunk(noise=NoiseRule(before=noise.before), flow_style='end', resolve_anticommutations=True)
        from gen._flows._flow_util import compile_chunks_into_circuit
        return compile_chunks_into_circuit([chunk1, chunk3], flow_to_extra_coords_func=extra_coords_func)

    def make_phenom_circuit(
        self,
        *,
        noise: float | NoiseRule,
        rounds: int,
        extra_coords_func: Callable[['gen.Flow'], Iterable[float]] = lambda _: (),
    ) -> stim.Circuit:
        if isinstance(noise, (int, float)):
            noise = NoiseRule(after={"DEPOLARIZE1": noise}, flip_result=noise)
        chunk1 = self.mpp_chunk(noise=NoiseRule(after=noise.after), flow_style='init', resolve_anticommutations=True)
        chunk2 = self.mpp_chunk(noise=noise, resolve_anticommutations=True)
        chunk3 = self.mpp_chunk(noise=NoiseRule(before=noise.before), flow_style='end', resolve_anticommutations=True)
        from gen._flows._flow_util import compile_chunks_into_circuit
        return compile_chunks_into_circuit([chunk1, chunk2 * rounds, chunk3], flow_to_extra_coords_func=extra_coords_func)

    def __repr__(self) -> str:
        def indented(x: str) -> str:
            return x.replace("\n", "\n    ")

        def indented_repr(x: Any) -> str:
            if isinstance(x, tuple):
                return indented(
                    indented("[\n" + ",\n".join(indented_repr(e) for e in x)) + ",\n]"
                )
            return indented(repr(x))

        return f"""gen.StabilizerCode(
    patch={indented_repr(self.patch)},
    observables_x={indented_repr(self.observables_x)},
    observables_z={indented_repr(self.observables_z)},
)"""

    def __eq__(self, other) -> bool:
        if not isinstance(other, StabilizerCode):
            return NotImplemented
        return (
            self.patch == other.patch
            and self.observables_x == other.observables_x
            and self.observables_z == other.observables_z
        )

    def __ne__(self, other) -> bool:
        return not (self == other)
