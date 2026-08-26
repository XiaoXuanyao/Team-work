# 01 boatdet 目录创建过程

## 背景

璞致板（FMQL100TAI900）的 icraft NPU（buyi backend）推理需要一套板载运行目录：icraft 运行时库（pyrtutils）、模型文件、测试图片、推理脚本。`boatdet` 即为此目的整理的本机来源目录，与板上 `/root/boatdet` 保持一致。

## 来源

| 来源 | 说明 |
|---|---|
| 复旦微 icraft 官方模型/工具 | pyrtutils 运行时库（`icraft_utils.py`、`Netinfo.py`、`modelzoo_utils` 等）、YOLO 模型（imodel） |
| YOLO26 | 板载 YOLO26 模型（`yolo26_0715_BY.json`/`.raw`，buyi 后端，13 类） |
| yolov10_icraft | 复旦微 YOLOv10 icraft 官方示例（含 1_scripts/2_compile/3_deploy + ultralytics） |
| WL 万联 | yolo26_demo_cpp 内 yolo26n C++ 工程（万联后处理/推理实现） |

## 目录整理（2026-08-12）

1. **结构**：`yolo26_demo/`（Python demo）+ `yolo26_demo_cpp/`（C++ 工程）+ `example/`（yolov10_icraft 示例）
2. **删除临时测试**：顶层 `test_plddr*.py`（test_plddr.py ~ test_plddr5.py，PL DDR 诊断脚本）已删除——它们是为位流适配排查临时创建，完整副本保留在 `docs/99-参考资料/复旦微UDP服务器全部资料/.../04_FPAI/06_临时（谨慎下载）/one_input_32ddr解压产物/`（HTTP 服务目录）
3. **用途变更**：boatdet 仅保留 AI 推理例程相关，位流/PL DDR 排查文档归入 `docs/03-位流适配`

## 板上同步方式

- 本地 `boatdet` 为来源；板上 `/root/boatdet` 同步（scp 或通过本机 HTTP 服务 `http://169.254.135.10:8000/` 下载）
- 板载运行需先配置：icraft 3.31.x、numpy/opencv/yaml/pandas/matplotlib（见 `02-NPU环境/03-板上环境配置.md`）

## 已知说明

- 创建的具体时间点/逐步操作以开发时记忆为准，本文档记录当前结构与用途
- `yolo26_demo_cpp` 内含编译产物（build_arm/build_win），如需源码请以 `src/`、`WL/src/` 为准
