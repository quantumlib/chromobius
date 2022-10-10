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

# Get to this script's git repo root.
cd "$( dirname "${BASH_SOURCE[0]}" )"
cd "$(git rev-parse --show-toplevel)"

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style midout_color_code_488_X \
    --noise_model uniform \
    --rounds 33 \
    --diameter 9 \
    --noise_strength 0.001 \
    > test_data/midout488_color_code_d9_r33_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style midout_color_code_X \
    --noise_model uniform \
    --rounds 36 \
    --diameter 9 \
    --noise_strength 0.001 \
    > test_data/midout_color_code_d9_r36_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style midout_color_code_X \
    --noise_model uniform \
    --diameter 25 \
    --rounds 100 \
    --noise_strength 0.001 \
    > test_data/midout_color_code_d25_r100_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style midout_color_code_X \
    --noise_model uniform \
    --diameter 5 \
    --rounds 10 \
    --noise_strength 0.001 \
    > test_data/midout_color_code_d5_r10_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style transit_rep_code \
    --noise_model uniform \
    --diameter 9 \
    --rounds 1 \
    --noise_strength 0.1 \
    > test_data/rep_code_d9_transit_p10.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style transit_rep_code_rg \
    --noise_model uniform \
    --diameter 9 \
    --rounds 1 \
    --noise_strength 0.1 \
    > test_data/rep_code_rg_d9_transit_p10.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style transit_rep_code_rbrrr \
    --noise_model uniform \
    --diameter 9 \
    --rounds 1 \
    --noise_strength 0.1 \
    > test_data/rep_code_rbrrr_d9_transit_p10.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style superdense_color_code_X \
    --noise_model uniform \
    --diameter 5 \
    --rounds 20 \
    --noise_strength 0.001 \
    > test_data/superdense_color_code_d5_r20_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style phenom_color_code \
    --noise_model uniform \
    --diameter 5 \
    --rounds 5 \
    --noise_strength 0.001 \
    > test_data/phenom_color_code_d5_r5_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style surface_code_X \
    --noise_model uniform \
    --diameter 5 \
    --rounds 5 \
    --noise_strength 0.001 \
    > test_data/surface_code_d5_r5_p1000.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style transit_color2surface_code \
    --noise_model uniform \
    --diameter 5 \
    --rounds 1 \
    --noise_strength 0.01 \
    > test_data/color2surface_d5_transit_p100.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style phenom_color2surface_code \
    --noise_model uniform \
    --diameter 7 \
    --rounds 7 \
    --noise_strength 0.01 \
    > test_data/color2surface_d7_phenom_r7_p100.stim &

./tools/gen_circuits \
    --out_dir test_data \
    --stdout \
    --style toric_superdense_color_code_magicEPR \
    --noise_model uniform \
    --diameter 12 \
    --rounds 5 \
    --noise_strength 0.001 \
    > test_data/toric_superdense_color_code_epr_d12_r5_p1000.stim &

wait
