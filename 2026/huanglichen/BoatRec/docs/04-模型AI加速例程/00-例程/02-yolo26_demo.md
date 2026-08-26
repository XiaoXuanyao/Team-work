# 02 yolo26_demo —— Python 板载推理 demo

> 位置：`boatdet/yolo26_demo/`（板上 `/root/boatdet/yolo26_demo/`）

## 用途

YOLO26 板载 NPU 推理验证：加载 imodel（`.json` 指令 + `.raw` 权重），用 buyi backend 做 `session.forward`，打印输出结构/数值，先验证 **forward + 输出结构**（不追求完整可视化）。

## 结构

```
yolo26_demo/
├── run_yolo26.py            # 主脚本
├── cfg/yolo26_board.yaml    # 板载配置（imodel/dataset/param）
├── imodel/
│   ├── yolo26_0715_BY.json  # 模型指令（1.6MB）
│   └── yolo26_0715_BY.raw   # 模型权重（25MB）
├── io/input/                # 测试图片（000000000139.jpg、bc_106.jpg、bus_640x640.png...）
├── io/output/               # 输出目录
├── names/yolo26.names       # 类别名（13 类）
└── pyrtutils/               # icraft 运行时库（icraft_utils.py、Netinfo.py、modelzoo_utils.py 等）
```

## 运行

```bash
cd /root/boatdet/yolo26_demo
python3 run_yolo26.py cfg/yolo26_board.yaml
```

### 关键配置（cfg/yolo26_board.yaml）

| 项 | 值 | 说明 |
|---|---|---|
| `imodel.run_backend` | `buyi` | NPU 后端（可选 `host` 纯模拟） |
| `imodel.mmuMode` | `false` | MMU 模式 |
| `imodel.speedmode` | `true` | 速度模式 |
| `imodel.compressFtmp` | `true` | ftmp 压缩 |
| `dataset.names` | `names/yolo26.names` | 13 类 |
| `param.conf` | `0.25` | 置信度阈值 |

## 脚本流程（run_yolo26.py）

1. 读 cfg → `getJrPath` 定位模型指令/权重
2. `loadNetwork` → `Netinfo` 打印输入/输出形状
3. `openDevice('buyi', 'axi://ql100aiu?npu=0x40000000&dma=0x80000000', ...)`
4. `initSession` → `session.apply()` → `enableTimeProfile`
5. 对 `io/input` 每张图：resize 到 640×640 → `numpy2Tensor` → `session.forward`
6. 打印每路输出 shape/dtype + numpy 数值范围；`device.reset(1)` 复位

## 依赖

- icraft 3.31.x + pyrtutils（`sys.path.insert(0, DIR)` 用本目录内 pyrtutils）
- numpy / opencv / yaml
- 需 PL DDR 就绪（NPU 数据经 PLDDR，见 `03-位流适配`）

## 验证点

- 输出每路 `out[i]` shape/dtype 打印
- `numpy[i]` min/max 合理（非 0）
- `enableTimeProfile` 可看推理耗时
