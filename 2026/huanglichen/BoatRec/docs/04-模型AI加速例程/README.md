# 04 模型 AI 加速例程

> 璞致板（FMQL100TAI900）NPU 上的模型推理例程。记录 `boatdet` 目录的创建过程与各项目说明。

## 目标

在璞致板 PL DDR 就绪后，用 icraft（buyi backend）跑 YOLO 检测推理（YOLO26 / YOLOv10），作为 NPU 可用性验证与应用示例。

## 关键资源（本地）

| 资源 | 路径 |
|---|---|
| 板载部署目录（本地来源） | `boatdet/`（项目根目录） |
| 板上目录 | `/root/boatdet`（本地同步） |
| icraft 运行时 | icraft 3.31.x（板上 `/usr/local/lib/python3.8/dist-packages/icraft`） |
| 推理依赖 | numpy 1.23 / opencv 4.6 / yaml / pandas / matplotlib（板上已装） |

## 目录结构（boatdet）

| 目录 | 说明 |
|---|---|
| `yolo26_demo/` | **YOLO26 板载推理/评估代码集**：`board/`（板上脚本：run_yolo26/eval/diag + 公共后处理 yolo26_post）、`eval_local/`（本机工具：FP32 验证/指标/上板）、`pyrtutils`（运行时库）、cfg/imodel/io/names |
| `yolo26_demo_cpp/` | **yolo26n C++ 工程**（CMake，含 WL 万联 yolo26n 版本、后处理） |
| `example/` | **yolov10_icraft 官方示例**（YOLOv10 + icraft 编译/部署全套，ultralytics 源码） |

## 当前进度

- [x] boatdet 目录整理（临时测试脚本已删除，见 `01-boatdet创建过程.md`）
- [x] yolo26_demo 板载推理脚本就绪（`run_yolo26.py`）
- [x] **YOLO26 推理 + 可视化跑通**（PL DDR 就绪，见 `03-位流适配`）
- [x] **ImageMake/DetPost 硬件加速**：253ms→20.9ms（约 12×），见 `03-ImageMake数据链路优化.md`
- [x] **新定稿（2026-08-15）**：MuSGD 微调模型 chusai_finetune2 + DetPost，板上
      **0.619/0.805/0.722 @ 20.9ms**（旧定稿 chusai 0.591/0.785），见 `00-例程/05-微调与量化实验.md`
- [ ] yolo26_demo_cpp（yolo26n C++）板载编译运行
- [ ] yolov10_icraft 编译/部署链路验证

## 依赖

- 位流：`docs/03-位流适配`（PL DDR 32bit 适配 + custop2 MMU/Norm/Softmax，已就绪）
- 环境：`docs/02-NPU环境`（icraft 环境、板上配置）

## 文档列表

| 文档 | 内容 |
|---|---|
| `01-Icraft模型转换流程.md` | icraft 编译流程（parse→optimize→quantize→adapt→generate）、BUYI/ZG 差异、yolo26n one2one/DFL 处理思路 |
| `01-boatdet创建过程.md` | boatdet 目录创建背景、来源、板上同步方式 |
| `02-yolo26_demo.md` | Python 板载推理 demo 说明 |
| `02-开发板测试项目.md` | 开发板 NPU 测试项目（yolo26_demo）部署/运行/结果 |
| `03-ImageMake数据链路优化.md` | ImageMake 硬件预处理（253ms→38.5ms）+ DetPost 硬件后处理（20.9ms）+ 编译坑（mix 禁用）+ DetPost 解码逆向 |
| `03-yolo26_demo_cpp-yolo26n.md` | yolo26n C++ 工程说明 |
| `04-yolov10_icraft.md` | yolov10_icraft 官方示例说明 |
| `00-例程/05-微调与量化实验.md` | **MuSGD 微调 → 量化编译（无 mix）→ 板上定稿 0.619** 完整实验记录 |

## 当前进度（补充）

- [x] **ImageMake 数据链路优化**：位流已含 ImageMake 硬件（无需重编译）；正确调用模式
      `dmaInit` 每帧 + `device.reset(1)`，输入 640×640 uint8 → forward 253ms→**37ms**（约 6.8×）。
      详见 `03-ImageMake数据链路优化.md`。
- [x] **DetPost 定稿切换**：chusai_finetune2（MuSGD 微调，无 mix 编译）+ DetPost =
      **0.619/0.805/0.722 @ 20.9ms**。⚠️ 编译纪律：quantize **禁用 `--mix_precision auto`**。
