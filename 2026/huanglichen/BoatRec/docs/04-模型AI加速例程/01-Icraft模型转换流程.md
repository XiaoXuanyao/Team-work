# 01 Icraft 模型转换流程

> 记录 icraft（复旦微 FMQL100TAI / ql100aiu / BUYI 平台）的模型编译转换流程，以及 yolo26n 的 one2one/one2many 与 box 头处理思路。依据 `boatdet/example/yolov10_icraft`、`boatdet/yolo26_demo_cpp`、`boatdet/yolo26_demo`、官方资料及 `boatdet/modelconverter`（实测跑通）整理。

## 1 背景

- 璞致板（FMQL100TAI900，device `ql100aiu`）用 icraft 3.31.x 部署 YOLO 检测模型。
- 模型从源格式（`.pt`/`.onnx`）编译为可部署的 **`.json`（图）+ `.raw`（权重）** 一对文件。
- BUYI（布衣）为 ql100aiu 后端；ZG（诸葛）为 ZG330 后端。

## 2 icraft 编译流程

### 2.1 入口命令

> **实测（icraft v3.31.1）：不存在 `icraft compile` 命令。** 官方 example 文档里写的
> `icraft compile config/BY/<模型>.toml` 并非独立子命令；实际编译由各阶段独立可执行文件
> 驱动（见 §2.2 产物与 `icraft-*.exe`）。`icraft.exe` 只是统一入口（`icraft <command> <toml>`），
> 会把 command 映射到 `bin/icraft-<command>.exe`，但 `bin/` 下**没有 `icraft-compile.exe`**。

官方 example 用一个 toml 内含多个 section 逐阶段串联；但每个阶段也可由 `bin/icraft-*.exe`
**直接命令行参数**单独执行（`icraft-<stage> --help` 查看参数）。`boatdet/modelconverter`
采用后者（一阶段一脚本）。

### 2.2 五阶段流水线（toml section / 独立 exe 与输入输出）

| 阶段 | toml 节 | 独立 exe | 输入 → 输出 | 作用 |
|---|---|---|---|---|
| parse | `[parse]` | `icraft-parse.exe` | `fmodel/x.onnx` → `x_parsed` | 框架模型导入；输入 `[1,3,640,640] NCHW`（源模型）、部署输入 `[1,640,640,3] NHWC`、`pre_method=resize`、`pre_scale/pre_mean`、`channel_swap` |
| optimize | `[optimize]` | `icraft-optimize.exe` | `x_parsed` → `x_optimized` | 图结构优化 |
| quantize | `[quantize]` | `icraft-quantize.exe` | `x_optimized` → `x_quantized` | 用 `qtset/coco` 校准集量化：BY 用 `bits=8`、`saturation=kld`、`per=channel` |
| adapt | `[adapt]` | `icraft-adapt.exe` | `x_quantized` → `x_adapted` | 插入自定义算子 `customop.ImageMakePass`/`customop.DetPostPass`（BY 启用，ZG 禁用） |
| generate | `[generate]` | `icraft-generate.exe` | `x_adapted` → `x_BY.json/.raw` | 生成最终片上部署模型 |
| run | `[run]`（可选） | `icraft-run.exe` | BY 模型 + qtset 图 | 板上推理 / 精度 dump（`dump_format=SFB`） |

- 产物落到 `3_deploy/imodel/BY|ZG/`，各阶段中间产物 `x_parsed/_optimized/_quantized/_adapted` 同名 json+raw。
- 参考配置：`boatdet/example/yolov10_icraft/2_compile/config/ZG/yolov10_tf32.toml`。

### 2.3 BUYI vs ZG 平台差异

| 维度 | BUYI（ql100aiu） | ZG（ZG330） |
|---|---|---|
| toml target | `buyi` / `BUYI` | `zhuge` |
| 量化 | `bits=8/16`、`mix_precision` | `qdtype=tf32/bf16/fp16/int8` |
| adapt 自定义算子 | 启用 DetPostPass/ImageMakePass | 禁用（注释） |
| 产物命名 | `*_BY.json/.raw` | `*_ZG.json/.raw` |
| 运行时后端 | `buyi`（固定取 BY.json） | `zg330`（固定取 ZG.json） |
| 设备 URL | `socket://ql100aiu@IP:9981`（x86）/ `axi://ql100aiu`（aarch64） | `socket://haps-zg330@IP:5001` |

## 3 yolo26n 的 one2one / DFL 处理

### 3.1 核心结论

**one2one/one2many 与 DFL 是两个独立概念，不要混淆：**

