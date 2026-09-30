# 来源与许可

固定版本：`default.xml`、`sources.lock.json`。小改动：`patches/series.json`。
核心组件仓库 `PORT_ORIGIN.md` 标明上游 URL 和基准提交。

- AOSP：android.googlesource.com，android-14.0.0_r75 的实际检出提交。
- 内核：rockchip-linux/kernel，develop-6.1，保留 GPL/SPDX 与上游历史。
- AIC SDIO：radxa-pkg/aic8800，保留上游历史、文件许可；本项目添加平台构建和稳定 MAC 选择。
- Rockchip 产品、HWC2、Utgard gralloc、U-Boot：公开的 rockchip_radxa_android13 GitLab BSP。
- Rockchip 音频、tinyalsa、speex、Codec2、Rockit、Gatekeeper、Weaver：公开的 rockchip_android14_radxa_rkr6 GitLab BSP。
- `hardware/aic`：AIC SDK Android HAL 源码快照，保留 Aicsemi/AOSP 文件许可及发布版本注释。
  可公开核对的参考 SDK 是 gtxaspec/aic8800-wifi；并非整个目录与该 SDK 提交逐文件相同。
- `hardware/rockchip/librga`：原工作树中手工复制的 Android 14 Rockchip 源码，保留 Rockchip 的 Apache-2.0
  COPYING、版权头和当前文件内容。其精确原始 Git 提交未保留下来；这里作为注明来源的源码快照发布，
  不虚构与旧 librga-old 或仅含预编译库的 aiRockchip 仓库的提交对应关系。
- `soong_rockchip_prebuilt`：从 device/rockchip/common 原目录迁移的 Soong 插件。
- `BoxRemoteSetup`：本项目实现；参考原厂行为分析，没有拷贝或分发原厂 BTHelp/Google TV APK。

本仓库 Apache-2.0 LICENSE 只适用于本项目新增的脚本/文档；补丁中被修改的代码继续适用其原有许可。
组件仓库和设备覆盖不统一重新许可：逐文件版权头、NOTICE、COPYING、SPDX 优先。

专有二进制不在本仓库 Git 中分发。清单中的公开上游链接仅用于定位，不替代上游许可。
Mali450 等许可未在本次移植中重新确认，使用者应依据自己的 SDK 授权取得。
支持从有权使用的本地文件导入，导入前强制 SHA256；没有原厂账户/密钥/个人数据下载步骤。

清单中 `required=false` 的项属于源码测试、样例、文档资源或可重新编译的 DTB，未作为固件构建的外部输入。
Mali 与当前 HWC HDR/parser、AIC 固件是运行时输入；不能用空占位文件代替。
