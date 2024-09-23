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

#include "gtest/gtest.h"

using namespace chromobius;

TEST(atomic_error, detector_instruction_to_color_basis) {
    std::vector<double> args{-1, -1, -1, 2};
    std::vector<double> offsets{-3, -3, -3, 3, -2};
    stim::DemInstruction instruction{
        .arg_data = args,
        .target_data = {},
        .type = stim::DemInstructionType::DEM_DETECTOR,
    };
    ASSERT_EQ(detector_instruction_to_color_basis(instruction, offsets), (ColorBasis{Charge::B, Basis::Z}));
    offsets[3] = 100;
    ASSERT_THROW({ detector_instruction_to_color_basis(instruction, offsets); }, std::invalid_argument);
    offsets[3] = 0.5;
    ASSERT_THROW({ detector_instruction_to_color_basis(instruction, offsets); }, std::invalid_argument);
    args[3] = 0.5;
    ASSERT_EQ(detector_instruction_to_color_basis(instruction, offsets), (ColorBasis{Charge::G, Basis::X}));
    args[3] = -1.5;
    ASSERT_EQ(detector_instruction_to_color_basis(instruction, offsets), (ColorBasis{Charge::NEUTRAL, Basis::UNKNOWN_BASIS, true}));
}