| 概念 | 含义 | 归属 |
|---|---|---|
| **one2one / one2many** | 标签分配：one2many 每个对象匹配多个 anchor（训练），one2one 每个对象只匹配一个（推理端到端、免 NMS） | 分类匹配 |
| **DFL** | box 回归解码：box 边界用分布预测，需 `DFL` 把 64 通道分布解码成 4 个 ltrb | box 回归 |

### 3.2 one2one 化的证据（结构性）

- one2one/one2many 删减发生在**训练后导出 ONNX 阶段**（仓库无导出脚本）。
- 编译产物 `yolo26_0715_BY.json` 元信息为 `framework_kind: ONNX, opset17`，即 icraft 编译输入已是 one2one 化的 ONNX。
- **只有单一检测头**：6 输出 = 3 尺度 × {类别[13], box[4]}（stride 8/16/32）；若保留 one2many 双头应为 12 输出。
- **图内无 NMS 算子**：模型图本身端到端。
- **但部署后处理仍保留 NMS**（`nms_soft`/`nms_hard`/`cv2.dnn.NMSBoxes`，yaml `fpga_nms=false` 用软件 NMS）——是"one2one 端到端 + 软件 NMS 兜底"，并非完全免 NMS。

### 3.3 DFL 与 yolo26n

- **yolo26n 不用 DFL**：`bbox_info_channel=4`（`yolo26_demo_cpp/WL/src/yolo26n.cpp:71`），box 头直接输出 4 通道 ltrb（`postprocess_yolo26.hpp` 直接取 4 值，无 `dfl()` 调用）。
- **这不是"因为 one2one"**：反例是 **YOLOv10 同样 one2one 但仍用 DFL**（`postprocess_yolov10.hpp` 走 `dfl()`、`boxPtr + w*64`，64 通道）。
- 正确表述：**yolo26 的 box 头本身就改成了直接回归（4 通道 ltrb，跳过 DFL 分布解码）**，与是否 one2one 无关。

## 4 检测头算子的 FPGA/CPU 分工

- 编译后主干网络 296 个 `HardOp` 为 `@buyit`（FPGA/片上）。
- 检测头 sigmoid/softmax 归一化 + 输出提取（Cast/PruneAxis）为 `@hostt`（CPU）。
- **`boatdet/yolo26_demo_cpp/patch_model.py`**：编译**后**把检测头 HardOp（`HEAD_OPS=[2240,2242,2244]`）从 `@buyit` 移到 `@hostt`——仅为绕**无 Norm/Softmax 硬件的旧位流**。当前 custop2 位流已含 Norm/Softmax 硬件，**无需此 patch**。

## 5 编译新模型（转换思路）

1. **准备源模型**：one2one 化的 `.onnx`（或 `.pt`），输入对齐 640×640×3 NHWC（或由 toml `inputs_layout` 指定）。
2. **写 BUYI toml**：`[parse]` 指源模型与输入格式 → `[quantize]` 准备 `qtset` 校准集（几张代表图 + 清单 `coco.txt`）→ `[adapt]` 视需启 DetPost/ImageMake → `[generate]` 输出路径。
3. **执行编译**：`icraft compile config/BY/<模型>.toml` → 生成 `*_BY.json/.raw`。
4. **部署**：json 放 `imodel/`，与 raw 配套；改 yaml（`imodel.dir/stage/run_backend=buyi`、`mmuMode/speedmode/compressFtmp`）。
5. **后处理适配**：按新模型输出布局调整 decode（分类通道数、box 通道数/编码格式）。yolo26 类 = 4 通道 ltrb；COCO 类（如 yolov10n）= DFL 64 通道，需实现 `dfl()` 解码。

## 6 实际转换流程（`boatdet/modelconverter`，2026-08-13 实测跑通）

> icraft v3.31.1（Windows，`C:/Icraft/CLI`）已安装并实测：完整 YOLO26 `.pt` → `*_BY.json/.raw`
> 编译链路跑通，产物结构与复旦微 `yolo26_0715_BY.json` 同构（23 ops、5 HardOp、单主输出）。

### 6.1 程序结构（一阶段一脚本）

```
boatdet/modelconverter/
├── input/ output/                 # 输入 .pt / 产物（imodel/BY/<bits>/ + temp/）
├── src/
│   ├── prune.py                   # one2one 剪枝（.pt -> 单头模型，可另存）
│   ├── export.py                  # onnx 导出（NCHW, opset17）
│   ├── parse.py / optimize.py / quantize.py / adapt.py / generate.py   # icraft 五阶段
│   └── compile.py                 # 五阶段编排
└── modelconverter.py              # 唯一主入口（9 子命令）
```

### 6.2 主入口命令

