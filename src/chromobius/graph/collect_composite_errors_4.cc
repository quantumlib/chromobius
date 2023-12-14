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

bool chromobius::decompose_single_basis_dets_into_atoms_helper_n2(
    std::span<const node_offset_int> dets,
    obsmask_int obs_flip,
    std::span<const ColorBasis> node_colors,
   const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    std::vector<AtomicErrorKey> *out_atoms,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {
    // Check if it's just directly included.
    AtomicErrorKey e{dets[0], dets[1], BOUNDARY_NODE};
    if (atomic_errors.contains(e)) {
        out_atoms->push_back(e);
        return true;
    }

    int best_score = 0;

    // 1:1 decomposition.
    for (size_t k1 = 0; k1 < dets.size(); k1++) {
        try_grow_decomposition(
            AtomicErrorKey{dets[k1], BOUNDARY_NODE, BOUNDARY_NODE},
            AtomicErrorKey{
                dets[0 + (k1 <= 0)],
                BOUNDARY_NODE,
                BOUNDARY_NODE,
            },
            node_colors,
            atomic_errors,
            out_atoms,
            best_score);
    }

    return try_finish_decomposition(best_score, obs_flip, atomic_errors, out_atoms, out_remnants);
}

void chromobius::try_grow_decomposition(
    AtomicErrorKey e1,
    AtomicErrorKey e2,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    std::vector<AtomicErrorKey> *out_atoms,
    int &best_score) {
    bool c1 = atomic_errors.contains(e1);
    bool c2 = atomic_errors.contains(e2);
    int score = c1 + 2 * c2;
    if (score <= best_score) {
        return;
    }
    if (score == 1 && e2.weight() == 3 && e2.net_charge(node_colors) != Charge::NEUTRAL) {
        return;
    }
    if (score == 2 && e1.weight() == 3 && e1.net_charge(node_colors) != Charge::NEUTRAL) {
        return;
    }

    if (best_score > 0) {
        out_atoms->pop_back();
        out_atoms->pop_back();
    }
    out_atoms->push_back(e1);
    out_atoms->push_back(e2);
    best_score = score;
}

bool chromobius::try_finish_decomposition(
    int best_score,
    obsmask_int obs_flip,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    std::vector<AtomicErrorKey> *out_atoms,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {
    assert(best_score == 0 || out_atoms->size() >= 2);
    if (best_score == 1) {
        AtomicErrorKey cur = (*out_atoms)[out_atoms->size() - 2];
        AtomicErrorKey rem = (*out_atoms)[out_atoms->size() - 1];
        (*out_remnants)[rem] = obs_flip ^ atomic_errors.at(cur);
    } else if (best_score == 2) {
        AtomicErrorKey cur = (*out_atoms)[out_atoms->size() - 1];
        AtomicErrorKey rem = (*out_atoms)[out_atoms->size() - 2];
        (*out_remnants)[rem] = obs_flip ^ atomic_errors.at(cur);
    }
    return best_score > 0;
}

bool chromobius::decompose_single_basis_dets_into_atoms_helper_n3(
    std::span<const node_offset_int> dets,
    obsmask_int obs_flip,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    std::vector<AtomicErrorKey> *out_atoms,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {
    // Check if it's just directly included.
    AtomicErrorKey e{dets[0], dets[1], dets[2]};
    if (atomic_errors.contains(e)) {
        out_atoms->push_back(e);
        return true;
    }

    int best_score = 0;

    // 1:2 decomposition.
    for (size_t k1 = 0; k1 < dets.size(); k1++) {
        try_grow_decomposition(
            AtomicErrorKey{dets[k1], BOUNDARY_NODE, BOUNDARY_NODE},
            AtomicErrorKey{
                dets[0 + (k1 <= 0)],
                dets[1 + (k1 <= 1)],
                BOUNDARY_NODE,
            },
            node_colors,
            atomic_errors,
            out_atoms,
            best_score);
    }

    return try_finish_decomposition(best_score, obs_flip, atomic_errors, out_atoms, out_remnants);
}