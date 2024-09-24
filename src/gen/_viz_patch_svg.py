import collections
import math
from typing import Iterable, Union, TYPE_CHECKING, Sequence, Callable, \
    Any

from gen._core._util import min_max_complex

if TYPE_CHECKING:
    import gen


def is_collinear(a: complex, b: complex, c: complex) -> bool:
    d1 = b - a
    d2 = c - a
    return abs(d1.real * d2.imag - d2.real * d1.imag) < 1e-4


def _path_commands_for_points_with_one_point(
    *,
    a: complex,
    draw_coord: Callable[[complex], complex],
    draw_radius: float | None = None,
):
    draw_a = draw_coord(a)
    if draw_radius is None:
        draw_radius = abs(draw_coord(0.2) - draw_coord(0))
    r = draw_radius
    left = draw_a - draw_radius
    return [
        f"""M {left.real},{left.imag}""",
        f"""a {r},{r} 0 0,0 {2*r},{0}""",
        f"""a {r},{r} 0 0,0 {-2*r},{0}""",
    ]


def _path_commands_for_points_with_two_points(
    *,
    a: complex,
    b: complex,
    hint_point: complex,
    draw_coord: Callable[[complex], complex],
) -> list[str]:
    def transform_dif(d: complex) -> complex:
        return draw_coord(d) - draw_coord(0)

    da = a - hint_point
    db = b - hint_point
    angle = math.atan2(da.imag, da.real) - math.atan2(db.imag, db.real)
    angle %= math.pi * 2
    if angle < math.pi:
        a, b = b, a

    if abs(abs(da) - abs(db)) < 1e-4 < abs(da + db):
        # Semi-circle oriented towards measure qubit.
        draw_a = draw_coord(a)
        draw_ba = transform_dif(b - a)
        return [
            f"""M {draw_a.real},{draw_a.imag}""",
            f"""a 1,1 0 0,0 {draw_ba.real},{draw_ba.imag}""",
            f"""L {draw_a.real},{draw_a.imag}""",
        ]
    else:
        # A wedge between the two data qubits.
        dif = b - a
        average = (a + b) * 0.5
        perp = dif * 1j
        if abs(perp) > 1:
            perp /= abs(perp)
        ac1 = average + perp * 0.2 - dif * 0.2
        ac2 = average + perp * 0.2 + dif * 0.2
        bc1 = average + perp * -0.2 + dif * 0.2
        bc2 = average + perp * -0.2 - dif * 0.2

        tac1 = draw_coord(ac1)
        tac2 = draw_coord(ac2)
        tbc1 = draw_coord(bc1)
        tbc2 = draw_coord(bc2)
        draw_a = draw_coord(a)
        draw_b = draw_coord(b)
        return [
            f"M {draw_a.real},{draw_a.imag}",
            f"C {tac1.real} {tac1.imag}, {tac2.real} {tac2.imag}, {draw_b.real} {draw_b.imag}",
            f"C {tbc1.real} {tbc1.imag}, {tbc2.real} {tbc2.imag}, {draw_a.real} {draw_a.imag}",
        ]


def _path_commands_for_points_with_many_points(
    *,
    pts: Sequence[complex],
    draw_coord: Callable[[complex], complex],
) -> list[str]:
    assert len(pts) >= 3
    ori = draw_coord(pts[-1])
    path_commands = [f"""M{ori.real},{ori.imag}"""]
    for k in range(len(pts)):
        prev_prev_q = pts[k - 2]
        prev_q = pts[k - 1]
        q = pts[k]
        next_q = pts[(k + 1) % len(pts)]
        if is_collinear(prev_q, q, next_q) or is_collinear(prev_prev_q, prev_q, q):
            prev_pt = draw_coord(prev_q)
            cur_pt = draw_coord(q)
            d = cur_pt - prev_pt
            p1 = prev_pt + d * (-0.25 + 0.05j)
            p2 = cur_pt + d * (0.25 + 0.05j)
            path_commands.append(
                f"""C {p1.real} {p1.imag}, {p2.real} {p2.imag}, {cur_pt.real} {cur_pt.imag}"""
            )
        else:
            q2 = draw_coord(q)
            path_commands.append(f"""L {q2.real},{q2.imag}""")
    return path_commands