```powershell
& .conda\python.exe boatdet\modelconverter\modelconverter.py all `
    --weights input\yolo26.pt --classes 13 --name yolo26     # 全链路 .pt -> *_BY.json/.raw
```

子命令：`prune / export / parse / optimize / quantize / adapt / generate / compile / all`。

### 6.3 关键实现要点（实测修正）

1. **源模型 ONNX 输入为 NCHW `[1,3,640,640]`**（模型原生布局）。部署输入 `[1,640,640,3] NHWC`
   由 icraft 依 toml `inputs_layout=NHWC` 插入布局转换，最终模型 INPUT 为 NHWC
   （`[-1,-1,-1,-1] @layout(NHWC)`）。**若把 ONNX 直接导成 NHWC，icraft 会把 `[1,640,640,3]`
   当 NCHW 解析，首个 Conv 报 `Input channels C not equal to kernel` 错误。**
2. **one2one 剪枝**：`Detect` 头 `end2end=True` 时同时持 `one2many(cv2/cv3)` 与
   `one2one(one2one_cv2/one2one_cv3)` 两套权重；只保留 one2one 分支，逐尺度（stride 8/16/32）
   输出原始特征：`cls[1,H,W,nc]`（sigmoid 前 logits）+ `box[1,H,W,4]`（ltrb 偏移），与
   `run_yolo26.py` 的 `decode()` 匹配。`reg_max=1`（box 直接回归 4 通道，无 DFL）。
3. **icraft 模型为单主输出**：`*_BY.json` 只有一个 `Output` op（如 `[1,80,80,13]`），检测头
   的 6 个张量（3 尺度 × cls/box）由内部 `HardOp` 产生，运行时返回多个输出。这与复旦微 json 一致。
4. **quantize 离线完成**：用校准集 `qtset/coco` + `coco.txt`（每行一张图）做 `kld/channel/int8`
   量化，无需连接板子。
5. **adapt 默认不启用 DetPost/ImageMake**（保持原始特征输出，匹配软件后处理）；如需硬件
   DetPost，用 `--custom_config` 指定 customop toml。custop2 位流已含 Norm/Softmax 硬件，
   无需旧 `patch_model.py` 搬移。
6. **quantize 与 DetPost 组合时禁用 `--mix_precision`**（2026-08-15 实测）：mix 版产物异常
   （DetPost 输出 128→64 通道、`data_thr` 溢出 [-22]→[-4933]、generate 主输出
   `[1,80,80,64]`、HardOp 16/正常 5），板上 DetPost 输出 0 候选、mAP 全 0。
   **必须全 int8（不带 mix）编译**；`--mix_precision auto` 仅对 ImageMake 版（无 DetPost）有效。
7. **五阶段独立命令示例**（`icraft-parse` 为例，其余同理）：
   ```
   icraft-parse --net_name yolo26 --network x.onnx --jr_path out/imodel/BY/8 \
       --framework onnx --target buyi --inputs 1,640,640,3 --inputs_layout NHWC \
       --pre_method resize --pre_scale 255.0,255.0,255.0 --pre_mean 0.0,0.0,0.0 --channel_swap 0,1,2
   ```
   - `icraft-optimize --json x_parsed.json --raw x_parsed.raw --jr_path . --target BUYI`
   - `icraft-quantize --json x_optimized.json --raw x_optimized.raw --jr_path . --target buyi \
       --forward_dir qtset/coco --forward_list qtset/coco.txt --saturation kld --per channel --bits 8`
   - `icraft-adapt --json x_quantized.json --raw x_quantized.raw --jr_path . --target BUYI`
   - `icraft-generate --json x_adapted.json --raw x_adapted.raw --jr_path . --ddr_base 4096`

### 6.4 实测产物（COCO 80 类测试权重 yolo26n.pt）

| 阶段 | 产物 | 说明 |
|---|---|---|
| export | `output/temp/yolo26.onnx` | NCHW `[1,3,640,640]`, opset17, 6 输出 |
| parse | `yolo26_parsed.json/.raw` | INPUT `[-1,-1,-1,-1] NHWC`, `ai_target=@buyit` |
| optimize | `yolo26_optimized.json/.raw` | 图优化（`Rewrite exceeds max allowed` 为无害警告） |
| quantize | `yolo26_quantized.json/.raw` | int8 kld，离线校准 |
| adapt | `yolo26_adapted.json/.raw` | 未启用自定义算子 |
| generate | `yolo26_BY.json/.raw` | 23 ops, HardOp=5, 主输出 `[1,80,80,80] NHWC` |

> 用户实际 13 类模型时主输出应为 `[1,80,80,13]`。产物用 `yolo26_demo/run_yolo26.py` 上板验证。
