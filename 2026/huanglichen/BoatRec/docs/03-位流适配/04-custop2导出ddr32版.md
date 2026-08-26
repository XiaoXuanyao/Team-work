# 04 custop2 导出 ddr32 版（含 MMU + Norm/Softmax）

> 解决 `02`/`03` 遗留问题：32ddr 位流（AI_Mate v1.1）缺 MMU 与 Norm/Softmax 硬件算子，yolo26 推理卡在 `MMU is not enabled` + `No Norm and Softmax HardWare`。本方案以 **custop2（AI_Mate v2.0）** 工程为基座，改造璞致 DQ32 引脚，导出**璞致板可用、且带 MMU + Norm/Softmax 硬件**的位流。

## 1 背景与目标

- **32ddr 位流**（`02` 产出，AI_Mate v1.1）已通过璞致引脚改造、PL DDR 已通（PLDDR OK），但 **无 MMU、无 Norm/Softmax 硬件** → yolo26 推理卡在算子层。
- **目标**：获得璞致板（DQ32 引脚）+ **MMU + Norm/Softmax 硬件** 的位流，使 yolo26 推理可跑通。

## 2 根因：AI_Mate IP 版本差异

| 维度 | 32ddr 工程 | custop2 工程（`25060601`） |
|---|---|---|
| AI_Mate 版本 | **1.1** | **2.0** |
| norm/softmax | 单开关 `Enable_Norm_Softmax=false` | 分项全开：`Enable_Layernorm`/`InstanceNorm2d`/`Normalize`/`Softmax`/`SptPost_max`/`SptPost_sample` 全 true |
| MMU | **无**（`modeInfo=0` → `MMU is not enabled`） | **内置**（AI_Mate v24090904 起固定硬件） |
| DDR | DQ32 | DQ64（悟空板基座） |

- `No Norm and Softmax HardWare`（寄存器 `0x23110206` 检查失败）= 32ddr 的 `Enable_Norm_Softmax=false`。
- `MMU is not enabled` = v1.1 位流本身无 MMU 硬件。
- **结论**：换用 custop2（AI_Mate 2.0）作基座，自带 MMU + Norm/Softmax；只需把 DDR 改到璞致 DQ32。

## 3 custop2 工程改造璞致 DQ32 引脚

**工程来源**：`参考实现\悟空开发板\附：CustomOP集合位流\25060601\FPGA工程\bywk_one_display_custop2_25060601.zip`（AI_Mate 2.0，悟空板 DDR64）。

**工作目录**（独立，不碰 32ddr）：`D:\HLCH\Works\BoatRec\vivado\custop2_puzhi\bywk_one_display_custop2_25060601`

**关键发现**：该工程 MIG 的 `XML_INPUT_FILE = mig_b.prj`（**不是 mig_a.prj**！）——改 MIG 引脚必须改 `mig_b.prj`（两处：`sources_1\ip\mig_7series_0` + `ps_in.ip_user_files\mem_init_files`）。

| 改动 | 文件 | 说明 |
|---|---|---|
| MIG 引脚 | `mig_b.prj`（两处） | 用 32ddr 已验证璞致 `mig_a.prj`（DataWidth=32、71 引脚）**整体覆盖**；`mig_a.prj` 不动 |
| PL DDR 位宽 | `AI_Mate_0.xci` | `PLDDR_WIDTH` 64→32（MODELPARAM + PARAM 两处） |
| 宏 | `ddr_width.v` | `DDR64`→`DDR32` |
| 约束 | `7100_peripheral.xdc` | 取消 REQP-52/56 注释 |
| 补丁 | `ip_patch\process_control\write_bitstream_pre.tcl` | 末尾追加 REQP-52/56 SEVERITY Warning |

> 备份：各文件改动前存 `.bak_ddr64`。MIG 覆盖后 regenerate 校验：`dq[0]=J3、addr[0]=H7、reset_n=E11、DataWidth=32`、AI_Mate app 接口 `[255:0]`。

## 4 综合/实现/出位流（Vivado 2018.3 + 补丁）

1. 设 `JFM_PATH=D:\HLCH\Works\BoatRec\patches\JFM_Kits`，重启 Vivado；打开 `ps_in.xpr`。
2. **AI_Mate_0 升级**：因手动改 `.xci` 导致 `.xml` stale 被锁 → GUI `Report IP Status`/`Refresh IP` 触发 upgrade（选 **core container disabled**）→ upgrade 后 `PLDDR_WIDTH=32` 保留，端口 `512→256bit`（DQ32 预期，非错误）。
3. 综合/实现/Generate Bitstream → 产出 `ps_in.runs\impl_3\ai7100_top.bit`（17.4MB）。