def svg_path_directions_for_tile(
    *, tile: "gen.Tile", draw_coord: Callable[[complex], complex], contract_towards: complex | None = None,
) -> str | None:
    hint_point = tile.measurement_qubit
    if any(abs(q - hint_point) < 1e-4 for q in tile.data_set):
        hint_point = sum(tile.data_set) / len(tile.data_set)

    points = sorted(
        tile.data_set,
        key=lambda p2: math.atan2(p2.imag - hint_point.imag, p2.real - hint_point.real),
    )

    if len(points) == 0:
        return None

    if len(points) == 1:
        return " ".join(
            _path_commands_for_points_with_one_point(
                a=points[0],
                draw_coord=draw_coord,
            )
        )

    if len(points) == 2:
        return " ".join(
            _path_commands_for_points_with_two_points(
                a=points[0],
                b=points[1],
                hint_point=hint_point,
                draw_coord=draw_coord,
            )
        )

    if contract_towards is not None:
        c = 0.85
        points = [p*c + (1-c)*contract_towards for p in points]

    return " ".join(
        _path_commands_for_points_with_many_points(
            pts=points,
            draw_coord=draw_coord,
        )
    )


def _draw_patch(
        *,
        patch: Union['gen.Patch', 'gen.StabilizerCode', 'gen.ChunkInterface'],
        q2p: Callable[[complex], complex],
        show_coords: bool,
        show_obs: bool,
        opacity: float,
        show_data_qubits: bool,
        show_measure_qubits: bool,
        expected_points: frozenset[complex],
        clip_path_id_ptr: list[int],
        out_lines: list[str],
        show_order: bool,
        find_logical_err_max_weight: int | None,
        tile_color_func: Callable[['gen.Tile'], str] | None = None
):
    layer_1q2 = []
    layer_1q = []
    fill_layer2q = []
    fill_layer_mq = []
    stroke_layer_mq = []
    scale_factor = abs(q2p(1) - q2p(0))

    from gen._core._stabilizer_code import StabilizerCode
    from gen._flows._chunk_interface import ChunkInterface
    if isinstance(patch, ChunkInterface):
        patch = patch.to_code()

    labels: list[tuple[complex, str, dict[str, Any]]] = []
    if isinstance(patch, StabilizerCode):
        if find_logical_err_max_weight is not None:
            err = patch.find_logical_error(max_search_weight=find_logical_err_max_weight)
            for e in err:
                for loc in e.circuit_error_locations:
                    for loc2 in loc.flipped_pauli_product:
                        r, i = loc2.coords
                        q = r + 1j*i
                        p = loc2.gate_target.pauli_type
                        labels.append((q, p + '!', {
                            'text-anchor': 'middle',
                            'dominant-baseline': 'central',
                            'font-size': scale_factor * 1.1,
                            'fill': BASE_COLORS_DARK[p],
                        }))

        if show_obs:
            k = 0
            while True:
                if k < 10:
                    suffix = "₀₁₂₃₄₅₆₇₈₉"[k]
                else:
                    suffix = str(k)
                work = False
                if k < len(patch.observables_x):
                    for q, basis2 in patch.observables_x[k].qubits.items():
                        if not patch.observables_z:
                            label = basis2 + suffix
                        elif basis2 != 'X':
                            label = 'X' + suffix + '[' + basis2 + ']'
                        else:
                            label = 'X' + suffix
                        labels.append((q, label, {
                            'text-anchor': 'end',
                            'dominant-baseline': 'hanging',
                            'font-size': scale_factor * 0.6,
                            'fill': BASE_COLORS_DARK[basis2],
                        }))
                    work = True
                if k < len(patch.observables_z):
                    for q, basis2 in patch.observables_z[k].qubits.items():
                        if basis2 != 'Z':
                            basis_suffix = '[' + basis2 + ']'
                        else:
                            basis_suffix = ''
                        labels.append((q, 'Z' + suffix + basis_suffix, {
                            'text-anchor': "start",
                            'dominant-baseline': 'bottom',
                            'font-size': scale_factor * 0.6,
                            'fill': BASE_COLORS_DARK[basis2],
                        }))
                    work = True
                if not work:
                    break
                k += 1
    for q, s, ts in labels:
        loc2 = q2p(q)
        terms = {
            'x': loc2.real,
            'y': loc2.imag,
            **ts,
        }
        layer_1q2.append(
            "<text" + ''.join(f' {key}="{val}"' for key, val in terms.items()) + f">{s}</text>"
        )

    all_points = patch.used_set | expected_points
    if show_coords and all_points:
        all_x = sorted({q.real for q in all_points})
        all_y = sorted({q.imag for q in all_points})
        left = min(all_x) - 1
        top = min(all_y) - 1

        for x in all_x:
            if x == int(x):
                x = int(x)
            loc2 = q2p(x + top*1j)
            stroke_layer_mq.append(
                "<text"
                f' x="{loc2.real}"'
                f' y="{loc2.imag}"'
                ' fill="black"'
                f' font-size="{0.5*scale_factor}"'
                ' text-anchor="middle"'
                ' alignment-baseline="central"'
                f">{x}</text>"
            )
        for y in all_y:
            if y == int(y):
                y = int(y)
            loc2 = q2p(y*1j + left)
            stroke_layer_mq.append(
                "<text"
                f' x="{loc2.real}"'
                f' y="{loc2.imag}"'
                ' fill="black"'
                f' font-size="{0.5*scale_factor}"'
                ' text-anchor="middle"'
                ' alignment-baseline="central"'
                f">{y}i</text>"
            )

    sorted_tiles = sorted(patch.tiles, key=tile_data_span, reverse=True)
    d2tiles = collections.defaultdict(list)

    def contraction_point(tile) -> complex | None:
        if len(tile.data_set) <= 2:
            return None
        for d in tile.data_set:
            for other_tile in d2tiles[d]:
                if other_tile is not tile:
                    if tile.data_set < other_tile.data_set or (tile.data_set == other_tile.data_set and tile.basis < other_tile.basis):
                        return sum(other_tile.data_set) / len(other_tile.data_set)
        return None

    for tile in sorted_tiles:
        for d in tile.data_set:
            d2tiles[d].append(tile)

    for tile in sorted_tiles:
        c = tile.measurement_qubit
        if any(abs(q - c) < 1e-4 for q in tile.data_set):
            c = sum(tile.data_set) / len(tile.data_set)
        dq = sorted(
            tile.data_set,
            key=lambda p2: math.atan2(p2.imag - c.imag, p2.real - c.real),
        )
        if not dq:
            continue
        fill_color = BASE_COLORS[tile.basis]
        if tile_color_func is not None:
            fill_color = tile_color_func(tile)

        if len(tile.data_set) == 1:
            fl = layer_1q
            sl = stroke_layer_mq
        elif len(tile.data_set) == 2:
            fl = fill_layer2q
            sl = stroke_layer_mq
        else:
            fl = fill_layer_mq
            sl = stroke_layer_mq
        cp = contraction_point(tile)
        path_directions = svg_path_directions_for_tile(
            tile=tile,
            draw_coord=q2p,
            contract_towards=cp,
        )
        if path_directions is not None:
            fl.append(
                f'''<path d="{path_directions}"'''
                f''' fill="{fill_color}"'''
                + (f''' opacity="{opacity}"''' * (opacity != 1)) +
                f''' stroke="none"'''
                f''' />'''
            )
            if cp is None:
                sl.append(
                    f'''<path d="{path_directions}"'''
                    f''' fill="none"'''
                    f''' stroke="black"'''
                    f""" stroke-width="{scale_factor * 0.02}" """
                    f""" />"""
                )

        # Add basis glows around data qubits in multi-basis stabilizers.
        if path_directions is not None and tile.basis is None and tile_color_func is None:
            clip_path_id_ptr[0] += 1
            fl.append(f'<clipPath id="clipPath{clip_path_id_ptr[0]}">')
            fl.append(f'''    <path d="{path_directions}" />''')
            fl.append(f"</clipPath>")
            for k, q in enumerate(tile.ordered_data_qubits):
                if q is None:
                    continue
                v = q2p(q)
                fl.append(
                    f"<circle "
                    f'clip-path="url(#clipPath{clip_path_id_ptr[0]})" '
                    f'cx="{v.real}" '
                    f'cy="{v.imag}" '
                    f'r="{scale_factor * 0.45}" '
                    f'fill="{BASE_COLORS[tile.bases[k]]}" '
                    f'stroke="none" />'
                )

        if show_measure_qubits:
            m = tile.measurement_qubit
            loc2 = q2p(m)
            layer_1q2.append(
                f"<circle "
                f'cx="{loc2.real}" '
                f'cy="{loc2.imag}" '
                f'r="{scale_factor * 0.05}" '
                f'fill="black" '
                f'stroke-width="{scale_factor * 0.02}" '
                f"""stroke="black" />"""
            )

        if show_data_qubits:
            for d in tile.data_set:
                loc2 = q2p(d)
                layer_1q2.append(
                    f"<circle "
                    f'cx="{loc2.real}" '
                    f'cy="{loc2.imag}" '
                    f'r="{scale_factor * 0.1}" '
                    f'fill="black" '
                    f"""stroke="none" />"""
                )

        for q in all_points:
            if q not in patch.data_set and q not in patch.measure_set:
                loc2 = q2p(q)
                layer_1q2.append(
                    f"<circle "
                    f'cx="{loc2.real}" '
                    f'cy="{loc2.imag}" '
                    f'r="{scale_factor * 0.1}" '
                    f'fill="black" '
                    f"""stroke="none" />"""
                )

    out_lines += fill_layer_mq
    out_lines += stroke_layer_mq
    out_lines += fill_layer2q
    out_lines += layer_1q
    out_lines += layer_1q2

    # Draw each element's measurement order as a zig zag arrow.
    if show_order:
        for tile in patch.tiles:
            _draw_tile_order_arrow(
                q2p=q2p,
                tile=tile,
                out_lines=out_lines,
            )


