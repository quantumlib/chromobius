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

import stim

import gen
from clorco._make_circuit_params import Params
from clorco.surface_code._surface_code_layouts import (
    make_surface_code_layout,
    make_toric_surface_code_layout,
)
from clorco.surface_code._transversal_cnot import (
    make_transversal_cnot_surface_code_circuit,
)
from clorco.surface_code._xz_surface_code_memory_circuits import (
    make_xz_memory_experiment_chunks,
)


def make_named_surface_code_constructions() -> (
    dict[str, Callable[[Params], stim.Circuit]]
):
    constructions: dict[str, Callable[[Params], stim.Circuit]] = {
        **_simplified_noise_surface_code_constructions(),
    }

    constructions["surface_code_X"] = lambda params: _chunks_to_circuit(
        params,
        make_xz_memory_experiment_chunks(
            basis="X",
            diameter=params.diameter,
            rounds=params.rounds,
        ),
    )
    constructions["surface_code_Z"] = lambda params: _chunks_to_circuit(
        params,
        make_xz_memory_experiment_chunks(
            basis="Z",
            diameter=params.diameter,
            rounds=params.rounds,
        ),
    )

    constructions[
        "surface_code_trans_cx_X"
    ] = lambda params: make_transversal_cnot_surface_code_circuit(
        diameter=params.diameter,
        basis="X",
        pad_rounds=params.rounds,
        noise=params.noise_model,
        convert_to_z=params.convert_to_cz,
    )
    constructions[
        "surface_code_trans_cx_Z"
    ] = lambda params: make_transversal_cnot_surface_code_circuit(
        diameter=params.diameter,
        basis="Z",
        pad_rounds=params.rounds,
        noise=params.noise_model,
        convert_to_z=params.convert_to_cz,
    )
    constructions[
        "surface_code_trans_cx_magicEPR"
    ] = lambda params: make_transversal_cnot_surface_code_circuit(
        diameter=params.diameter,
        basis="MagicEPR",
        pad_rounds=params.rounds,
        noise=params.noise_model,
        convert_to_z=params.convert_to_cz,
    )

    return constructions


def f2c(flow: gen.Flow) -> list[float]:
    c = 0
    if 'color=r' in flow.flags:
        c += 0
    elif 'color=g' in flow.flags:
        c += 1
    elif 'color=b' in flow.flags:
        c += 2
    else:
        raise NotImplementedError(f'{flow=}')
    if 'basis=X' in flow.flags:
        c += 0
    elif 'basis=Z' in flow.flags:
        c += 3
    else:
        raise NotImplementedError(f'{flow=}')
    return [c]


def _chunks_to_circuit(params: Params, chunks: list[gen.Chunk]) -> stim.Circuit:
    assert len(chunks) >= 2
    if "magic" not in params.style:
        assert not any(inst.name == 'MPP' for chunk in chunks if isinstance(chunk, gen.Chunk) for inst in chunk.circuit)

    if params.debug_out_dir is not None:
        patches = [chunk.end_interface().to_patch() for chunk in chunks[:-1]]
        changed_patches = [
            patches[k]
            for k in range(len(patches))
            if k == 0 or patches[k] != patches[k - 1]
        ]
        allowed_qubits = {q for patch in changed_patches for q in patch.used_set}
        gen.write_file(
            params.debug_out_dir / "patch.svg",
            gen.patch_svg_viewer(
                changed_patches,
                show_order=False,
                expected_points=allowed_qubits,
            ),
        )

    if params.debug_out_dir is not None:
        ignore_errors_ideal_circuit = gen.compile_chunks_into_circuit(
            chunks, ignore_errors=True
        )
        patch_dict = {}
        cur_tick = 0
        last_patch = gen.Patch([])
        if chunks[0].start_interface().to_patch() != last_patch:
            patch_dict[0] = chunks[0].start_interface().to_patch()
            last_patch = chunks[0].start_interface().to_patch()
            cur_tick += 1

        for c in gen.ChunkLoop(chunks, repetitions=1).flattened():
            cur_tick += c.tick_count()
            if c.end_interface().to_patch() != last_patch:
                patch_dict[cur_tick] = c.end_interface().to_patch()
                last_patch = c.end_interface().to_patch()
                cur_tick += 1
        gen.write_file(
            params.debug_out_dir / "ideal_circuit.html",
            gen.stim_circuit_html_viewer(
                ignore_errors_ideal_circuit,
                patch=patch_dict,
            ),
        )
        gen.write_file(
            params.debug_out_dir / "ideal_circuit.stim", ignore_errors_ideal_circuit
        )
        gen.write_file(
            params.debug_out_dir / "ideal_circuit_dets.svg",
            ignore_errors_ideal_circuit.diagram("time+detector-slice-svg"),
        )

    body = gen.compile_chunks_into_circuit(chunks, flow_to_extra_coords_func=f2c)

    if params.convert_to_cz:
        body = gen.transpile_to_z_basis_interaction_circuit(body)
        if params.debug_out_dir is not None:
            gen.write_file(
                params.debug_out_dir / "ideal_cz_circuit.html",
                gen.stim_circuit_html_viewer(
                    body,
                    patch=chunks[0].end_interface().to_patch(),
                ),
            )
            gen.write_file(
                params.debug_out_dir / "ideal_cz_circuit.stim", body
            )
            gen.write_file(
                params.debug_out_dir / "ideal_cz_circuit_dets.svg",
                body.diagram("time+detector-slice-svg"),
            )

    if params.noise_model is not None:
        body = params.noise_model.noisy_circuit_skipping_mpp_boundaries(body)

    if params.debug_out_dir is not None:
        gen.write_file(
            params.debug_out_dir / "noisy_circuit.html",
            gen.stim_circuit_html_viewer(
                body,
                patch=chunks[0].end_interface().to_patch(),
            ),
        )

    return body


def _simplified_noise_surface_code_constructions() -> (
    dict[str, Callable[[Params], stim.Circuit]]
):
    constructions: dict[str, Callable[[Params], stim.Circuit]] = {}

    def _make_simple_circuit(
        params: Params, *, code: gen.StabilizerCode, phenom: bool
    ) -> stim.Circuit:
        if phenom:
            return code.make_phenom_circuit(
                noise=params.noise_model.idle_depolarization,
                rounds=params.rounds,
                extra_coords_func=f2c,
            )
        assert params.rounds == 1
        return code.make_code_capacity_circuit(
            noise=params.noise_model.idle_depolarization,
            extra_coords_func=f2c,
        )

    constructions["transit_surface_code"] = lambda params: _make_simple_circuit(
        params=params,
        code=make_surface_code_layout(
            width=params.diameter,
            height=params.diameter,
        ),
        phenom=False,
    )
    constructions["phenom_surface_code"] = lambda params: _make_simple_circuit(
        params=params,
        code=make_surface_code_layout(
            width=params.diameter,
            height=params.diameter,
        ),
        phenom=True,
    )
    constructions["transit_toric_surface_code"] = lambda params: _make_simple_circuit(
        params=params,
        code=make_toric_surface_code_layout(
            width=params.diameter,
            height=params.diameter,
        ),
        phenom=False,
    )
    constructions["phenom_toric_surface_code"] = lambda params: _make_simple_circuit(
        params=params,
        code=make_toric_surface_code_layout(
            width=params.diameter,
            height=params.diameter,
        ),
        phenom=True,
    )
    return constructions
