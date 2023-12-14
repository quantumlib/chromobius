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

bool chromobius::decompose_single_basis_dets_into_atoms_helper_n6(
    std::span<const node_offset_int> dets,
    obsmask_int obs_flip,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    std::vector<AtomicErrorKey> *out_atoms,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {
    int best_score = 0;

    // 3:3 decomposition.
    for (size_t k1 = 0; k1 < dets.size() && best_score < 2; k1++) {
        for (size_t k2 = k1 + 1; k2 < dets.size(); k2++) {
            for (size_t k3 = k2 + 1; k3 < dets.size(); k3++) {
                try_grow_decomposition(
                    AtomicErrorKey{dets[k1], dets[k2], dets[k3]},
                    AtomicErrorKey{
                        dets[0 + (k1 <= 0) + (k2 <= 0) + (k3 <= 0)],
                        dets[1 + (k1 <= 1) + (k2 <= 1) + (k3 <= 1)],
                        dets[2 + (k1 <= 2) + (k2 <= 2) + (k3 <= 2)],
                    },
                    node_colors,
                    atomic_errors,
                    out_atoms,
                    best_score);
            }
        }
    }

    return try_finish_decomposition(best_score, obs_flip, atomic_errors, out_atoms, out_remnants);
}
