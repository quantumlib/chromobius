import functools
import pathlib
from typing import Iterable, Callable, Literal, Union

import gen
from gen._core._util import sorted_complex, min_max_complex
from gen._core._tile import Tile
from gen._util import write_file


DESIRED_Z_TO_ORIENTATION: dict[str, str] = {
    "X": "ZX",
    "Y": "ZY",
    "Z": "XZ",
}


class Patch:
    """A collection of annotated stabilizers to measure simultaneously."""

    def __init__(self, tiles: Iterable[Tile], *, do_not_sort: bool = False):
        if do_not_sort:
            self.tiles = tuple(tiles)
        else:
            self.tiles = tuple(sorted_complex(tiles, key=lambda e: e.measurement_qubit))

    def with_edits(
            self,
            *,
            tiles: Iterable[Tile] | None = None,
    ) -> 'Patch':
        return gen.Patch(
            tiles=self.tiles if tiles is None else tiles,
        )

    def with_transformed_coords(
        self, coord_transform: Callable[[complex], complex]
    ) -> "Patch":
        return Patch(
            [e.with_transformed_coords(coord_transform) for e in self.tiles],
        )

    def after_basis_transform(
        self,
        basis_transform: Callable[[Literal["X", "Y", "Z"]], Literal["X", "Y", "Z"]],
    ) -> "Patch":
        return Patch(
            [e.after_basis_transform(basis_transform) for e in self.tiles],
        )

    def with_only_x_tiles(self) -> "Patch":
        return Patch([tile for tile in self.tiles if tile.basis == "X"])

    def with_only_y_tiles(self) -> "Patch":
        return Patch([tile for tile in self.tiles if tile.basis == "Y"])

    def with_only_z_tiles(self) -> "Patch":
        return Patch([tile for tile in self.tiles if tile.basis == "Z"])

    def without_wraparound_tiles(self) -> "Patch":
        p_min, p_max = min_max_complex(self.data_set, default=0)
        w = p_max.real - p_min.real
        h = p_max.imag - p_min.imag
        left = p_min.real + w * 0.1
        right = p_min.real + w * 0.9
        top = p_min.imag + h * 0.1
        bot = p_min.imag + h * 0.9

        def keep_tile(tile: Tile) -> bool:
            t_min, t_max = min_max_complex(tile.data_set, default=0)
            if t_min.real < left and t_max.real > right:
                return False
            if t_min.imag < top and t_max.imag > bot:
                return False
            return True

        return Patch([t for t in self.tiles if keep_tile(t)])

    @functools.cached_property
    def m2tile(self) -> dict[complex, Tile]:
        return {e.measurement_qubit: e for e in self.tiles}

    def with_opposite_order(self) -> "Patch":
        return Patch(
            tiles=[
                Tile(
                    bases=tile.bases[::-1],
                    measurement_qubit=tile.measurement_qubit,
                    ordered_data_qubits=tile.ordered_data_qubits[::-1],
                )
                for tile in self.tiles
            ]
        )

    def write_svg(
        self,
        path: str | pathlib.Path,
        *,
        other: Union['gen.Patch', 'gen.StabilizerCode', Iterable[Union['gen.Patch', 'gen.StabilizerCode']]] = (),
        show_order: bool | Literal["undirected", "3couplerspecial"] = False,
        show_measure_qubits: bool = False,
        show_data_qubits: bool = False,
        expected_points: Iterable[complex] = (),
        show_coords: bool = True,
        opacity: float = 1,
        show_obs: bool = False,
        rows: int | None = None,
        cols: int | None = None,
        tile_color_func: Callable[[Tile], str] | None = None
    ) -> None:
        from gen._viz_patch_svg import patch_svg_viewer

        from gen._core._stabilizer_code import StabilizerCode
        patches = [self] + ([other] if isinstance(other, (Patch, StabilizerCode)) else list(other))

        viewer = patch_svg_viewer(
            patches=patches,
            show_measure_qubits=show_measure_qubits,
            show_data_qubits=show_data_qubits,
            show_order=show_order,
            expected_points=expected_points,
            opacity=opacity,
            show_coords=show_coords,
            show_obs=show_obs,
            rows=rows,
            cols=cols,
            tile_color_func=tile_color_func,
        )
        write_file(path, viewer)

    def with_xz_flipped(self) -> "Patch":
        trans = {"X": "Z", "Y": "Y", "Z": "X"}
        return self.after_basis_transform(trans.__getitem__)

    @functools.cached_property
    def used_set(self) -> frozenset[complex]:
        result = set()
        for e in self.tiles:
            result |= e.used_set
        return frozenset(result)

    @functools.cached_property
    def data_set(self) -> frozenset[complex]:
        result = set()
        for e in self.tiles:
            for q in e.ordered_data_qubits:
                if q is not None:
                    result.add(q)
        return frozenset(result)

    def __eq__(self, other):
        if not isinstance(other, Patch):
            return NotImplemented
        return self.tiles == other.tiles

    def __ne__(self, other):
        return not (self == other)

    @functools.cached_property
    def measure_set(self) -> frozenset[complex]:
        return frozenset(e.measurement_qubit for e in self.tiles)

    def __repr__(self):
        return "\n".join(
            [
                "gen.Patch(tiles=[",
                *[f"    {e!r},".replace("\n", "\n    ") for e in self.tiles],
                "])",
            ]
        )

    def with_reverse_order(self) -> "Patch":
        return Patch(
            tiles=[
                Tile(
                    bases=plaq.bases[::-1],
                    measurement_qubit=plaq.measurement_qubit,
                    ordered_data_qubits=plaq.ordered_data_qubits[::-1],
                )
                for plaq in self.tiles
            ],
        )
