// Copyright 2023 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "chromobius/graph/collect_composite_errors.h"

#include "chromobius/graph/collect_atomic_errors.h"

using namespace chromobius;

void chromobius::collect_composite_errors_and_remnants_into_mobius_dem(
    const stim::DetectorErrorModel &dem,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    bool drop_mobius_errors_involving_remnant_errors,
    bool ignore_decomposition_failures,
    stim::DetectorErrorModel *out_mobius_dem,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {

    stim::SparseXorVec<node_offset_int> dets;
    std::vector<node_offset_int> x_buf;
    std::vector<node_offset_int> z_buf;
    std::vector<AtomicErrorKey> atoms_buf;
    std::vector<stim::DemTarget> composite_error_buffer;

    dem.iter_flatten_error_instructions([&](stim::DemInstruction inst) {
        xxx22(
            dem,
            node_colors,
            atomic_errors,
            drop_mobius_errors_involving_remnant_errors,
            ignore_decomposition_failures,
            out_mobius_dem,
            out_remnants,
            dets, x_buf, z_buf, atoms_buf, composite_error_buffer, inst);
    });
}
