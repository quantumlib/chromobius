/*
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef _CHROMOBIUS_STIM_INTEGRATION_H
#define _CHROMOBIUS_STIM_INTEGRATION_H

#include <ostream>
#include <span>

#include "chromobius/datatypes/conf.h"
#include "chromobius/datatypes/color_basis.h"
#include "stim.h"

namespace chromobius {

ColorBasis detector_instruction_to_color_basis(
    const stim::DemInstruction &instruction, std::span<const double> coord_offsets);

}  // namespace chromobius

#endif