BASE_COLORS = {"X": "#FF8080", "Z": "#8080FF", "Y": "#80FF80", None: "gray"}
BASE_COLORS_DARK = {"X": "#B01010", "Z": "#1010B0", "Y": "#10B010", None: "black"}


def tile_data_span(tile: "gen.Tile") -> Any:
    min_c, max_c = min_max_complex(tile.data_set, default=0)
    return max_c.real - min_c.real + max_c.imag - min_c.imag, tile.bases


def _draw_tile_order_arrow(
        *,
        tile: 'gen.Tile',
        q2p: Callable[[complex], complex],
        out_lines: list[str],
):
    scale_factor = abs(q2p(1) - q2p(0))

    c = tile.measurement_qubit
    if len(tile.data_set) == 3 or c in tile.data_set:
        c = 0
        for q in tile.data_set:
            c += q
        c /= len(tile.data_set)
    pts: list[complex] = []

    path_cmd_start = f'<path d="M'
    arrow_color = "black"
    delay = 0
    prev = None
    for q in tile.ordered_data_qubits:
        if q is not None:
            f = 0.6
            v = q * f + c * (1 - f)
            pp = q2p(v)
            path_cmd_start += f"{pp.real},{pp.imag} "
            v = q2p(v)
            pts.append(v)
            for d in range(delay):
                if prev is None:
                    prev = v
                v2 = (prev + v) / 2
                out_lines.append(
                    f'<circle cx="{v2.real}" cy="{v2.imag}" r="{scale_factor * (d * 0.06 + 0.04)}" '
                    f'stroke-width="{scale_factor * 0.02}" '
                    f'stroke="yellow" '
                    f'fill="none" />'
                )
            delay = 0
            prev = v
        else:
            delay += 1
    path_cmd_start = path_cmd_start.strip()
    path_cmd_start += (
        f'" fill="none" '
        f'stroke-width="{scale_factor * 0.02}" '
        f'stroke="{arrow_color}" />'
    )
    out_lines.append(path_cmd_start)

    # Draw arrow at end of arrow.
    if len(pts) > 1:
        p = pts[-1]
        d2 = p - pts[-2]
        if d2:
            d2 /= abs(d2)
            d2 *= 4 * scale_factor * 0.02
        a = p + d2
        b = p + d2 * 1j
        c = p + d2 * -1j
        out_lines.append(
            f"<path"
            f' d="M{a.real},{a.imag} {b.real},{b.imag} {c.real},{c.imag} {a.real},{a.imag}"'
            f' stroke="none"'
            f' fill="{arrow_color}" />'
        )


