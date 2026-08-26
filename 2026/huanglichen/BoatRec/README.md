# BoatRec — 璞致板（FMQL100TAI900）NPU 船只检测

在复旦微 JFMQL100TAI900（璞致板）FPGA SoC 上运行 YOLO 船只检测推理的完整项目记录：
SD 卡启动 → NPU 环境 → 位流适配 → 模型 AI 加速，最终在 icraft 3.31（AI_Mate NPU）上跑通
YOLO26 / YOLOv10 推理并定稿。

## 本仓库内容

| 目录 | 说明 |
|---|---|
| `boatdet/` | 板载部署代码（同步到板上 `/root/boatdet`）：`yolo26_demo/`（Python 板载推理/评估）、`yolo26_demo_cpp/`（yolo26n C++ 工程）、`example/yolov10_icraft/`（官方示例）、`modelconverter/`（模型转换工具） |
| `docs/` | 里程碑文档 00~04：环境准备 → 最小 Linux 启动 → NPU 环境 → 位流适配 → 模型 AI 加速例程 |
| `data/chusai_4yolo/` | 船只检测 YOLO 数据集（4484 张，13 类，见下文） |

## 数据集（data/chusai_4yolo）

- **格式**：YOLO（`images/` + `labels/` + `data.yaml`，txt 标注：`class cx cy w h` 归一化）
- **规模**：train 3593 张 / val 891 张，共 4484 张
- **类别（13）**：

| id | 名称 | id | 名称 |
|---|---|---|---|
| 0 | hangmu（航母） | 7 | tuochuan（拖船） |
| 1 | huweijian（护卫舰） | 8 | huolunjizhuangxiangchuan（货轮/集装箱船） |
| 2 | bujijian（驱逐舰） | 9 | youlue（游艇） |
| 3 | denglujian（登陆舰） | 10 | youting（油艇） |
| 4 | haijingchuan（海警船） | 11 | fanchuan（帆船） |
| 5 | junyongtuochuan（军用拖船） | 12 | minyongshiyanchuan（民用试验船） |
| 6 | buyuchuan（捕鱼船） | | |

## 关键结果

- **定稿模型**：chusai_finetune2（MuSGD 微调，无 mix 编译）+ ImageMake/DetPost 硬件加速
- **板上指标**：**0.619 / 0.805 / 0.722 @ 20.9ms**（P / R / F1）
- **数据链路**：forward 253ms → 20.9ms（ImageMake 硬件预处理 + DetPost 硬件后处理，约 12×）
- **位流**：custop2（AI_Mate v2.0，MMU + Norm/Softmax）璞致 DQ32 版，U-Boot `fpga loadb` 开机自动加载

## 本仓库未包含的文件

为控制仓库体积，以下大文件 / 二进制 / 厂商资料未上传（获取方式见对应文档）：

| 内容 | 原路径 | 获取方式 |
|---|---|---|
| 模型权重（.pt / .onnx / .raw） | `boatdet/*/` | Ultralytics 官方下载 / 微调产物 |
| 位流（.bit / .bin） | `data/bitstream/`、`vivado/bit/` | Vivado 工程构建产物 |
| SD 启动盘 / 整卡镜像 | `data/sd/`、`data/image/` | 见 `docs/01`、`docs/02` |
| FPGA / PRO CISE 工程 | `vivado/`、`procise/` | 项目工作区 |
| 厂商 IP 核（AI_Mate_IP、Xilinx IP、PS7） | `vivado/AI_Mate_IP/` 等 | 复旦微 / Xilinx 官方渠道 |
| 厂商参考资料（~100GB） | `docs/99-参考资料/` | 复旦微 / 璞致官方渠道 |
| 补丁包（JFM_Kits 等） | `patches/` | 复旦微官方 |
| 构建产物（runs / cache / sim / .dcp） | 各工程目录 | 工程内重新构建 |
| 推理结果图 | `runs/` | 板上重新运行生成 |

## 环境要求

- 硬件：璞致板 FMQL100TAI900（JFMQL100TAI900，PL DDR DQ32，UART0 = MIO46/47）
- 工具链：Vivado 2020.4（需复旦微 7z100ai 数据库补丁）、PRO CISE（FSBL/SDK）、IAR（FSBL 编译）
- 板上：Linux 5.4.52、icraft 3.31.x、numpy 1.23、opencv 4.6、Python 3.8
