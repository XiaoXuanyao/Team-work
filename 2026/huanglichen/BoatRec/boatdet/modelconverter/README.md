# modelconverter —— YOLO26 → 复旦微布衣(BUYI)格式转换

把训练得到的 **YOLO26 权重**（Detect 头含 one2many + one2one 双分支）转换为璞致板
（FMQL100TAI900，buyi 后端）可部署的 **`*_BY.json` + `*_BY.raw`**，供
`yolo26_demo/run_yolo26.py` 加载推理。

## 全链路

```
YOLO26.pt
  ├─ prune  ──▶ one2one 剪枝（去 one2many 头，可另存 .pt）
  ├─ export ──▶ one2one.onnx（NCHW 输入，opset17）
  └─ compile（五阶段 icraft）
       parse → optimize → quantize → adapt → generate
        └──────────────▶ *_BY.json/.raw
```

## 结构

```
modelconverter/
├── input/                # 输入 YOLO26 .pt
├── output/               # 一模型一目录
│   └── <name>/           # 如 yolo26/
│       ├── imodel/BY/<bits>/   # 五阶段中间模型（*_parsed/_optimized/_quantized/_adapted）
│       ├── temp/               # 中间产物（.onnx、pruned .pt、icraft 工作目录）
│       ├── <name>_BY.json      # 最终部署产物
│       └── <name>_BY.raw
├── src/                  # 一阶段一文件
│   ├── prune.py          #   one2one 剪枝
│   ├── export.py         #   onnx 导出（NCHW, opset17）
│   ├── parse.py          #   icraft 阶段1
│   ├── optimize.py       #   icraft 阶段2
│   ├── quantize.py       #   icraft 阶段3（校准集量化）
│   ├── adapt.py          #   icraft 阶段4
│   ├── generate.py       #   icraft 阶段5
│   └── compile.py        #   五阶段编排
├── modelconverter.py     # 唯一主入口
└── README.md
```

## 环境

| 阶段 | 依赖 | 环境 |
|---|---|---|
| `prune`/`export` | torch + ultralytics(≥8.4) + onnx | 项目 `.conda`（python 3.10） |
| `compile`（parse~generate） | icraft CLI | Windows，默认 `C:/Icraft/CLI`（`--icraft` 可改） |

## 用法

```powershell
& .conda\python.exe boatdet\modelconverter\modelconverter.py <子命令> ...

# 全链路：.pt -> output/<name>/<name>_BY.json/.raw
& .conda\python.exe boatdet\modelconverter\modelconverter.py all `
    --weights input\yolo26.pt --classes 13 --name yolo26

# 或分步
& .conda\python.exe boatdet\modelconverter\modelconverter.py prune --weights input\yolo26.pt --classes 13 --name yolo26
& .conda\python.exe boatdet\modelconverter\modelconverter.py export --weights input\yolo26.pt --classes 13 --name yolo26 --inspect
& .conda\python.exe boatdet\modelconverter\modelconverter.py compile --name yolo26

# 单独跑某一阶段（自动定位 output/<name>/imodel/BY/8/ 下的输入）
& .conda\python.exe boatdet\modelconverter\modelconverter.py parse     --name yolo26
& .conda\python.exe boatdet\modelconverter\modelconverter.py optimize  --name yolo26
& .conda\python.exe boatdet\modelconverter\modelconverter.py quantize  --name yolo26
& .conda\python.exe boatdet\modelconverter\modelconverter.py adapt     --name yolo26
& .conda\python.exe boatdet\modelconverter\modelconverter.py generate  --name yolo26
```

每个模型用 `--name <模型名>` 决定输出目录 `output/<name>/`。最终产物 `output/<name>/<name>_BY.json/.raw`，中间在 `output/<name>/imodel/BY/<bits>/`，onnx/pruned 在 `output/<name>/temp/`。

子命令：`prune` / `export` / `parse` / `optimize` / `quantize` / `adapt` / `generate` / `compile` / `all`。

## 关键点

- **one2one 剪枝**：`Detect` 头 `end2end=True` 时含 one2many(cv2/cv3) + one2one(one2one_cv2/3)
  两套权重；`prune` 只保留 one2one，逐尺度输出原始 cls logits + box ltrb。
- **ONNX 输入为 NCHW `[1,3,640,640]`**（模型原生布局）；部署输入 `[1,640,640,3] NHWC` 由
  icraft 依 toml `inputs_layout` 插入布局转换，最终模型 INPUT 为 NHWC。
- **icraft 无 `compile` 命令**：五阶段由独立 exe（`icraft-parse/optimize/quantize/adapt/generate.exe`）
  驱动，`compile.py` 依次调用。
- **单主输出**：icraft 模型只有一个 Output op（如 `[1,80,80,13]`），检测头 6 个张量由内部
  HardOp 产生，运行时返回多个输出（与复旦微 json 同构）。
- **quantize 离线完成**：用校准集 `qtset/coco` 做 kld/channel/int8 量化，无需板子。
- **adapt 默认不启用 DetPost/ImageMake**（保持原始特征输出，匹配 `run_yolo26.py` decode）；
  需要硬件后处理用 `--custom_config` 指定 customop toml。

## 校准集（qtset）

默认复用 `boatdet/example/yolov10_icraft/2_compile/qtset/`（COCO 图）。Boat 检测建议用实际
场景图替换，保持 `qtset/coco/*.jpg` + `qtset/coco.txt`（每行一张图），`--qtset` 指定。

## 备注

- 参考：`docs/04-模型AI加速例程/01-Icraft模型转换流程.md`
- 安装：`docs/99-参考资料/ICraft/README.md`
- 最终产物 `output/<name>/<name>_BY.json/.raw` 请上板用 `yolo26_demo/run_yolo26.py` 验证
  （当前测试权重为 COCO 80 类，用户实际模型为 13 类时主输出为 `[1,80,80,13]`）。
