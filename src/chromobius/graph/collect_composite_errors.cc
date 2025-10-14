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

static inline void try_grow_decomposition(
    AtomicErrorKey e1,
    AtomicErrorKey e2,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors,
    AtomicErrorKey *out_atom,
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

    *out_atom = c2 ? e2 : e1;
    best_score = score;
}

static AtomicErrorKey decompose_single_basis_dets_into_atoms_helper_n2(
    std::span<const node_offset_int> dets,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors) {

    AtomicErrorKey a1{dets[0], BOUNDARY_NODE, BOUNDARY_NODE};
    AtomicErrorKey a2{dets[0], BOUNDARY_NODE, BOUNDARY_NODE};
    if (atomic_errors.contains(a1)) {
        return a1;
    }
    if (atomic_errors.contains(a2)) {
        return a2;
    }
    return AtomicErrorKey{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};
}

static AtomicErrorKey decompose_single_basis_dets_into_atoms_helper_n3(
    std::span<const node_offset_int> dets,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors) {

    int best_score = 0;
    AtomicErrorKey result{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};

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
            &result,
            best_score);
    }

    return result;
}

static AtomicErrorKey decompose_single_basis_dets_into_atoms_helper_n4(
    std::span<const node_offset_int> dets,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors) {
    int best_score = 0;
    AtomicErrorKey result{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};

    // 2:2 decomposition.
    for (size_t k1 = 0; k1 < dets.size() && best_score < 2; k1++) {
        for (size_t k2 = k1 + 1; k2 < dets.size(); k2++) {
            try_grow_decomposition(
                AtomicErrorKey{dets[k1], dets[k2], BOUNDARY_NODE},
                AtomicErrorKey{
                    dets[0 + (k1 <= 0) + (k2 <= 1)],
                    dets[1 + (k1 <= 1) + (k2 <= 2)],
                    BOUNDARY_NODE,
                },
                node_colors,
                atomic_errors,
                &result,
                best_score);
        }
    }

    // 1:3 decomposition.
    for (size_t k1 = 0; k1 < dets.size(); k1++) {
        try_grow_decomposition(
            AtomicErrorKey{dets[k1], BOUNDARY_NODE, BOUNDARY_NODE},
            AtomicErrorKey{
                dets[0 + (k1 <= 0)],
                dets[1 + (k1 <= 1)],
                dets[2 + (k1 <= 2)],
            },
            node_colors,
            atomic_errors,
            &result,
            best_score);
    }

    return result;
}

static AtomicErrorKey decompose_single_basis_dets_into_atoms_helper_n5(
    std::span<const node_offset_int> dets,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors) {

    int best_score = 0;
    AtomicErrorKey result{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};

    // 2:3 decomposition.
    for (size_t k1 = 0; k1 < dets.size() && best_score < 2; k1++) {
        for (size_t k2 = k1 + 1; k2 < dets.size(); k2++) {
            try_grow_decomposition(
                AtomicErrorKey{dets[k1], dets[k2], BOUNDARY_NODE},
                AtomicErrorKey{
                    dets[0 + (k1 <= 0) + (k2 <= 1)],
                    dets[1 + (k1 <= 1) + (k2 <= 2)],
                    dets[2 + (k1 <= 2) + (k2 <= 3)],
                },
                node_colors,
                atomic_errors,
                &result,
                best_score);
        }
    }

    return result;
}

static AtomicErrorKey decompose_single_basis_dets_into_atoms_helper_n6(
    std::span<const node_offset_int> dets,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors) {

    int best_score = 0;
    AtomicErrorKey result{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};

    // 3:3 decomposition.
    for (size_t k1 = 0; k1 < dets.size() && best_score < 2; k1++) {
        for (size_t k2 = k1 + 1; k2 < dets.size(); k2++) {
            for (size_t k3 = k2 + 1; k3 < dets.size(); k3++) {
                try_grow_decomposition(
                    AtomicErrorKey{dets[k1], dets[k2], dets[k3]},
                    AtomicErrorKey{
                        dets[0 + (k1 <= 0) + (k2 <= 1) + (k3 <= 2)],
                        dets[1 + (k1 <= 1) + (k2 <= 2) + (k3 <= 3)],
                        dets[2 + (k1 <= 2) + (k2 <= 3) + (k3 <= 4)],
                    },
                    node_colors,
                    atomic_errors,
                    &result,
                    best_score);
            }
        }
    }

    return result;
}

