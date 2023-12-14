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

bool chromobius::decompose_single_basis_dets_into_atoms(
    std::span<const node_offset_int> dets,
    obsmask_int obs_flip,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    std::vector<AtomicErrorKey> *out_atoms,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {
    switch (dets.size()) {
        case 0:
            return true;
        case 1:
            out_atoms->push_back(AtomicErrorKey{dets[0], BOUNDARY_NODE, BOUNDARY_NODE});
            return atomic_errors.contains(out_atoms->back());
        case 2:
            return decompose_single_basis_dets_into_atoms_helper_n2(
                dets, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
        case 3:
            return decompose_single_basis_dets_into_atoms_helper_n3(
                dets, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
        case 4:
            return decompose_single_basis_dets_into_atoms_helper_n4(
                dets, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
        case 5:
            return decompose_single_basis_dets_into_atoms_helper_n5(
                dets, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
        case 6:
            return decompose_single_basis_dets_into_atoms_helper_n6(
                dets, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
        default:
            return false;
    }
}
