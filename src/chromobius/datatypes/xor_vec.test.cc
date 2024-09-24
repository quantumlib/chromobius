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