static AtomicErrorKey decompose_single_basis_dets_into_atoms(
    std::span<const node_offset_int> dets,
    std::span<const ColorBasis> node_colors,
    const std::map<AtomicErrorKey, obsmask_int> &atomic_errors) {
    if (dets.size() <= 3) {
        AtomicErrorKey solo{dets};
        if (atomic_errors.contains(solo)) {
            return solo;
        }
    }

    switch (dets.size()) {
        case 2:
            return decompose_single_basis_dets_into_atoms_helper_n2(
                dets, atomic_errors);
        case 3:
            return decompose_single_basis_dets_into_atoms_helper_n3(
                dets, node_colors, atomic_errors);
        case 4:
            return decompose_single_basis_dets_into_atoms_helper_n4(
                dets, node_colors, atomic_errors);
        case 5:
            return decompose_single_basis_dets_into_atoms_helper_n5(
                dets, node_colors, atomic_errors);
        case 6:
            return decompose_single_basis_dets_into_atoms_helper_n6(
                dets, node_colors, atomic_errors);
        default:
            // Failed to decompose.
            return AtomicErrorKey{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};
    }
}

static void decompose_dets_into_atoms(
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
        assert(!cb.ignored);
        if (cb.basis == Basis::X) {
            buf_x_detectors->push_back(t);
        } else {
            buf_z_detectors->push_back(t);
        }
    }

    // Split into atomic errors.
    out_atoms->clear();
    for (size_t rep = 0; rep < 3; rep++) {
        for (auto *basis_dets : std::array<std::vector<node_offset_int> *, 2>{buf_x_detectors, buf_z_detectors}) {
            AtomicErrorKey removed{BOUNDARY_NODE, BOUNDARY_NODE, BOUNDARY_NODE};
            if (rep == 2) {
                removed = extract_atomic_errors_from_dem_error_instruction_dets(
                    *basis_dets,
                    obs_flip,
                    node_colors,
                    out_remnants);
            } else {
                removed = decompose_single_basis_dets_into_atoms(*basis_dets, node_colors, atomic_errors);
            }

            auto w = removed.weight();
            if (w) {
                for (size_t k = 0; k < w; k++) {
                    // Remove matching item.
                    for (size_t i = 0; i < basis_dets->size(); i++) {
                        if ((*basis_dets)[i] == removed.dets[k]) {
                            (*basis_dets)[i] = basis_dets->back();
                            basis_dets->pop_back();
                            break;
                        }
                    }
                }
                if (atomic_errors.contains(removed)) {
                    obs_flip ^= atomic_errors.at(removed);
                } else {
                    obs_flip ^= out_remnants->at(removed);
                }
                out_atoms->push_back(removed);
            }
        }
    }
    if ((!buf_x_detectors->empty() || !buf_z_detectors->empty()) && !ignore_decomposition_failures) {
        std::stringstream ss;
        ss << "Failed to decompose a complex error instruction into basic errors.\n";
        ss << "    The instruction (after shifting): " + instruction_for_error_message.str() << "\n";
        ss << "    The undecomposed X detectors: [" << stim::comma_sep(*buf_x_detectors) << "]\n";
        ss << "    The undecomposed Z detectors: [" << stim::comma_sep(*buf_z_detectors) << "]\n";
        for (auto e : *out_atoms) {
            ss << "    Decomposed piece:";
            for (auto d : e.dets) {
                if (d != BOUNDARY_NODE) {
                    ss << " D" << d;
                }
            }
            obsmask_int l = atomic_errors.contains(e) ? atomic_errors.at(e) : out_remnants->at(e);
            for (size_t k = 0; k < sizeof(obsmask_int) * 8; k++) {
                if ((l >> k) & 1) {
                    ss << " L" << k;
                }
            }
            ss << "\n";
        }
        if (obs_flip) {
            ss << "    The undecomposed observable mask:";
            for (size_t k = 0; k < sizeof(obsmask_int) * 8; k++) {
                if ((obs_flip >> k) & 1) {
                    ss << " L" << k;
                }
            }
            ss << "\n";
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
        extract_obs_and_dets_from_error_instruction(instruction, &dets, &obs_flip, node_colors);

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
            out_mobius_dem->append_error_instruction(p, composite_error_buffer, "");
        }
    });
}
