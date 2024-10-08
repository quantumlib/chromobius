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
from clorco.color2surface_code._color2surface_layouts import make_color2surface_layout
from clorco.color2surface_code._color2surface_layouts import rgb2xyz


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


def make_named_color2surface_code_constructions() -> (
    dict[str, Callable[[Params], stim.Circuit]]
):
    constructions: dict[str, Callable[[Params], stim.Circuit]] = {}

    def _make_simple_circuit(
        params: Params, *, code: gen.StabilizerCode, phenom: bool
    ) -> stim.Circuit:
        if params.debug_out_dir is not None:
            code.patch.write_svg(
                params.debug_out_dir / "rgb_patch.svg",
                other=[rgb2xyz(code.patch, "X"), rgb2xyz(code.patch, "Z")],
                opacity=0.8,
            )
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

    constructions["transit_color2surface_code"] = lambda params: _make_simple_circuit(
        params=params,
        code=make_color2surface_layout(
            base_data_width=params.diameter,
        ),
        phenom=False,
    )
    constructions["phenom_color2surface_code"] = lambda params: _make_simple_circuit(
        params=params,
        code=make_color2surface_layout(
            base_data_width=params.diameter,
        ),
        phenom=True,
    )

    return constructions