## 5 位流字节交换转换（关键经验）

**fpga_manager 正确格式 = 标准 bin 每 4 字节反转（byte-swap）**，sync = `66 55 99 AA`。

| 格式 | sync | 结果 |
|---|---|---|
| 标准 .bit | `AA 99 55 66` | `could not find a sync word` |
| write_cfgmem `bpix8` | `55 99 AA 66`（bit 反转） | `could not find a sync word` |
| **标准bin 每4字节反转** | **`66 55 99 AA`** | **✅ operating** |

**验证锚点**：板子上已知成功文件 `ai7100_top_puzhi_swap.bin`（MD5 `D6422805...`）= 电脑 `data\bitstream\ai7100_top_puzhi.bin` **每 4 字节反转**（MD5 逐字验证一致）。

**转换命令**：
```python
# 1) 构造标准 bin = 48字节头 + 配置数据(.bit 从 sync 152 起)
std = open('data/bitstream/ai7100_top_puzhi.bin','rb').read()[:48] + \
      open(custop2_bit,'rb').read()[152:]
# 2) 每 4 字节反转
out = bytearray(len(std))
for j in range(0, len(std)-3, 4):
    out[j:j+4] = std[j:j+4][::-1]
```

## 6 上板验证结果（2026-08-13，✅ 核心目标达成）

| 验证项 | 结果 |
|---|---|
| 位流加载 | ✅ `state=operating`（dmesg 无错误） |
| **PLDDR**（璞致引脚适配） | ✅ `test_plddr6.py` → `PLDDR OK`，`read back match: True` |
| **MMU 检查** | ✅ 不再报 `MMU is not enabled` |
| **Norm/Softmax 检查** | ✅ 不再报 `No Norm and Softmax HardWare` |
| 设备识别 | ✅ `device: 25060601`、模型加载、`SESSION APPLY DONE` 正常 |
| **yolo26 推理** | ✅ **跑通**（3 张图 forward 成功，见 §7） |

## 7 segfault 根因与修复（2026-08-13 ✅）

**yolo26 推理已跑通**，3 张图 forward 全部成功、无 segfault、输出形状正确。

**segfault 根因有两层**：

1. **模型 json 被误改**：此前为绕 32ddr 无 MMU，把 `yolo26_0715_BY.json` 的 `tags.speedmode / compressFtmp` 从 `true` 改成 `false`，但 **`.raw` 编译产物未重新编译** → json 与 raw 不一致、与 yaml（`mmuMode/speedmode/compressFtmp=true`）三者全不一致。**修复**：恢复 json 两 tag 为 `true`（与 `.bak_speedmode` 原版逐字一致），`Netinfo MMU: True`。
2. **输入 tensor 缺 batch 维**：`run_yolo26.py` 传 3D `rgb (640,640,3)`，而网络期望 4D `[1,640,640,3]`；`numpy2Tensor` 用 `input_array.shape` setShape，native 按 4D 布局读 → 越界 segfault。**修复**：`numpy2Tensor(rgb[np.newaxis, ...], network)`（对照 `pyrt_main_example.py` 标准用法有 `unsqueeze(0)`）。

**验证输出**（`=== 000000000139.jpg ===`）：
```
out[0..5] shape=[1,80,80,13/4],[1,40,40,13/4],[1,20,20,13/4] dtype=@fp(32)
numpy[0] (1,80,80,13) min=-164.9 max=-31.5 ...  (bus/bc 同理)  → DONE
```

### 7.1 segfault 诊断过程（排除法）

1. **`-X faulthandler` 精确定位**：崩溃前打印 `Fatal Python error: Segmentation fault` + `File "run_yolo26.py", line 55 in main` → 锁定在 `session.forward([tensor])`，且 `numpy2Tensor`（line 53）已成功。
2. **排除 icraft 版本**：`Icraft v3.31.0 解析 v3.31.1 编译模型` 仅 warning，用户确认完全兼容 → 非根因。
3. **排除 C++ 例程对照**：`yolo26_demo_cpp/WL/yolo26n.cpp` 面向 **WL170 device**（非 ql100aiu/axi），不适用本板 → 不能直接对照。
4. **对照标准例程**：`pyrt_main_example.py:104,108` 构造输入时 `img.unsqueeze(0)` 加 batch 维、传 4D；而 `run_yolo26.py` 传 3D → **命中根因②**。
5. **核对 json 与 raw**：`git diff` 备份 `.bak_speedmode`（原版 speedmode=true）确认 json 只改了两 tag，raw 未重编译 → **命中根因①**。

