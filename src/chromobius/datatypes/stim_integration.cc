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

#include "chromobius/datatypes/stim_integration.h"

#include <sstream>

using namespace chromobius;

ColorBasis chromobius::detector_instruction_to_color_basis(
    const stim::DemInstruction &instruction, std::span<const double> coord_offsets) {
    assert(instruction.type == stim::DemInstructionType::DEM_DETECTOR);
    bool failed = false;
    double c = -2;
    if (instruction.arg_data.size() > 3) {
        c = instruction.arg_data[3];
        if (coord_offsets.size() > 3) {
            c += coord_offsets[3];
        }
    } else {
        failed = true;
    }

    int r = 0;
    if (c < -1 || c > 5) {
        failed = true;
    } else {
        r = (int)c;
        if (r != c) {
            failed = true;
        }
    }
    if (failed) {
        throw std::invalid_argument(
            "Expected all detectors to have at least 4 coordinates, with the 4th "
            "identifying the basis and color "
            "(RedX=0, GreenX=1, BlueX=2, RedZ=3, GreenZ=4, BlueZ=5), but got " +
            instruction.str());
    }
    if (r == -1) {
        return ColorBasis{
            .color=Charge::NEUTRAL,
            .basis=Basis::UNKNOWN_BASIS,
            .ignored=true,
        };
    }
    constexpr std::array<ColorBasis, 6> mapping{
        ColorBasis{Charge::R, Basis::X},
        ColorBasis{Charge::G, Basis::X},
        ColorBasis{Charge::B, Basis::X},
        ColorBasis{Charge::R, Basis::Z},
        ColorBasis{Charge::G, Basis::Z},
        ColorBasis{Charge::B, Basis::Z},
    };
    return mapping[r];
}
