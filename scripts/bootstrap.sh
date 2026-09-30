#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_workspace="${1:?Usage: bootstrap.sh WORKSPACE}"
mkdir -p "$task_workspace/src/aosp"
task_workspace="$(realpath "$task_workspace")"
cd "$task_workspace/src/aosp"
repo init -u https://github.com/kxn/rk3518-atv.git -b main -m default.xml
repo sync -c -j"${SYNC_JOBS:-8}" --fail-fast
python3 "$project_dir/scripts/project.py" native --workspace "$task_workspace"
python3 "$project_dir/scripts/project.py" apply --workspace "$task_workspace"
echo 'Next: restore proprietary inputs as documented, then run build.sh WORKSPACE kernel.'
