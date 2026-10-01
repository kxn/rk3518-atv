# 构建说明

需要 x86_64 Linux，AOSP 构建依赖，Git、repo、Python 3.11+，以及 arm64 GCC 交叉工具链。
现有内核和 AIC 构建采用 Buildroot GCC 10.3.0 / Binutils 2.36.1。
本项目不自动安装交叉工具链；将 `CROSS_COMPILE` 设置为其完整前缀。
Android 使用 manifest 固定的预编译 Clang。建议 32 GB 以上内存、约 700 GB 可用空间。

1. 克隆主仓库，在 Android 源码树之外保留它。
2. 运行 `scripts/bootstrap.sh WORKSPACE`。AOSP/BSP 由 repo 同步，独立组件由 sources.lock.json 同步。
3. 运行 `project.py inputs --workspace WORKSPACE --fetch-upstream`，恢复固定来源并验证 SHA256。
   若不希望脚本获取二进制，使用 `--supplied DIR`。此目录以 SHA256 命名文件。
4. 运行 `build.sh WORKSPACE kernel`。用实际交付内核配置编译内核、Mali 模块、板子 DTB、AIC BSP/fdrv。
5. 运行 `build.sh WORKSPACE android`，生成 AOSP `boot.img` 与 `super.img`。
   产品保留 `kernel-5.10` 路径别名以兼容旧 BSP，其目标实际是这个 6.1 内核。
6. 可单独运行 `build.sh WORKSPACE modules` 编译遥控器、设置、图形、supplicant 和蓝牙组件。

### 输入完整性

`project.py apply` 在应用补丁前确认项目 HEAD，再做 git apply --check。
重复执行已应用的补丁会跳过；保存补丁与覆盖文件的内容/权限指纹，若用户随后编辑过则停止，避免覆盖。覆盖文件前保留首次原始副本，不 reset/clean 已有工作树。
原厂私钥不作为构建输入；缺失 NFC 开发签名使用 AOSP 公共 platform 测试密钥。
不要将这个开发签名用于正式 OTA 信任体系。

### 引导和救砖

`loader/build_loaders.py` 是独立的 LPDDR3 780 MHz 下载 loader 生成工具。
先执行 `python3 loader/fetch_inputs.py` 恢复 loader 输入，再执行 `python3 loader/build_loaders.py` 和 `python3 loader/verify_loaders.py`。`upstream-tree.json` 固定官方 rkbin Git blob，
脚本只改 lp3_freq=780，打包 DDR 1.11 / USB plug 1.04 / SPL 1.07，不操作 USB 或块设备。

U-Boot 源码及实际配置在组件仓库和 device-support/configs 中。它仍依赖 Rockchip rkbin
提供 BL31/TEE/SPL。使用该 BSP 的 `make.sh rk3528` 流程时，要按 sources.lock.json 的 rkbin
版本布置输入；不要用其他芯片的 trust/loader 或把下载容器当裸 ID block 写入。
本发布尚未验证从零生成与已交付 ID block / U-Boot FIT 完全一致的打包链，现有固件升级优先仅更新 super。

### 与现有 v7 镜像的区别

现有 v7 是对已成功启动的分区做增量替换，保存并校验 ext4 元数据和 SELinux 标签。
蓝牙 APEX 更新时保留已验收的 Java payload，仅更新本地 native 库。
源码构建将一起重建 Java/native APEX，因此需重新验收 ART、蓝牙和冷启动；不能声称其已得到同等实机验证。
完整 build.sh 新流程是供复现和继续开发的构建入口，当前未做完整 clean build。

`scripts/repack.py` 提供已知基准 super 的离线更新路径：通过参数传入自己的基准、工具目录和修改清单。
它不含原厂镜像、不连接盒子，也不直接刷机。

如构建失败，请记录锁定提交、主仓库版本、命令和首个失败目标；避免以 ALLOW_MISSING_DEPENDENCIES
掩盖运行时 HAL 缺失。原 BSP 的此开关暂予保留，不代表所有依赖均可忽略。

## v7.2 源码组织

请使用全新工作目录，从 `source-preview-v7.2` 检出构建入口后执行 bootstrap。
旧版本使用的 HWC 父目录仓库已改为两个独立上游项目，不能在已打补丁的 v7.1 源码树中直接 repo sync 升级。
本次只调整源码来源和组织，保留现有固件的代码修改；并没有产出或宣称验收新的整机镜像。
`project.py apply` 依次应用 AOSP/独立树补丁、按清单提取 SDK 文件、安装本项目覆盖。
再次执行会校验已准备文件；发现用户修改则报错，避免静默覆盖。

## v8 应用精简

rk3528_box 不再打包 Lightning 浏览器和 Traceur（System Tracing）应用；其他产品的选择不变。
屏幕输入法、TvSettings、配对程序、WebView/媒体组件和底层诊断接口保留。
离线 repack 的 changes 清单支持 `op: remove-app`，仅允许删除 app/priv-app 下明确命名的单个应用目录；
递归删除后检查不存在，并对所有分区执行 e2fsck 和打包读回哈希校验。
不要对运行中、几乎满载的 vendor 分区在线覆盖 HWC 文件。以离线生成并验证的 super 镜像恢复/更新，
刷后核对实际 HWC SHA256，并通过一次重启确认持久性。
