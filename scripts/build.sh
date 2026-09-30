#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_workspace="${1:?Usage: build.sh WORKSPACE [kernel|android|modules]}"
task_workspace="$(realpath "$task_workspace")"
target="${2:-android}"
jobs="${JOBS:-$(nproc)}"
aosp="$task_workspace/src/aosp"
kernel="$task_workspace/src/rk-kernel"
device="$task_workspace/src/device-support"
if [[ "$target" == kernel ]]; then
    : "${CROSS_COMPILE:?Set the absolute aarch64 GCC toolchain prefix; see docs/build.md}"
    cp "$device/configs/kernel.config" "$kernel/.config"
    make -C "$kernel" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" olddefconfig
    make -C "$kernel" -j"$jobs" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" rk3518-evb1-ddr4-v10.img modules
    driver="$task_workspace/src/aic8800/src/SDIO/driver_fw/driver/aic8800"
    make -C "$kernel" -j"$jobs" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" M="$driver" modules
    staging="$aosp/device/rockchip/rk3528/rk3528_box/modules"
    mkdir -p "$staging"
    for name in aic8800_bsp aic8800_fdrv; do
        install -m644 "$driver/$name/$name.ko" "$staging/$name.ko"
    done
    for path in "$aosp/device/rockchip/rk3528/dtb" "$aosp/device/rockchip/rk3528/rk3528_box/dtb"; do
        mkdir -p "$path"
        install -m644 "$kernel/arch/arm64/boot/dts/rockchip/rk3518-evb1-ddr4-v10.dtb" "$path/"
    done
    exit 0
fi
python3 "$project_dir/scripts/project.py" check --workspace "$task_workspace"
cd "$aosp"
source build/envsetup.sh
lunch rk3528_box-ap2a-userdebug
if [[ "$target" == modules ]]; then
    m -j"$jobs" BoxRemoteSetup TvSettings hwcomposer.rk30board wpa_supplicant \
        libbt-vendor-aic android.hardware.bluetooth@1.0-impl libbluetooth_jni
elif [[ "$target" == android ]]; then
    test -f "$kernel/arch/arm64/boot/Image" || { echo 'Run the kernel stage first'; exit 1; }
    m -j"$jobs" bootimage superimage
else
    echo 'Unknown target' >&2; exit 2
fi
