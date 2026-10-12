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

#include "chromobius/test_util.test.h"

#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include "gtest/gtest.h"

using namespace chromobius;

FILE *chromobius::open_test_data_file(const char *name) {
    std::vector<std::string> directories_to_check = {
        "test_data/",
        "../test_data/",
        "../../test_data/",
    };
    for (const auto &d : directories_to_check) {
        std::string path = d + name;
        FILE *f = fopen((d + name).c_str(), "r");
        if (f != nullptr) {
            return f;
        }
    }
    throw std::invalid_argument("Failed to find test data file " + std::string(name));
}

constexpr mode_t kOwnerReadWrite = S_IRUSR | S_IWUSR;

static void init_path(RaiiTempNamedFile &self) {
    char tmp_stdin_filename[] = "/tmp/stim_test_named_file_XXXXXX";
    self.descriptor = mkstemp(tmp_stdin_filename);
    if (self.descriptor == -1) {
        throw std::runtime_error("Failed to create temporary file.");
    }
    if (fchmod(self.descriptor, kOwnerReadWrite) == -1) {
        close(self.descriptor);
        self.descriptor = -1;
        remove(tmp_stdin_filename);
        throw std::runtime_error("Failed to set permissions on temporary file.");
    }
    close(self.descriptor);
    self.descriptor = -1;
    self.path = std::string(tmp_stdin_filename);
}

RaiiTempNamedFile::RaiiTempNamedFile() {
    init_path(*this);
}

RaiiTempNamedFile::RaiiTempNamedFile(const std::string &contents) : RaiiTempNamedFile() {
    write_contents(contents);
}

RaiiTempNamedFile::~RaiiTempNamedFile() {
    if (descriptor != -1) {
        close(descriptor);
        descriptor = -1;
    }
    if (!path.empty()) {
        remove(path.data());
        path = "";
    }
}

std::string RaiiTempNamedFile::read_contents() {
    FILE *f = fopen(path.c_str(), "rb");
    if (f == nullptr) {
        throw std::runtime_error("Failed to open temp named file " + path);
    }
    std::string result;
    while (true) {
        int c = getc(f);
        if (c == EOF) {
            break;
        }
        result.push_back(c);
    }
    fclose(f);
    return result;
}

void RaiiTempNamedFile::write_contents(const std::string &contents) {
    int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, kOwnerReadWrite);
    if (fd == -1) {
        throw std::runtime_error("Failed to open temp named file " + path);
    }
    if (fchmod(fd, kOwnerReadWrite) == -1) {
        close(fd);
        throw std::runtime_error("Failed to set permissions on temp named file " + path);
    }
    FILE *f = fdopen(fd, "wb");
    if (f == nullptr) {
        close(fd);
        throw std::runtime_error("Failed to open temp named file " + path);
    }
    for (char c : contents) {
        putc(c, f);
    }
    fclose(f);
}

// Clears the process umask when passed 0 so permission checks verify that 0600
// comes from the code under test rather than an already-restrictive environment
// umask.
struct ScopedUmask {
    mode_t old_mask;
    explicit ScopedUmask(mode_t mask = 0) : old_mask(umask(mask)) {
    }
    ~ScopedUmask() {
        umask(old_mask);
    }
};

static mode_t permission_bits(const std::string &path) {
    struct stat st{};
    EXPECT_EQ(stat(path.c_str(), &st), 0);
    return st.st_mode & 0777;
}

TEST(test_util, created_with_owner_only_permissions) {
    ScopedUmask clear_umask(0);
    RaiiTempNamedFile tmp;
    ASSERT_FALSE(tmp.path.empty());
    ASSERT_EQ(tmp.descriptor, -1);
    ASSERT_EQ(permission_bits(tmp.path), kOwnerReadWrite);
    ASSERT_EQ(tmp.read_contents(), "");
}

TEST(test_util, write_contents_truncates) {
    RaiiTempNamedFile tmp;
    tmp.write_contents("hello chromobius\n");
    ASSERT_EQ(tmp.read_contents(), "hello chromobius\n");

    tmp.write_contents("short");
    ASSERT_EQ(tmp.read_contents(), "short");

    tmp.write_contents("");
    ASSERT_EQ(tmp.read_contents(), "");
}

TEST(test_util, write_contents_restores_permissions) {
    ScopedUmask clear_umask(0);
    RaiiTempNamedFile tmp;

    ASSERT_EQ(chmod(tmp.path.c_str(), kOwnerReadWrite | S_IRGRP | S_IROTH), 0);
    ASSERT_NE(permission_bits(tmp.path), kOwnerReadWrite);
    tmp.write_contents("tightened");
    ASSERT_EQ(permission_bits(tmp.path), kOwnerReadWrite);

    ASSERT_EQ(remove(tmp.path.c_str()), 0);
    tmp.write_contents("recreated");
    ASSERT_EQ(permission_bits(tmp.path), kOwnerReadWrite);
    ASSERT_EQ(tmp.read_contents(), "recreated");
}

TEST(test_util, write_contents_round_trips_binary) {
    RaiiTempNamedFile tmp;
    std::string payload("binary\0data", 11);
    tmp.write_contents(payload);
    ASSERT_EQ(tmp.read_contents(), payload);
}

TEST(test_util, destructor_removes_file) {
    std::string saved_path;
    {
        RaiiTempNamedFile tmp("ephemeral");
        saved_path = tmp.path;
        ASSERT_FALSE(saved_path.empty());
    }

    struct stat st{};
    errno = 0;
    ASSERT_EQ(stat(saved_path.c_str(), &st), -1);
    ASSERT_EQ(errno, ENOENT);
}

TEST(test_util, contents_constructor_round_trips) {
    ScopedUmask clear_umask(0);
    RaiiTempNamedFile tmp("initial contents");
    ASSERT_EQ(tmp.descriptor, -1);
    ASSERT_EQ(tmp.read_contents(), "initial contents");
    ASSERT_EQ(permission_bits(tmp.path), kOwnerReadWrite);
}

TEST(test_util, error_paths_do_not_leak_fds) {
    // POSIX guarantees dup() returns the lowest-numbered unused file descriptor,
    // so an unchanged value before and after an operation confirms no descriptor
    // was leaked.
    int fd_before = dup(0);
    ASSERT_NE(fd_before, -1);
    ASSERT_EQ(close(fd_before), 0);

    {
        RaiiTempNamedFile tmp("initial contents");
        std::string saved_path = tmp.path;

        ASSERT_EQ(remove(saved_path.c_str()), 0);
        ASSERT_THROW(tmp.read_contents(), std::runtime_error);

        tmp.path = "/nonexistent_dir_chromobius_test/file";
        ASSERT_THROW(tmp.write_contents("fail"), std::runtime_error);

        tmp.path = saved_path;
        tmp.write_contents("recovered");
        ASSERT_EQ(tmp.read_contents(), "recovered");

        int fd_during = dup(0);
        ASSERT_NE(fd_during, -1);
        ASSERT_EQ(close(fd_during), 0);
        ASSERT_EQ(fd_during, fd_before);
    }

    int fd_after = dup(0);
    ASSERT_NE(fd_after, -1);
    ASSERT_EQ(close(fd_after), 0);
    ASSERT_EQ(fd_after, fd_before);
}
