#!/usr/bin/env python3
"""YOLO26 -> one2one ONNX 导出。

把训练得到的 YOLO26 权重（Detect 头同时含 one2many + one2one 双分支）裁剪为
只保留 one2one 检测头的端到端单头模型，并导出为 icraft 可编译的 ONNX。

one2one 剪枝在独立模块 `prune.py`（`prune.load_pruned`），本模块负责 torch.onnx 导出。

ONNX 源模型输入为 **NCHW** `[1,3,640,640]`（模型原生布局）；icraft 部署输入布局
`[1,640,640,3] NHWC` 由 toml 的 `inputs_layout` 声明，icraft 会在图上插入布局转换，
使部署模型 INPUT 为 NHWC（与复旦微 yolo26_0715_BY.json 一致）。

输出契约（对齐复旦微 yolo26_0715_BY.json）：
  - 输出 : 6 个张量，3 尺度 × {cls, box} 交替，NHWC fp32
       cls[1,80,80,nc], box[1,80,80,4],   # stride 8  (P3)
       cls[1,40,40,nc], box[1,40,40,4],   # stride 16 (P4)
       cls[1,20,20,nc], box[1,20,20,4]    # stride 32 (P5)
   其中 cls 为 sigmoid 前的 logits，box 为 ltrb 偏移（未解码），与 run_yolo26.py 的
   decode() 完全匹配。

依赖: ultralytics + torch + onnx（在装有 torch 的 conda 环境运行）。
"""
import argparse
import os
import sys

import torch
import torch.nn as nn
from src.prune import load_pruned


def build_export_model(weights: str, nc: int, imgsz: int = 640) -> nn.Module:
    """one2one 剪枝，返回输入为 NCHW [1,3,H,W] 的 DetectionModel（可直接导出）。"""
    return load_pruned(weights, nc)


def export(
    weights: str,
    out: str,
    nc: int,
    imgsz: int = 640,
    opset: int = 17,
) -> str:
    """导出 one2one ONNX，返回输出路径。"""
    model = build_export_model(weights, nc, imgsz)
    model.eval()

    dummy = torch.zeros(1, 3, imgsz, imgsz)  # NCHW fp32
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    kw = dict(
        input_names=["input"],
        output_names=[f"out_{i}" for i in range(6)],
        opset_version=opset,
        dynamic_axes=None,
    )
    exported = False
    if opset <= 17:
        # 传统（TorchScript）导出可稳定产出 opset<=17，避免新版 exporter 的版本转换失败
        try:
            torch.onnx.export(model, dummy, out, dynamo=False, **kw)
            exported = True
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] 传统 exporter (opset{opset}) 失败: {e}\n     改用新 exporter。")
    if not exported:
        torch.onnx.export(model, dummy, out, **kw)
    return out


def inspect(onnx_path: str):
    import onnx
    m = onnx.load(onnx_path)
    onnx.checker.check_model(m)
    print("ONNX 校验通过:", os.path.basename(onnx_path))
    print("输入:")
    for i in m.graph.input:
        print("  ", i.name, [d.dim_value for d in i.type.tensor_type.shape.dim])
    print("输出 (6 = 3尺度 × cls/box):")
    for i, o in enumerate(m.graph.output):
        shape = [d.dim_value for d in o.type.tensor_type.shape.dim]
        print(f"   [{i}] {o.name} {shape}  {'cls' if i % 2 == 0 else 'box'}")


def main():
    ap = argparse.ArgumentParser(description="YOLO26 -> one2one ONNX 导出")
    ap.add_argument("--weights", required=True, help="YOLO26 训练权重 .pt")
    ap.add_argument("--out", default="yolo26_one2one.onnx", help="输出 ONNX 路径")
    ap.add_argument("--classes", type=int, default=13, help="类别数")
    ap.add_argument("--imgsz", type=int, default=640, help="输入尺寸")
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--inspect", action="store_true", help="导出后打印 ONNX 输入/输出")
    args = ap.parse_args()

    export(args.weights, args.out, args.classes, args.imgsz, args.opset)
    print("导出完成:", args.out)
    if args.inspect:
        inspect(args.out)


if __name__ == "__main__":
    main()
