# 01 Procise项目

## 1 创建项目

1. **检查 Procise 安装**：若未安装，参照 `docs/00-环境准备/02-环境准备.md` 安装 Procise 2025.1.1（build 31969）+ patch V2.1
2. **新建工程**：打开 Procise → `File → New Project...`，选择新建空项目
3. **命名与路径**：输入项目名称（例：`proj260811`）与项目路径，点击 `Next`
4. **器件设置**（按下表填写），点击 `Next`：

   | 配置项 | 值 |
   |---|---|
   | Device Family | `jfmql` |
   | Device | `jfmql100tai900` |
   | Package | `fcbga900` |
   | Speed | `-2` |

5. 其余选项保持默认设置，点击 `Next`
6. 点击 `Finish` 完成创建

## 2 添加IP核

1. 左侧栏找到 `Create Block Design`，双击
2. 默认 design 名（`design_1`），确认
3. 左上角双击 `Hierarchy > Sources > design_1 (design_1.bd)`
4. 右侧空白区域右键，选择 `Add IP...`
5. 搜索 `process`，找到 `fmsh.com:ip:processing_system7p:1.0`，双击添加
6. 双击这个 IP 块，进行配置修改（配置项见下）：

### 2.1 Peripheral I/O Pins

勾选以下接口：

- Quad SPI Flash
- Ethernet0（并点击它左侧下拉箭头，把 **MDI0** 一并勾选上）
- SD0
- UART0

### 2.2 MIO Configuration

设置 IO：

| 外设 | MIO |
|---|---|
| Quad SPI Flash | 默认值 |
| Ethernet0 | MIO16..27 |
| MDI0 | MIO52..53 |
| SD0 | MIO40..45 |
| UART0 | **MIO46..47** |

> 上方 **Bank1 I/O Voltage** 选 `LVCMOS 1.8V`。
> **UART0 必须用 MIO46..47**（璞致板实际接线，配成其他 MIO 会串口无输出）。

### 2.3 Clock Configuration

**不要勾选** `Advanced Clocking > Override Clocks`，PLL 由工具自动配置。

> 手动设置 PLL Multiplier（Override Clocks）会导致 UART 时钟异常，FSBL 卡死在 UART 打印（实测，去掉 override 后正常）。

### 2.4 DDR Configuration

- 保持默认配置，暂不修改

全部设置完成后点击OK

## 3 导出 FSBL 和 DeviceTree

1. 右键 `design_1.bd` → **Generate Output Products**（生成块设计综合产物）
2. 提示是否自动添加 DDR 和 Fixed_IO 接口，选 **OK**（自动将 `DDR`/`FIXED_IO` 引出为外部接口，并生成顶层 wrapper `design_1_wrapper.v`）
3. 完成后，再次右键 `design_1.bd` → **Export Hardware**，勾选 **FSBL 和 DeviceTree**，点 OK
4. 右下角输出 `generate IAR example designes successfully.` 即为成功

**导出产物**（`procise/proj260811/SDK/design_1_platform/`）：

| 目录/文件 | 内容 |
|---|---|
| `FSBL/` | FSBL 工程（`FSBL.ewp`，含 `FM_QL_fsbl` 源码） |
| `DeviceTree/FM_QL_hw_platform/system-top.dts` | 板级设备树源码 |
| `FM_QL_hw_platform/ps_init.c` | PS 初始化（含 DDR/PLL 配置） |
| `FM_QL_bsp/` | BSP（bootloader + libsrc + 头文件） |
| `design_1_platform.eww` | IAR 工作区（含 FSBL 工程，编译入口） |

## 4 Procise - IAR 构建 FSBL.out

1. `Project > Launch IAR`，保持默认设置点击 **OK**（Procise 启动 IAR，自动加载 SDK 工作区 `design_1_platform.eww`）
2. 等待工程加载完成后，右键 `FSBL - Debug`，选择 **Rebuild All**
3. 编译完成后，产物位于 `procise/proj260811/SDK/design_1_platform/FSBL/Debug/Exe/FSBL.out`
4. 输出	“Build succeeded” 表示构建完成

## 5 支路：基于悟空板参考工程（推荐）

> 从零搭建工程（第 1~4 节）可行，但**最快且已实测完整启动的方案**是复用悟空板参考工程（复旦微官方 100TAI，与璞致板同芯片 JFMQL100TAI900），只改 UART0 MIO。

1. **复制参考工程**到工作区：`data/sd/puzhi_ql100tai_amp_ref/ql100tai_amp` → `procise/ql100tai_pz/`（保留原始参考）
2. **Procise 打开** `procise/ql100tai_pz/ql100tai.fpe`（器件 jfmql100tai / fcbga900 / -2）
3. 打开块设计 `ql100tai.bd`，双击 `processing_system7p`
4. **MIO Configuration**：UART0 从 `MIO50..51` 改为 **`MIO46..47`**（璞致板实际接线），其余外设/PLL/DDR 保持悟空板配置
5. 保存 bd → **Generate Output Products → Export Hardware**（勾选 FSBL）
6. `Project > Launch IAR` → Rebuild All 编译 FSBL.out（`procise/ql100tai_pz/SDK/ql100tai_platform/FSBL/Debug/Exe/FSBL.out`）
7. **Create Boot Image**：BIF 用 `procise/ql100tai_pz/ql100tai_pz_boot.bif`（悟空板 FSBL + prebuilt bl31.elf + u-boot.elf + `[fsbl_config]apu_x64`），输出 BOOT.bin
8. **实测结果**：璞致板完整启动 bootrom→FSBL→bl31→u-boot→Linux 5.4.52（4×A53）→ Buildroot login