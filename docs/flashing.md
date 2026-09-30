# 刷机记录

本工程针对已测试的这块 RK3518 / 1.5 GB LPDDR3 / 8 GB eMMC 板；设备名字保留 RK3528 BSP 命名。
其他同名盒子的 DDR、GPIO、分区表可能不同。先保存自己设备的分区表、原厂 ID block、U-Boot 和 misc。

本机 super 起始 LBA 为 `0x001FD000`，长度为 2,516,582,400 字节。
Android 构建常产生 sparse super；使用 RKDevTool 支持的镜像格式或先 simg2img 转 raw，并核对大小。
更新应用/HAL 通常只需 super，保留 userdata。不要将这一地址用于未核对 GPT 的其他设备。

Linux 6.1 arm64 boot、arm64 U-Boot 与真实板子 DTB 必须配套。损坏的 recovery 仍可能使
misc 中的 boot-recovery 状态形成重启死循环；不要把未修复的 recovery 当成正常恢复手段。

Maskrom 下载 loader 是 DDR+USB/SPL 下载容器，供工具试载建立访问；不是裸分区镜像。
确认 DDR 和读取 eMMC 成功后再执行写入。LPDDR3 780 MHz 参数仅对应这一块板子的验证情况。

公开源码脚本不会自动擦除、写 USB 设备、清数据或重启盒子。刷机后应通过串口/网络 ADB
验证 sys.boot_completed、实际文件版本、Mali 节点、wlan0、遥控器、视频硬解和 HDMI 音频。
