# 来源与许可

固定版本：`default.xml`、`sources.lock.json`。小改动：`patches/series.json`。
直接上游组件的 URL/提交记录在锁文件中；真实 fork 的 `PORT_ORIGIN.md` 保留祖先提交信息。
路径重定位通过 `source-imports.json` 明确列出；不在设备仓库重复导入第三方源码。

- AOSP：android.googlesource.com，android-14.0.0_r75 的实际检出提交。
- 内核：rockchip-linux/kernel，develop-6.1，保留 GPL/SPDX 与上游历史。
- AIC SDIO：radxa-pkg/aic8800，保留上游历史、文件许可；本项目添加平台构建和稳定 MAC 选择。
- Rockchip 产品、HWC2、Utgard gralloc、U-Boot：公开的 rockchip_radxa_android13 GitLab BSP。
- Rockchip 音频、tinyalsa、speex、Codec2、Rockit、Gatekeeper、Weaver：公开的 rockchip_android14_radxa_rkr6 GitLab BSP。
- `hardware/aic`：精确来源为 radxa-pkg/aic8800 的 `src/libbt-vendor/aicbt` 和
  `src/SDIO/driver_fw/aic/wlan`；取自锁定的 AIC SDK fork，补丁为 `aic-android-hal.patch`。
- `hardware/rockchip/librga`：直接引用 rockchip_android14_radxa_rkr6/linux/linux-rga 的
  `a5444901f6c0164ea1738af16b4991774db95be1`；243 个原文件中仅 Android.go 有改动。
- HWC2：直接引用 Android 13 BSP 的 `f8586c8a417f67d38513cc04d0ff2c004be37ff8`，修改保存在补丁中。
- HWC3：直接引用 Android 14 BSP 的 `c2ce1c4346ac15c6b2bc7df1a2f868874cf3b75d`，无修改。
- `soong_rockchip_prebuilt`：从 device/rockchip/common 的固定上游树提取；原位置保留源码，
  修改和禁用旧模块入口记录在该项目补丁中，以免 Soong 重复注册。
- `BoxRemoteSetup`：本项目实现；参考原厂行为分析，没有拷贝或分发原厂 BTHelp/Google TV APK。

本仓库 Apache-2.0 LICENSE 只适用于本项目新增的脚本/文档；补丁中被修改的代码继续适用其原有许可。
组件仓库和设备覆盖不统一重新许可：逐文件版权头、NOTICE、COPYING、SPDX 优先。

专有二进制不在本仓库 Git 中分发。清单中的公开上游链接仅用于定位，不替代上游许可。
Mali450 等许可未在本次移植中重新确认，使用者应依据自己的 SDK 授权取得。
支持从有权使用的本地文件导入，导入前强制 SHA256；没有原厂账户/密钥/个人数据下载步骤。

外部输入清单只保留 12 个 AIC 固件和两个 Mali 库。其余未修改的上游资源由 Git 直接提供，
包括 HWC HDR/parser；不能用空占位文件代替运行时输入。

source-preview-v7.2 修正了之前快照发布的组织方式。旧 tag 和归档仓库仅供历史追溯，
当前 manifest 不再引用它们；没有通过改写旧历史掩盖此前的发布。
