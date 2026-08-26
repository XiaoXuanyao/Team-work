# 03 yolo26_demo_cpp —— yolo26n C++ 工程

> 位置：`boatdet/yolo26_demo_cpp/`

## 用途

YOLO26n 的 C++ 板载推理工程（CMake 构建），含完整后处理（NMS）与双后端支持（BY/ZG）。`WL/` 子目录为万联版本（另含 yolov8n 推理）。

## 结构

```
yolo26_demo_cpp/
├── CMakeLists.txt          # 构建（TARGET yolo26，LINUX_AARCH64 选项）
├── CMakePresets.json
├── patch_model.py          # 模型补丁脚本（BY 配置修正）
├── cfg/
│   ├── yolo26_demo.yaml    # 板载配置（run_backend=buyi、mmuMode=true）
│   └── yolov26_ZG_int8_demo.yaml   # ZG int8 配置
├── imodel/                 # 模型 yolo26_0715_BY.json/.raw
├── io/input/               # 测试图片
├── io/output/              # 输出（结果图/文本）
├── names/                  # 类别名
├── modelzoo_utils/         # 运行时库（C++ 头文件 + pyrtutils）
├── src/                    # 主源码
│   ├── yolo26.cpp          # 推理主程序
│   ├── postprocess_yolo26.hpp   # 后处理
│   └── yolo26_utils.hpp
├── WL/                     # 万联版本（yolo26n.cpp / yolov8n.cpp + build_arm）
├── build_arm/ build_win/   # 编译产物
└── backup/                 # 备份
```

## 构建

```bash
cd boatdet/yolo26_demo_cpp
cmake -B build_arm -DLINUX_AARCH64=ON
cmake --build build_arm -j
```

## 关键配置（cfg/yolo26_demo.yaml）

| 项 | 值 | 说明 |
|---|---|---|
| `imodel.run_backend` | `buyi` | NPU 后端 |
| `imodel.mmuMode` | `true` | MMU 使能 |
| `imodel.ip` | `169.254.135.10` | 设备地址 |
| `param.number_of_class` | `13` | 类别数 |
| `param.number_of_head` | `3` | 检测头数 |

## 说明

- `patch_model.py`：对 BY 模型配置做修正（json 内字段调整），模型改动后需重跑
- `WL/` 为万联（WL）实现，含 yolov8n/yolo26n 双模型，`build_arm` 已有编译产物
- 后处理在 `src/postprocess_yolo26.hpp`（解包多检测头 + NMS）
