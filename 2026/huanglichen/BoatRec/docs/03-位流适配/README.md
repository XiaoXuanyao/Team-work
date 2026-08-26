# 03 位流适配

> 璞致板（FMQL100TAI900）PL DDR 为 32bit（DQ32），官方 AI 位流 DDR 控制器为 64bit（DQ64），导致 icraft NPU 无法运行。本文档记录排查过程、方案与进度（过程文档形式）。

## 目标

让官方 AI 位流适配璞致板 32bit PL DDR，或获得适配的 32bit 位流，使 icraft NPU 可运行。

## 核心结论

1. **根因**：璞致板 PL DDR 为 DQ32（2×MT41K256M16-107），官方位流 DDR_MIG 为 DQ64（app 512bit）→ DQ 不匹配 → MIG 校准失败 → PL DDR 不可用 → icraft 无法运行
2. **方案成立**：复旦微官方存在 DQ32 完整工程（`one_input_wk_display_24030104_32ddr`，xc7z100 + MIG7S + DataWidth32）；璞致板 DDR 引脚已确认（= 璞致 PZ_PCIE MIG = 璞致 UCF）
3. **已跑通**：MIG 改璞致引脚 → 复旦微补丁（7z100ai 数据库）解决 PS7 → 综合/实现/出位流 → **璞致引脚版位流 `ai7100_top_puzhi.bit` 产出** → byte-swap bin → **fpga_manager 加载成功（operating）→ PL DDR 写读一致（PLDDR OK）**
4. **MMU + Norm/Softmax 已解决**：升级 custop2（AI_Mate v2.0）位流（`04`），璞致 DQ32 + MMU + Norm/Softmax 硬件齐备；yolo26 不再报 `MMU is not enabled` / `No Norm and Softmax HardWare`
5. **已验证**：32ddr 位流加载璞致板成功（device 24030104），原引脚 DDR 校准失败 → 改引脚后 **DDR 校准成功（PLDDR_STATUS=1）**；custop2 位流 `device 25060601`
6. **yolo26 推理已跑通**：修复两层 segfault 根因（模型 json 误改 + 输入缺 batch 维，见 `04` §7）→ forward 成功、输出形状正确
7. **可视化已跑通**：`run_yolo26.py` 加解码+NMS+画框（`04` §8），修复 box 中心格式误当左上角；bc_1222 框与 GT 完美贴合
8. **位流开机自动加载**：U-Boot 通过 p1 FAT 的 `uEnv.txt` `fpga loadb` 自动加载 `download.bit`（标准 .bit），重启免手动 echo（`03` §7）

## 当前进度

- [x] 根因定位（DQ64 vs DQ32）
- [x] 复旦微 DQ32 官方工程确认（32ddr）
- [x] 璞致板 DDR 引脚确认（PZ_PCIE = UCF，xc7z100）
- [x] MIG 改璞致引脚（PZ_PCIE PinSelection 完整版）→ 综合 **0 critical warnings**
- [x] 顶层综合 `synth_2` Complete
- [x] **PS7 定制 IP（AI_IN）解决**（复旦微 7z100ai 数据库补丁）
- [x] 实现 + 出位流 `impl_3` → **`ai7100_top_puzhi.bit`（16.61MB）**
- [x] 位流转 **byte-swap bin** + fpga_manager 加载 **operating**
- [x] **璞致板 PLDDR 实测通过**（写读一致 `PLDDR OK`，校准成功）
- [x] **位流升级 custop2**（MMU + Norm/Softmax 硬件）→ 检查通过（见 `04`）
- [x] **yolo26 推理跑通**（修复 json 误改 + 输入缺 batch 维，见 `04` §7）
- [x] **可视化跑通**（解码+NMS+画框，修复 box 中心格式，见 `04` §8）
- [x] **位流开机自动加载**（U-Boot `fpga loadb` 加载 p1 FAT `download.bit`，重启免手动 echo，见 `03` §7）

> 遗留核查项（非阻塞）：
> - ~~硬件 DetPost + NMS 全流程~~：**已完成并定稿**（ImageMake+DetPost，20.9ms，见 `04-模型AI加速例程/03-ImageMake数据链路优化.md`）；C++ 例程 `yolo26_demo_cpp` 板载编译运行仍未做
> - 确认璞致板 PL DDR 颗粒电压（MIG 1.5V vs 旧记录 DDR3L 1.35V）
> - 下载 `100TAI对应ICraft版本说明.txt` 核实历史版本参考实现

## 关键路径速查

| 项 | 路径 |
|---|---|
| 32ddr 工程 | `D:\HLCH\Works\BoatRec\vivado\PLIN.xpr\ps_in\ps_in.xpr` |
| **custop2 工程（MMU+Norm/Softmax）** | `D:\HLCH\Works\BoatRec\vivado\custop2_puzhi\bywk_one_display_custop2_25060601\PLIN.xpr\ps_in\ps_in.xpr` |
| 璞致引脚版位流 | `D:\HLCH\Works\BoatRec\ai7100_top_puzhi.bit` |
| **custop2 位流 bin** | `D:\HLCH\Works\BoatRec\data\bitstream\ai7100_top_custop2_puzhi_swap.bin` |
| **custop2 位流标准 .bit** | `...\ps_in.runs\impl_3\ai7100_top.bit`（自动加载 download.bit 用） |
| **FAT 启动盘资源** | `D:\HLCH\Works\BoatRec\data\sd\2026-08-13_FAT_ql100tai_pz\`（含 download.bit/README.md） |
| **启动盘整卡镜像** | `D:\HLCH\Works\BoatRec\data\image\pz_icraft.bin`（p1 FAT @offset 1049088） |
| 璞致 PZ_PCIE MIG | `docs\99-参考资料\璞致资料\07.开发板教程源码\2_ARM\4_14_PZ_PCIE\Vivado_prj\PZ_PCIE\...\design_1_mig_7series_0_0\mig_a.prj` |
| 补丁包 | `D:\HLCH\Works\BoatRec\patches\JFM_Kits`（JFM_PATH 环境变量） |
| 补丁包下载站 | `docs\99-参考资料\复旦微UDP服务器全部资料\...\02_A7_K7_Z7_V7补丁（PL必须打补丁）\补丁包\IP补丁\5.3.1.6` |
| 32ddr 原始 zip | `docs\99-参考资料\复旦微UDP服务器全部资料\...\04_FPAI\06_临时（谨慎下载）\one_input_wk_display_24030104_32ddr.zip` |
| 32ddr vs 璞致引脚完整对照 | `02` §3.3 |

## 文档列表

| 文档 | 内容 |
|---|---|
| `01-问题背景与根因.md` | 问题现象、根因、证据链、下载站调查、解决路线与结果 |
| `02-璞致引脚位流改造.md` | DQ32 确认、资源准备、璞致板 DDR 引脚数据与对照、改引脚 + 打补丁生成璞致位流 |
| `03-板上实测.md` | 32ddr 位流实测（DDR 校准失败）、璞致位流后处理/转换/上板验证（成功）、custop2 位流实测、位流开机自动加载 |
| `04-custop2导出ddr32版.md` | custop2（AI_Mate v2.0）导出璞致 DQ32 + MMU + Norm/Softmax 位流；byte-swap 转换；segfault 修复；yolo26 后处理+可视化 |
