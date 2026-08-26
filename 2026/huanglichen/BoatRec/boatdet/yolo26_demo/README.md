# yolo26_demo —— YOLO26 板载推理与评估

璞致板（FMQL100TAI900 / ql100aiu）YOLO26（13 类船舶）NPU 推理、评估、诊断的代码集。

## 目录结构

```
yolo26_demo/
├── board/                 # ★ 板上运行的脚本（同步到 /root/boatdet/yolo26_demo/board/）
│   ├── run_yolo26.py      #   推理 + 可视化（cfg 驱动）
│   ├── eval.py            #   批量评估：--model <name> [--mode auto|detpost|soft]（DetPost/软件后处理自动选择）
│   ├── diag.py            #   诊断：--task probe（输出结构探测）/ --task bench（ImageMake 基准+画框）
│   └── yolo26_post.py     #   公共后处理模块（decode/decode_detpost/nms/letterbox/13 类表）
├── eval_local/            # ★ 本机工具（PC，.conda 环境，不用板子）
│   ├── fp32_eval.py       #   FP32 验证：--weights 1..n → preds + mAP
│   ├── eval_coco_metrics.py  # COCO 指标计算（labels 根目录自动识别 val 子目录）
│   ├── board_eval.py      #   上板工具：上传模型/脚本 → 执行评估/探测 → 拉回 preds
│   ├── chusai_local.yaml  #   本机数据集配置
│   └── README.md
├── cfg/                   # 推理配置（yolo26_board.yaml 等，run_yolo26.py 用）
├── imodel/                # 部署模型 *_BY.json/.raw（板上同步）
├── io/                    # 输入图片 / 输出（preds_*.json、visual/）
├── names/                 # 类别名文件
└── pyrtutils/             # icraft 运行时封装（getJrPath/loadNetwork/initSession/forward）
```

## 工作流

```powershell
# 1) 本机 FP32 验证（训练/微调后）
& .conda\python.exe boatdet\yolo26_demo\eval_local\fp32_eval.py --weights <one或多个.pt>

# 2) icraft 编译（boatdet/modelconverter，quantize 禁用 --mix_precision）
#    → output/<name>/imodel/BY/8/<name>_BY.json/.raw

# 3) 上板评估（上传模型+脚本 → 板上跑 → 拉回 preds_<model>.json）
& .conda\python.exe boatdet\yolo26_demo\eval_local\board_eval.py --model <name>
#     --task probe 结构探测（排查 DetPost 输出异常）
#     --task bench  ImageMake 基准

# 4) 本机指标
& .conda\python.exe boatdet\yolo26_demo\eval_local\eval_coco_metrics.py `
    --preds boatdet\yolo26_demo\io\output\preds_<name>.json `
    --labels data\chusai_4yolo\labels --shapes boatdet\yolo26_demo\io\output\img_shapes.json
```

## 说明

- 板上脚本统一假设工作根为 `yolo26_demo/`（ROOT=脚本上上级目录），imodel/io/names/cfg 均相对 ROOT。
- 路径约定：评估输出 `io/output/preds_<model>.json`；可视化 `io/output/visual/`。
- 板上登录：root（密码见 `.dsh/docs/03-板上环境.md`），板 IP 169.254.135.20。
- 详细过程文档：`docs/04-模型AI加速例程/`；工作区记忆：`.dsh/`。
