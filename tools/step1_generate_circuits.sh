#!/bin/bash
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


set -e
set -o pipefail

parallel --ungroup ./tools/gen_circuits \
    --style {1} \
    --out_dir out/circuits_matchable \
    --noise_model uniform \
    --rounds "d*4" \
    --diameter {2} \
    --noise_strength 0.001 \
    ::: surface_code_X surface_code_Z \
    ::: 3 5 7 9 11 13


parallel --ungroup ./tools/gen_circuits \
    --style {1} \
    --out_dir out/circuits_unmatchable \
    --noise_model uniform \
    --rounds "d*4" \
    --diameter {2} \
    --noise_strength 0.001 \
    ::: midout_color_code_488_X midout_color_code_488_Z \
    ::: 3 5 7 9 11 13 15 17 19


parallel --ungroup ./tools/gen_circuits \
    --style {1} \
    --out_dir out/circuits_unmatchable \
    --noise_model uniform \
    --rounds "d*4" \
    --diameter {2} \
    --noise_strength {3} \
    ::: midout_color_code_X midout_color_code_Z superdense_color_code_X superdense_color_code_Z \
    ::: 3 5 7 9 11 13 15 17 19 \
    ::: 0.0001 0.0002 0.0003 0.0005 0.0007 0.001 0.002 0.003 0.005 0.006 0.007 0.008 0.01


parallel --ungroup ./tools/gen_circuits \
    --style {1} \
    --out_dir out/circuits_unmatchable \
    --noise_model uniform \
    --rounds "d*4" \
    --diameter {2} \
    --noise_strength 0.01 \
    ::: phenom_toric_color_code \
    ::: 6 12 18 24
parallel --ungroup ./tools/gen_circuits \
    --style {1} \
    --out_dir out/circuits_matchable \
    --noise_model uniform \
    --rounds "d*4" \
    --diameter {2} \
    --noise_strength 0.01 \
    ::: phenom_ablated_toric_color_code \
    ::: 6 12 18 24


parallel --ungroup ./tools/gen_circuits \
    --style {1} \
    --out_dir out/circuits_unmatchable \
    --noise_model uniform \
    --rounds "d*4" \
    --diameter {2} \
    --noise_strength 0.01 \
    ::: phenom_rep_code phenom_surface_code phenom_color_code phenom_pyramid_code phenom_color_code_488 phenom_color2surface_code \
    ::: 3 5 7 9 11 13


parallel --ungroup ./tools/gen_circuits \
    --style transit_color_code \
    --out_dir out/circuits_unmatchable \
    --noise_model bitflip \
    --rounds 1 \
    --diameter {1} \
    --noise_strength {2} \
    ::: 11 15 19 23 27 31 \
    ::: 0.01 0.02 0.03 0.04 0.05 0.06 0.07 0.08 0.09 0.1