**定位命令**（板上）：`python3 -X faulthandler run_yolo26.py cfg/yolo26_board.yaml`（faulthandler 会打印崩溃 Python 行号）。

> 辅助：icraft 运行时 v3.31.0 解析 v3.31.1 编译模型仅 warning，不影响。

## 8 yolo26 后处理 + 可视化（2026-08-13 ✅）

`run_yolo26.py` 已加入完整后处理：**解码 → NMS → 画框 → 保存**，输出到 `io/output/visual/res_<原图名>.jpg`。参照 C++ 例程 `yolo26_demo_cpp/src/postprocess_yolo26.hpp` 的 `post_detpost_soft`（fp32 NHWC 布局：6 个输出 = 3 头 × {13 class, 4 box}）。

**处理流程**：
1. **decode**：遍历 3 头（stride 由 `input_size/特征图H` 推导 = 8/16/32），每格取分类 argmax + sigmoid，`>conf`(0.25) 才解码
2. **box 解码**（yolo26 无 DFL，4 通道直接解码）：
   ```
   x1 = grid_x+0.5 - b[0]; y1 = grid_y+0.5 - b[1]
   x2 = grid_x+0.5 + b[2]; y2 = grid_y+0.5 + b[3]
   cx = (x2+x1)/2*stride; cy = (y2+y1)/2*stride
   w  = (x2-x1)*stride;  h  = (y2-y1)*stride
   ```
3. **NMS**：`cv2.dnn.NMSBoxes`（iou=0.45）
4. **letterbox_inverse**：640×640 左上对齐 letterbox 的 (cx,cy,w,h) → 原图坐标（`/scale` 放大 + 裁剪到边界）

**关键坑（box 解码曾错）**：
- decode 输出的是**中心格式** (cx,cy,w,h)；**letterbox_inverse 必须按中心格式换算**（`x1=(cx-w/2)/scale`），不能当左上角 `(x1,y1,w,h)` 用
- 错误症状：**框左上角点 = 目标中心点**（用户根据标注 `D:\HLCH\Datasets\BBLabel_4yolo` 确认）
- 验证：bc_1222 检测框 (85,218)-(589,370) vs GT (84,227)-(592,366) 完美贴合

**实测**（璞致板 + custop2 位流）：
- 三图全流程跑通：000000000139→bc 0.261；bc_106→bc 0.739；bc_1222→bc 0.739（bus 图无船 0 检测，13 类全为船舶类）
- bc_106（船占图 91% 高度、超大目标）检测中心略偏左 ~100px，因落在 stride=32 的 20×20 头（grid 分辨率 32px），属模型尺度定位精度，非解码错误；框仍覆盖整船

## 9 后续优化方向

- 当前 `DETPOST_ON=False`，软件后处理（NMS+画框）已跑通；可接硬件 **DetPost + NMS** 提升效率
- 或用 C++ 例程 `yolo26_demo_cpp` 跑完整检测流程（注意默认面向 WL170，需改 ql100aiu/axi）
- 13 类为船舶自定义模型（bc/blj/dlj/...）；如需通用目标检测，需编译 COCO 版模型（yolov10_icraft 的 imodel 为空，需从 `yolov10n_640x640.pt` 编译）

## 10 关键路径

| 项 | 路径 |
|---|---|
| custop2 工程（改造后） | `D:\HLCH\Works\BoatRec\vivado\custop2_puzhi\bywk_one_display_custop2_25060601\PLIN.xpr\ps_in\ps_in.xpr` |
| custop2 位流 | `...\ps_in.runs\impl_3\ai7100_top.bit` |
| 字节交换 bin | `D:\HLCH\Works\BoatRec\data\bitstream\ai7100_top_custop2_puzhi_swap.bin` |
| 32ddr 工程 | `D:\HLCH\Works\BoatRec\vivado\PLIN.xpr\ps_in\ps_in.xpr` |
| 成功格式锚点 | 板 `ai7100_top_puzhi_swap.bin`（MD5 `D6422805...`）/ 电脑 `data\bitstream\ai7100_top_puzhi.bin` |
| custop2 原 zip | `参考实现\悟空开发板\附：CustomOP集合位流\25060601\FPGA工程\bywk_one_display_custop2_25060601.zip` |
