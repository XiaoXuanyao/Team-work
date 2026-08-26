# 01 官方 icraft 镜像方案（璞致板适配）

## 1 SD 卡分区

> 需 ≥8GB 卡；会清空卡内数据。Windows 下建议用 DiskGenius/Paragon（ext4），或 WSL/Linux 虚拟机。

- **p1**：FAT32，500MB~1GB（启动文件）
- **p2**：ext4，剩余空间（rootfs）

## 2 p1 内容（FAT32）

| 文件 | 来源 | 说明 |
|---|---|---|
| BOOT.bin | `data/sd/2026-08-11_1938_MIO46-47_ql100tai_pz/BOOT.bin` | UART MIO46/47 版本（悟空板工程 ql100tai_pz 导出，见 `01-最小Linux启动`） |
| Image | 官方 `FAT_image_icraft3.31.zip` | 官方内核（配套 udmabuf） |
| fmqlmp-verify.dtb | 官方 `FAT_image_icraft3.31.zip` | 含 udmabuf0（128MB） |
| download.bit | 官方 custop2：`.../参考实验/悟空开发板/基于CustomOP集合位流的软件Demo（仅供测试用）/25060601/位流/BOOT_custop2_25060601.zip` 内 `ai7100_top_disable_icap.bit`（17.4MB） | AI 位流，改名 download.bit |
| uEnv.txt | 见下 | 加载位流+内核 |

## 3 uEnv.txt（修改版）

官方原版从 `mmc 0:2` 加载 download.bit，但 p2 是 ext4（fatload 不支持），改为全部从 `0:1`（FAT）加载：

```
bootcmd=run loadbit; run uenvcmd
loadbit=mmc rescan && fatload mmc 0:1 0x10000000 download.bit && fpga loadb 0 0x10000000 $filesize
uenvcmd=mmc rescan && fatload mmc 0:1 0x10080000 Image && fatload mmc 0:1 0x11000000 fmqlmp-verify.dtb && booti 0x10080000 - 0x11000000
bootargs=console=ttyPS0,115200n8 earlycon=uart8250,mmio32,0xe0004000 loglevel=8 root=/dev/mmcblk0p2 rootwait rw clk_ignore_unused mem=1024M
bootdelay=3
```

## 4 p2 rootfs（ext4）

```
gzip -d icraft3.31_rootfs.cpio.gz
mkdir rootfs && cd rootfs
cpio -idmv < ../icraft3.31_rootfs.cpio
```
解压后把 `rootfs/*` 拷入 p2 根目录。登录：账号 `root`，密码见官方 `使用说明.txt`（rootfs 内 `/etc/inittab` 可查）。

## 5 启动验证

1. 串口观察：u-boot 应先打印 `fpga loadb` 加载位流，再 booti 内核
2. root 登录后验证：
   - `ls /dev/udmabuf0` 存在（udmabuf 驱动生效）
   - `python3 -c "import icraft"`（python icraft 运行时）
   - `ls /AI`（官方自带 yolov5 demo）
   - 运行官方 demo：`/AI/psin_yolov5_7.0/...`（见 rootfs 内 demo 说明）

## 6 风险/备选

1. **位流**：用官方 custop2 `ai7100_top_disable_icap.bit`（含 sptpost_max/sptpost_sample 算子，配套 icraft 3.31 demo）；已在本机，无需联网
2. **u-boot 是否支持 `fpga` 命令**：先测现有 prebuilt u-boot；若不支持，用 custop2 包内官方 `u-boot`（同芯片，UART 由 FSBL 决定）重组 BOOT.bin：我们的 FSBL(MIO46/47) + bl31 + 官方 u-boot
3. rootfs 较大（解压后 >1.5GB），p2 需足够空间