def patch_svg_viewer(
    patches: Iterable[Union['gen.Patch', 'gen.StabilizerCode', 'gen.ChunkInterface']],
    *,
    canvas_height: int = 500,
    show_order: bool = True,
    show_obs: bool = True,
    opacity: float = 1,
    show_measure_qubits: bool = True,
    show_data_qubits: bool = False,
    expected_points: Iterable[complex] = (),
    extra_used_coords: Iterable[complex] = (),
    show_coords: bool = True,
    find_logical_err_max_weight: int | None = None,
    rows: int | None = None,
    cols: int | None = None,
    tile_color_func: Callable[['gen.Tile'], str] | None = None
) -> str:
    """Returns a picture of the stabilizers measured by various plan."""
    expected_points = frozenset(expected_points)

    extra_used_coords = frozenset(extra_used_coords)
    patches = tuple(patches)
    all_points = {
        q
        for patch in patches
        for q in patch.used_set | expected_points | extra_used_coords
    }
    min_c, max_c = min_max_complex(all_points, default=0)
    min_c -= 1 + 1j
    max_c += 1 + 1j
    if show_coords:
        min_c -= 1 + 1j
    box_width = max_c.real - min_c.real
    box_height = max_c.imag - min_c.imag
    pad = max(box_width, box_height) * 0.1 + 1
    box_x_pitch = box_width + pad
    box_y_pitch = box_height + pad
    if cols is None and rows is None:
        cols = math.ceil(math.sqrt(len(patches)))
        rows = math.ceil(len(patches) / max(1, cols))
    elif cols is None:
        cols = math.ceil(len(patches) / max(1, rows))
    elif rows is None:
        rows = math.ceil(len(patches) / max(1, cols))
    else:
        assert cols * rows >= len(patches)
    total_height = max(1.0, box_y_pitch * rows - pad)
    total_width = max(1.0, box_x_pitch * cols - pad)
    scale_factor = canvas_height / max(total_height, 1)
    canvas_width = int(math.ceil(canvas_height * (total_width / total_height)))

    def patch_q2p(patch_index: int, q: complex) -> complex:
        q -= min_c
        q += box_x_pitch * (patch_index % cols)
        q += box_y_pitch * (patch_index // cols) * 1j
        q *= scale_factor
        return q

    lines = [
        f"""<svg viewBox="0 0 {canvas_width} {canvas_height}" xmlns="http://www.w3.org/2000/svg">"""
    ]

    clip_path_id_ptr = [0]
    for plan_i, plan in enumerate(patches):
        _draw_patch(
            patch=plan,
            q2p=lambda q: patch_q2p(plan_i, q),
            show_coords=show_coords,
            opacity=opacity,
            show_data_qubits=show_data_qubits,
            show_measure_qubits=show_measure_qubits,
            expected_points=expected_points,
            clip_path_id_ptr=clip_path_id_ptr,
            out_lines=lines,
            show_order=show_order,
            show_obs=show_obs,
            find_logical_err_max_weight=find_logical_err_max_weight,
            tile_color_func=tile_color_func,
        )

    # Draw frame outlines
    for outline_index, outline in enumerate(patches):
        a = patch_q2p(outline_index, min_c)
        b = patch_q2p(outline_index, max_c)
        lines.append(
            f'<rect fill="none" stroke="#999" x="{a.real}" y="{a.imag}" width="{(b - a).real}" height="{(b - a).imag}" />'
        )

    lines.append("</svg>")
    return "\n".join(lines)
