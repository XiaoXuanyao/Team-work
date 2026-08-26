# 04 example/yolov10_icraft —— YOLOv10 icraft 官方示例

> 位置：`boatdet/example/yolov10_icraft/`

## 用途

复旦微 icraft 的 YOLOv10 官方示例（THU-MIG/YOLOv10 + icraft 编译/部署），覆盖从模型转换（icraft 编译）到板载推理（deploy）的全流程，含 ultralytics 源码。

## 结构

```
yolov10_icraft/
├── 1_scripts/          # 推理/保存/可视化脚本（0_infer.py、1_save.py、2_save_infer.py）
├── 2_compile/          # icraft 编译配置
│   ├── config/         #   BY/ZG 编译配置（yolov10_16/int8/mix、bf16/fp16/tf32 toml）
│   ├── fmodel/         #   torch 权重（yolov10n_640x640.pt）
│   └── qtset/          #   量化校准集（coco 图片）
├── 3_deploy/           # 部署
│   ├── cfg/            #   推理配置
│   ├── imodel/         #   编译产物
│   ├── io/             #   输入/输出/golden
│   ├── modelzoo_utils/ #   运行时库（pyrtutils）
│   ├── src/            #   推理代码
│   └── metrics/        #   精度评估
├── ultralytics/        # ultralytics 源码（YOLOv10 训练/推理）
├── examples/           # 各框架推理示例（ONNX/OpenCV/LibTorch 等）
├── docker/ docs/ figures/ weights/
├── app.py  flops.py  yolov10.yaml ...
└── README.md           # YOLOv10 官方说明
```

## 典型流程

1. **编译**（2_compile）：`icraft` 将 `.pt` 权重按 `config/BY/yolov10_int8.toml` 编译为 imodel（`fmodel/` → `imodel/`），qtset 提供量化校准图
2. **部署**（3_deploy）：用 `modelzoo_utils/pyrtutils` 加载 imodel，`session.forward` 推理，`metrics` 评估精度
3. **脚本**（1_scripts）：`0_infer.py` 推理、`1_save.py` 保存结果、`2_save_infer.py` 推理+保存

## 与本项目关系

- 提供 icraft 编译/部署的**完整参考**（配置、量化、运行时）
- `modelzoo_utils/pyrtutils` 与 `yolo26_demo/pyrtutils` 同源（icraft 运行时库）
- 板载跑 YOLOv10 时按 `03-位流适配` 就绪后，用 `3_deploy` 流程 + 板载 cfg 运行

## 说明

- 编译需 icraft 工具链（主机端），板上只跑 `3_deploy`（推理）
- 权重 `fmodel/yolov10n_640x640.pt` 已含（11MB）
