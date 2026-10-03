#!/usr/bin/env python3
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#########################################################
# Sets version numbers to a date-based dev version.
#
# Does nothing if not on a dev version.
#########################################################
# Example usage (from repo root):
#
# ./dev/overwrite_dev_versions_with_date.sh
#########################################################

import os
import pathlib
import re
import subprocess


def main():
    os.chdir(pathlib.Path(__file__).parent)
    os.chdir(subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip())

    # Generate dev version starting from major.minor version.
    # (Requires the existing version to have a 'dev' suffix.)
    # (Uses the timestamp of the HEAD commit, to ensure consistency when run multiple times.)
    with open('setup.py') as f:
        maj_min_version_line, = [line for line in f.read().splitlines() if re.match("^__version__ = '[^']+'", line)]
        maj_version, min_version, patch = maj_min_version_line.split()[-1].strip("'").split('.')
        if 'dev' not in patch:
            return  # Do nothing for non-dev versions.
    timestamp = subprocess.check_output(['git', 'show', '-s', '--format=%ct', 'HEAD']).decode().strip()
    new_version = f"{maj_version}.{min_version}.dev{timestamp}"

    # Overwrite existing versions.
    package_setup_files = [
        "setup.py",
    ]
    for path in package_setup_files:
        with open(path) as f:
            content = f.read()
        assert maj_min_version_line in content
        content = content.replace(maj_min_version_line, f"__version__ = '{new_version}'")
        with open(path, 'w') as f:
            print(content, file=f, end='')


if __name__ == '__main__':
    main()
