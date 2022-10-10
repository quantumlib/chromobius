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

mkdir -p assets

./tools/fuse_xz_data --stats assets/stats.csv > assets/generated/stats-xz-combo.csv

./tools/sinter_plot_print \
    --title "Ignoring 1/3 of detectors slightly improves accuracy on the torus" \
    --in assets/stats.csv \
    --x_func "m.d" \
    --xaxis "Patch Diameter (d)" \
    --out "assets/generated/toric.png" \
    --group_func "f'''{'drop_1/3_detectors' if 'ablated' in m.c else 'all_detectors_kept'} decoder={decoder}'''" \
    --subtitle "code=toric_color_code, rounds=4d, noise=phenom, p=0.01" \
    --filter_func "m.r == m.d * 4 and abs(m.p - 0.01) < 1e-5 and 'phenom' in m.c and 'toric' in m.c" \
    --ymin 1e-12 \
    --failure_unit_name "round" \
    --failure_units_per_shot_func m.r \
    --failure_values_func "2" \
    &

for BASIS in X Z XZ; do
  NUM_OBS=1
  if [ "${BASIS}" = "XZ" ]; then
    NUM_OBS=2
  fi
  ./tools/sinter_plot_print \
      --title "Comparing color code and surface code circuits" \
      --in "assets/generated/stats-xz-combo.csv" \
      --x_func "m.q" \
      --xaxis "[sqrt]Total Qubits (sqrt scale)" \
      --out "assets/generated/compare_${BASIS}.png" \
      --group_func "f'''c={m.c} decoder={decoder}'''" \
      --subtitle "rounds=4d, gates=css, noise=uniform, p=0.001" \
      --line_fits \
      --xmax 1500 \
      --filter_func "m.r == m.d * 4 and abs(m.p - 0.001) < 1e-5 and m.c in ['surface_code_${BASIS}', 'midout_color_code_${BASIS}', 'midout_color_code_488_${BASIS}', 'superdense_color_code_${BASIS}']" \
      --ymin 1e-12 \
      --failure_unit_name "round" \
      --failure_units_per_shot_func m.r \
      --failure_values_func "${NUM_OBS}" \
      &

  ./tools/sinter_plot_print \
      --title "Footprint of middle-out color code circuits" \
      --in "assets/generated/stats-xz-combo.csv" \
      --x_func "m.q" \
      --xaxis "[sqrt]Total Qubits (sqrt scale)" \
      --out "assets/generated/midout_footprint_${BASIS}.png" \
      --group_func "f'''noise strength (p) = {m.p}'''" \
      --xmin 0 \
      --xmax 1500 \
      --subtitle "rounds=4d, gates=css, noise=uniform, decoder=chromobius, circuit=midout_color_code_${BASIS}" \
      --line_fits \
      --filter_func "m.r == m.d * 4 and m.c in ['midout_color_code_${BASIS}']" \
      --ymin 1e-12 \
      --failure_unit_name "round" \
      --failure_units_per_shot_func m.r \
      --failure_values_func "${NUM_OBS}" \
      &


  ./tools/sinter_plot_print \
      --title "Error rates of middle-out Color Code Circuit" \
      --in "assets/generated/stats-xz-combo.csv" \
      --x_func "m.p" \
      --xaxis "[log]Noise Strength (p)" \
      --out "assets/generated/midout_error_${BASIS}.png" \
      --group_func "f'''patch base width = {m.d}, total qubits = {m.q}'''" \
      --subtitle "rounds=4d, gates=css, noise=uniform, decoder=chromobius, circuit=midout_color_code_${BASIS}" \
      --filter_func "m.r == m.d * 4 and m.c in ['midout_color_code_${BASIS}']" \
      --ymin 1e-12 \
      --failure_unit_name "round" \
      --failure_units_per_shot_func m.r \
      --failure_values_func "${NUM_OBS}" \
      &


  ./tools/sinter_plot_print \
      --title "Footprint of superdense color code circuits" \
      --in "assets/generated/stats-xz-combo.csv" \
      --x_func "m.q" \
      --xaxis "[sqrt]Total Qubits (sqrt scale)" \
      --out "assets/generated/superdense_footprint_${BASIS}.png" \
      --group_func "f'''noise strength (p) = {m.p}'''" \
      --xmin 0 \
      --xmax 1500 \
      --subtitle "rounds=4d, gates=css, noise=uniform, decoder=chromobius, circuit=superdense_color_code_${BASIS}" \
      --line_fits \
      --filter_func "m.r == m.d * 4 and m.c in ['superdense_color_code_${BASIS}']" \
      --ymin 1e-12 \
      --failure_unit_name "round" \
      --failure_units_per_shot_func m.r \
      --failure_values_func "${NUM_OBS}" \
      &

  ./tools/sinter_plot_print \
      --title "Error rates of superdense color code circuits" \
      --in "assets/generated/stats-xz-combo.csv" \
      --x_func "m.p" \
      --xaxis "[log]Noise Strength (p)" \
      --out "assets/generated/superdense_error_${BASIS}.png" \
      --group_func "f'''patch base width = {m.d}, total qubits = {m.q}'''" \
      --subtitle "rounds=4d, gates=css, noise=uniform, decoder=chromobius, circuit=superdense_color_code_${BASIS}" \
      --filter_func "m.r == m.d * 4 and m.c in ['superdense_color_code_${BASIS}']" \
      --ymin 1e-12 \
      --failure_unit_name "round" \
      --failure_units_per_shot_func m.r \
      --failure_values_func "${NUM_OBS}" \
      &
done

./tools/sinter_plot_print \
    --title "Decoding various planar codes under phenomenological noise" \
    --in assets/stats.csv \
    --x_func "m.q" \
    --xaxis "[sqrt]Data Qubits (sqrt scale)" \
    --out "assets/generated/phenom.png" \
    --line_fits \
    --group_func "f'''{m.c}'''" \
    --subtitle "rounds=4d, noise=phenom, decoder=chromobius, p=0.01" \
    --filter_func "m.r == m.d * 4 and abs(m.p - 0.01) < 1e-5 and 'phenom' in m.c and 'toric' not in m.c" \
    --ymin 1e-12 \
    --failure_unit_name "round" \
    --failure_units_per_shot_func m.r \
    --failure_values_func "1" \
    &


./tools/sinter_plot_print \
    --title "Reproduce code capacity noise" \
    --in assets/stats.csv \
    --x_func "m.p" \
    --xaxis "[log]Bit Flip Noise Strength" \
    --out "assets/generated/cmp_transit.png" \
    --group_func "f'''c={m.c} d={m.d}'''" \
    --subtitle "{common}" \
    --filter_func "m.c == 'transit_color_code'" \
    --plot_args_func "{'color': 'C' + str({1: 4, 2: 1, 4: 5, 5: 2}.get(index, index))}" \
    --ymin 1e-12 \
    &


wait
