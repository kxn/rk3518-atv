# RK3518 64 位 Android TV 盒子

这是 RK3518 / Mali-450 / 1.5 GB LPDDR3 / AIC8800D80 盒子的社区移植工程。
目标用途是 AllStream 投屏：保留遥控器、Wi-Fi、视频硬解、HDMI 音频、桌面和 AOSP 屏幕输入法。

本仓库是构建入口，固定 AOSP、Rockchip BSP 和本项目组件的提交，并保存小补丁和构建脚本。
**源码发布版为 `source-preview-v7.1`。全新检出后的整机编译和冷启动尚未验收，不承诺与现有 v7 镜像逐字节相同。**
已验证的设备和构建范围见 [验证记录](docs/validation.md)。

## 开始

在 Linux 上安装 AOSP 构建依赖、Git、Python 3.11+ 和 `repo`，预留约 700 GB 磁盘。
主仓库应放在 Android 源码树外，避免其补丁、脚本被 Soong 当成模块扫描。

```sh
git clone https://github.com/kxn/rk3518-atv.git
./rk3518-atv/scripts/bootstrap.sh /path/to/workspace
python3 rk3518-atv/scripts/project.py inputs --workspace /path/to/workspace --fetch-upstream
export CROSS_COMPILE=/path/to/aarch64-gcc/bin/aarch64-buildroot-linux-gnu-
./rk3518-atv/scripts/build.sh /path/to/workspace kernel
./rk3518-atv/scripts/build.sh /path/to/workspace android
```

`--fetch-upstream` 从清单列出的公开上游恢复固定版本的二进制输入，不从本仓库下载原厂备份。
也可用 `--supplied DIR` 提供自己有权使用的文件，文件名为其 SHA256。
获取路径、版本及校验值见 [proprietary-files.json](proprietary-files.json)。
详细步骤与当前限制见 [构建说明](docs/build.md) 和 [刷机说明](docs/flashing.md)。

## 组件

| 仓库 | 内容 |
|---|---|
| [rk3518-atv-device](https://github.com/kxn/rk3518-atv-device) | 独立遥控器配对、产品覆盖、AIC Android HAL、手工引入的图形源码、配置 |
| [rk3518-atv-kernel](https://github.com/kxn/rk3518-atv-kernel) | Rockchip 6.1 内核 fork、Mali DMA_BUF 命名空间适配 |
| [rk3518-atv-aic8800](https://github.com/kxn/rk3518-atv-aic8800) | AIC SDIO 驱动 fork、稳定 MAC 选择 |
| [rk3518-atv-u-boot](https://github.com/kxn/rk3518-atv-u-boot) | 64 位 U-Boot、电脑 VBUS 自动下载入口 |
| [rk3518-atv-hwcomposer](https://github.com/kxn/rk3518-atv-hwcomposer) | HWC2、DRM4 视频格式和同步栅栏修复 |
| [rk3518-atv-bluetooth](https://github.com/kxn/rk3518-atv-bluetooth) | HID/SMP 重连、L2CAP 生命周期和诊断快照修复 |

内核和 AIC 保留上游 Git 祖先。U-Boot、HWC、Bluetooth 使用注明提交来源的源码快照导入；不是原上游历史的完整镜像。
`sources.lock.json` 和 `default.xml` 固定构建使用的提交；不以变化的上游分支作为构建输入。

## 配置与边界

- AOSP 基准是 `android-14.0.0_r75` / API 34。旧构建 fingerprint 中的 VanillaIceCream 不代表 API 35。
- arm64 主架构，保留 arm32 应用兼容。最终 GPU 使用 Android Mali-450 32/64 位 blob；没有使用 Linux blob wrapper 或 Mesa/Lima。
- 使用 HIDL Composer 2.1；保留但不启用 HWC3 的源码。
- 独立 `BoxRemoteSetup` 接管名为 `Bluetooth remote` 的遥控器；首次引导要出现可用 DPAD 才完成。
- 开启 Wi-Fi 网络 ADB 5555、无屏幕授权；关闭 USB ADB 循环。此配置对应用户的家庭开发设备。
- userdebug、开发签名、SELinux permissive；恢复分区尚未修复。不是 Google 认证系统，不包含 Google TV/GMS APK。
- AllStream 是独立应用，不在此仓库公开其源码或 APK；构建后自行安装。

不上传原厂完整固件、userdata、蓝牙密钥、个人日志、OEM 签名私钥或未知许可驱动库。
原有源码保留各自许可证；本项目新增脚本和遥控器应用采用 Apache-2.0。见 [来源与许可](docs/provenance.md)。
