# M1 最小 Linux 启动

**目标**：璞致板从 SD 卡启动最小 Linux，串口（COM7 115200）出现 bootrom→FSBL→bl31→u-boot→kernel→shell 日志。

## 启动链

```
bootrom → FSBL.out（DDR/PS 初始化）→ bl31.elf（ATF）→ u-boot.elf
        → Image（kernel）→ system-top.dtb → rootfs（ramdisk）→ shell
```

## 关键文件与来源

| 文件 | 来源 | 状态 |
|---|---|---|
| `FSBL.out`（璞致板专用，PLL 默认/UART0 MIO46/47） | Procise 工程 `proj260811` 导出 + IAR 编译 | ✅ 已编译 |
| `bl31.elf` | 100T 研发板 prebuilt 20250408 | ✅ 已备 |
| `u-boot.elf` | 同上 | ✅ 已备 |
| `Image`（kernel 5.4.52） | 同上 | ✅ 已备 |
| `system-top.dtb` | 同上（与璞致板外设兼容：UART0/MMC0/GMAC0/QSPI/1GB DDR） | ✅ 已备 |
| `u-rootfs`（mini buildroot ramdisk） | 同上 | ✅ 已备 |
| `uEnv.txt` | 自写（booti Image+dtb+ramdisk） | ✅ 已备 |

组装目录（`data/sd/`，按版本带时间）：`2026-08-11_1938_MIO46-47_ql100tai_pz/`（当前版，含 download.bit 位流）、`2026-08-11_1614_MIO46-47/`（旧版）、`2025-05-13_prebuilt/`（prebuilt 对照）

## 当前进度

- [x] Procise GUI 编译 FSBL.out
- [x] Create Boot Image：`FSBL.out + bl31.elf + u-boot.elf` → `BOOT.bin`
- [x] SD 卡 FAT32 分区组装（BOOT.bin/Image/system-top.dtb/u-rootfs/uEnv.txt）
- [x] 上电验证：**璞致板完整启动到 Linux（Buildroot login）**
- [x] 链路：bootrom → FSBL → bl31(ATF) → u-boot(EL2) → Linux 5.4.52（4×A53）→ shell
- [x] M1 功能验证：root 登录、mount、lo、**eth0 RGMII 1Gbps 通（ping 对端 0% loss）**

## 最终方案（实测可行）

以**悟空板参考工程**（`procise/ql100tai_pz`，来自 `data/sd/puzhi_ql100tai_amp_ref`）为基础，**只修改 UART0 MIO 为 MIO46..47**，其余（PLL 54/48/30、DDR 400MHz、外设）保持悟空板配置，即可在璞致板完整启动。

- FSBL.out：悟空板工程导出 + IAR 编译（UART0=MIO46/47）
- bl31.elf / u-boot.elf：100T 研发板 prebuilt 20250408（`data/sd/fmsh_official_ramrootfs_boot/`）
- BOOT.bin：`FSBL + bl31 + u-boot` + `[fsbl_config]apu_x64`

## 调试结论（重要）

1. **UART0 必须用 MIO46..47**（璞致板实际接线；配成 MIO50/51 则串口完全无输出——这是"无输出"的根因）
2. 璞致板与悟空板同芯片（JFMQL100TAI900），DDR/外设配置兼容：悟空板配置（含手动 PLL 54/48/30、DDR 400MHz）在璞致板正常
3. 之前自制工程 UART 卡死源于 UART MIO 错配 + IO_PLL=45/UART DIVISOR=8 时钟组合；悟空板配置（IO=30/DIV=5）正常
4. bl31/u-boot 复用同芯片 prebuilt，无需重编

## 验证标准

- 串口出现 u-boot 与 kernel 日志并进入 root shell（mini rootfs 为 busybox）
- DDR 正常（Linux 能启动即证明 DDR 读写正常）

## 参考

- `output.bif`：`[bootloader]FSBL.out` + `[destination_cpu=apu_0]bl31.elf` + `u-boot.elf` + `[fsbl_config]apu_x64`
- prebuilt 的 BOOT.bin 可作为对照（同芯片官方构建，10 分钟可验证板卡本身是否 OK）
