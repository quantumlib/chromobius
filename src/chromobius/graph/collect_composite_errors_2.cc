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

void chromobius::decompose_dets_into_atoms(
    std::span<const node_offset_int> dets,
    obsmask_int obs_flip,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    bool ignore_decomposition_failures,
    std::vector<node_offset_int> *buf_x_detectors,
    std::vector<node_offset_int> *buf_z_detectors,
    const stim::DemInstruction &instruction_for_error_message,
    const stim::DetectorErrorModel *dem_for_error_message,
    std::vector<AtomicErrorKey> *out_atoms,
    std::map<AtomicErrorKey, obsmask_int> *out_remnants) {
    // Split into X and Z parts.
    buf_x_detectors->clear();
    buf_z_detectors->clear();
    for (const auto &t : dets) {
        auto cb = node_colors[t];
        int c = (int)cb.color - 1;
        int b = (int)cb.basis - 1;
        if (c < 0 || c >= 3 || b < 0 || b >= 2) {
            std::stringstream ss;
            ss << "Detector D" << t << " originating from instruction (after shifting) '"
               << instruction_for_error_message << "'";
            ss << " is missing coordinate data indicating its color and basis.\n";
            ss << "Every detector used in an error must have a 4th coordinate in "
                  "[0,6) where RedX=0, GreenX=1, BlueX=2, RedZ=3, GreenZ=4, BlueZ=5.";
            throw std::invalid_argument(ss.str());
        }
        if (b == 0) {
            buf_x_detectors->push_back(t);
        } else {
            buf_z_detectors->push_back(t);
        }
    }

    // Split into atomic errors.
    out_atoms->clear();
    bool x_worked = decompose_single_basis_dets_into_atoms(
        *buf_x_detectors, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
    bool z_worked = decompose_single_basis_dets_into_atoms(
        *buf_z_detectors, obs_flip, node_colors, atomic_errors, out_atoms, out_remnants);
    if (!(x_worked && z_worked) && !ignore_decomposition_failures) {
        std::stringstream ss;
        ss << "Failed to decompose a complex error instruction into basic errors.\n";
        ss << "    The instruction (after shifting): " + instruction_for_error_message.str() << "\n";
        if (!x_worked) {
            ss << "    The undecomposed X detectors: [" << stim::comma_sep(*buf_x_detectors) << "]\n";
        }
        if (!z_worked) {
            ss << "    The undecomposed Z detectors: [" << stim::comma_sep(*buf_z_detectors) << "]\n";
        }
        ss << "    Detector data:\n";
        std::set<uint64_t> ds;
        for (const auto &t : instruction_for_error_message.target_data) {
            if (t.is_relative_detector_id()) {
                ds.insert(t.raw_id());
            }
        }
        std::map<uint64_t, std::vector<double>> coords;
        if (dem_for_error_message != nullptr) {
            coords = dem_for_error_message->get_detector_coordinates(ds);
        }
        for (const auto &t : instruction_for_error_message.target_data) {
            if (t.is_relative_detector_id()) {
                auto d = t.raw_id();
                ss << "        " << t << ": coords=[" << stim::comma_sep(coords[d]) << "] " << node_colors[d] << "\n";
            }
        }
        ss << "This problem can unfortunately be quite difficult to debug. Likely causes are:\n";
        ss << "    (1) The source circuit has detectors with invalid color/basis annotations.\n";
        ss << "    (2) The source circuit is producing errors too complex to decompose (e.g. more than 6 symptoms in "
              "one basis).\n";
        ss << "    (3) chromobius is missing logic for a corner case present in the source circuit; a corner case that "
              "didn't appear in the test circuits used during development.\n";
        throw std::invalid_argument(ss.str());
    }
}
