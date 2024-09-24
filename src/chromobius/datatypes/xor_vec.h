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

#ifndef _CHROMOBIUS_XOR_VEC_H
#define _CHROMOBIUS_XOR_VEC_H

#include <algorithm>
#include <span>

namespace chromobius {

template <typename T>
inline std::span<T> inplace_xor_sort(std::span<T> items) {
    std::sort(items.begin(), items.end());
    size_t new_size = 0;
    for (size_t k = 0; k < items.size(); k++) {
        if (new_size > 0 && items[k] == items[new_size - 1]) {
            new_size--;
        } else {
            if (k != new_size) {
                std::swap(items[new_size], items[k]);
            }
            new_size++;
        }
    }
    return items.subspan(0, new_size);
}

}  // namespace chromobius

#endif
