#!/bin/bash
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


set -e
set -o pipefail
trap "exit 1" INT

sinter collect \
    --circuits out/circuits_unmatchable/*.stim out/circuits_matchable/*.stim \
    --save_resume_filepath out/stats.csv \
    --decoders chromobius \
    --processes auto \
    --max_shots 100_000_000 \
    --max_errors 1000 \
    --metadata_func auto \
    --custom_decoders "chromobius:sinter_decoders"


sinter collect \
    --circuits out/circuits_matchable/*.stim \
    --save_resume_filepath out/stats.csv \
    --decoders chromobius pymatching sparse_blossom_correlated \
    --processes auto \
    --max_shots 100_000_000 \
    --max_errors 1000 \
    --metadata_func auto \
    --custom_decoders "chromobius:sinter_decoders" "gqec:make_custom_sinter_decoders_dict"
