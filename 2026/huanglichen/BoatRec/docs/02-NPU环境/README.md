# 02 NPU 环境（M2）

## 目标

在璞致板加载 AI 位流 + icraft 3.31 运行时，为 YOLO demo（M3/M4）准备运行环境。

## 关键资源（已在工作区）

| 资源 | 路径 |
|---|---|
| AI 位流（官方 custop2） | `data/sd/fmsh_custop2_25060601_boot/ai7100_top_disable_icap.bit`（17.4MB，改名 download.bit） |
| 官方 icraft FAT 启动包 | `docs/99-参考资料/复旦微UDP下载器完整资料包/.../04_FPAI/02_Icraft/v3.31/系统镜像/Linux/buildroot/FAT_image_icraft3.31.zip` |
| 官方 icraft rootfs（889MB） | `.../buildroot/icraft3.31_rootfs.cpio.gz` |
| icraft arm64 运行时 | `.../Icraft安装包/icraft-3.31.1-cp38-none-manylinux2014_aarch64.whl`、`Icraft_3.31.1_arm64.deb` |
| udmabuf demo（C++ 示例+说明） | `.../08_PSOC/.../02_linux-demo/03_udmabuf/udmabuf使用示例.zip` |
| 官方 ubuntu SD 完整镜像（备选，30GB） | `.../系统镜像/Linux/ubuntu20.4/ubuntu镜像文件/wk_icraft3.31_unbuntu_sd_Image/wk_icraft3.31_unbuntu_sd_Image.bin` |

## 方案结论（官方 buildroot icraft 方案 + 璞致板适配）

官方 icraft 镜像的 BOOT.bin/BL31/u-boot 是**悟空板 UART MIO50/51**，璞致板直接用会串口无输出。适配方法：**SD 卡用我们的 BOOT.bin（UART MIO46/47），其余（Image/dtb/rootfs）复用官方 icraft 包**。

启动机制（官方 uEnv.txt）：
- `bootcmd = run loadbit; run uenvcmd`
- `loadbit = fatload download.bit && fpga loadb`（u-boot 直接把 AI 位流加载进 PL）
- root 在 `mmcblk0p2`（ext4）

官方 dtb（`fmqlmp-verify.dtb`）已含 NPU 必需的 **udmabuf0（128MB，`ikwzm,u-dma-buf`）**。

## 当前进度

- [x] 自制 ImageUSB 整卡镜像 `pz_icraft.bin`（p1 FAT32 512MB + p2 ext4 9.5GB ubuntu rootfs），见 `02-SD卡镜像制作与烧写.md`
- [x] 烧写 + 启动：位流 `fpga loadb` 加载成功，进入 Ubuntu rootfs
- [x] `uname -r`=5.4.52，**`/dev/udmabuf0` 就绪**（NPU 内存交换路径打通）
- [x] 板上环境：icraft 3.31.0 / numpy 1.23 / opencv 4.6 / buyi backend 齐全
- [x] 网络持久化（interfaces.d/eth0 static + rc.local 去 dhclient），见 `03-板上环境配置.md`
- [x] **YOLO26 demo 运行**（imodel + buyi forward 验证跑通，见 `03-位流适配/README.md` 与 `04-模型AI加速例程/`）
