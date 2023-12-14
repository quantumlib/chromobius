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

    dem.iter_flatten_error_instructions([&](stim::DemInstruction instruction) {
        obsmask_int obs_flip;
        extract_obs_and_dets_from_error_instruction(instruction, &dets, &obs_flip);

        decompose_dets_into_atoms(
            dets.sorted_items,
            obs_flip,
            node_colors,
            atomic_errors,
            ignore_decomposition_failures,
            &x_buf,
            &z_buf,
            instruction,
            &dem,
            &atoms_buf,
            out_remnants);

        if (drop_mobius_errors_involving_remnant_errors && !out_remnants->empty()) {
            atoms_buf.clear();
            out_remnants->clear();
        }

        // Convert atomic errors into mobius detection events with decomposition suggestions.
        composite_error_buffer.clear();
        bool has_corner_node = false;
        for (const auto &atom : atoms_buf) {
            has_corner_node |= atom.dets[1] == BOUNDARY_NODE;
            atom.iter_mobius_edges(node_colors, [&](node_offset_int d1, node_offset_int d2) {
                composite_error_buffer.push_back(stim::DemTarget::relative_detector_id(d1));
                composite_error_buffer.push_back(stim::DemTarget::relative_detector_id(d2));
                composite_error_buffer.push_back(stim::DemTarget::separator());
            });
        }

        // Put the composite error into the mobius dem as an error instruction.
        if (!composite_error_buffer.empty()) {
            composite_error_buffer.pop_back();
            double p = instruction.arg_data[0];
            if (has_corner_node) {
                // Corner nodes have edges to themselves that correspond to reaching the boundary in one subgraph
                // and then bouncing back in another subgraph. Accounting for this correctly requires doubling the
                // weight of the edge, which corresponds to squaring the probability.
                p *= p;
            }
            out_mobius_dem->append_error_instruction(p, composite_error_buffer);
        }
    });
}
