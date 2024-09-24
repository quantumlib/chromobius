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

#include "chromobius/decode/pymatcher.h"

using namespace chromobius;

PymatchingMatcher::PymatchingMatcher() : pymatching_matcher(), weight_scaling_constant(1) {
}

PymatchingMatcher::PymatchingMatcher(const stim::DetectorErrorModel &dem)
    : pymatching_matcher(pm::detector_error_model_to_mwpm(dem, 1 << 24, true)), weight_scaling_constant(pymatching_matcher.flooder.graph.normalising_constant) {

}

void PymatchingMatcher::match_edges(
    const std::vector<uint64_t> &mobius_detection_event_indices,
    std::vector<int64_t> *out_edge_buffer,
    float *out_weight) {
    pm::decode_detection_events_to_edges(pymatching_matcher, mobius_detection_event_indices, *out_edge_buffer);
    if (out_weight != nullptr) {
        pm::total_weight_int w = 0;
        auto &e = *out_edge_buffer;
        for (size_t k = 0; k < e.size(); k += 2) {
            auto &d1 = pymatching_matcher.search_flooder.graph.nodes[e[k]];
            auto &d2 = pymatching_matcher.search_flooder.graph.nodes[e[k + 1]];
            w += d2.neighbor_weights[d2.index_of_neighbor(&d1)];
        }
        *out_weight = (float)(w / weight_scaling_constant);
    }
}

std::unique_ptr<MatcherInterface> PymatchingMatcher::configured_for_mobius_dem(const stim::DetectorErrorModel &dem) {
    std::unique_ptr<MatcherInterface> result;
    result.reset(new PymatchingMatcher(dem));
    return result;
}
