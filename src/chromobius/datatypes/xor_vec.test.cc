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

#include "chromobius/datatypes/xor_vec.h"

#include "gtest/gtest.h"

using namespace chromobius;

TEST(xor_vec, inplace_xor_sort) {
    auto f = [](std::vector<int> v) -> std::vector<int> {
        std::span<int> s = v;
        auto r = inplace_xor_sort(s);
        v.resize(r.size());
        return v;
    };
    ASSERT_EQ(f({}), (std::vector<int>({})));
    ASSERT_EQ(f({5}), (std::vector<int>({5})));
    ASSERT_EQ(f({5, 5}), (std::vector<int>({})));
    ASSERT_EQ(f({5, 5, 5}), (std::vector<int>({5})));
    ASSERT_EQ(f({5, 5, 5, 5}), (std::vector<int>({})));
    ASSERT_EQ(f({5, 4, 5, 5}), (std::vector<int>({4, 5})));
    ASSERT_EQ(f({4, 5, 5, 5}), (std::vector<int>({4, 5})));
    ASSERT_EQ(f({5, 5, 5, 4}), (std::vector<int>({4, 5})));
    ASSERT_EQ(f({4, 5, 5, 4}), (std::vector<int>({})));
    ASSERT_EQ(f({3, 5, 5, 4}), (std::vector<int>({3, 4})));
}
