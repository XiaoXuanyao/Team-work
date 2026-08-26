#!/usr/bin/env python3
"""YOLO26 one2one 剪枝。

YOLO26 的 Detect 头在 end2end=True 时同时持有两套检测头权重：
  - one2many : cv2 / cv3                （训练分配用）
  - one2one  : one2one_cv2 / one2one_cv3 （推理端到端用）
本模块把模型剪枝为只保留 one2one 分支：替换 Detect.forward 使其逐尺度只跑
one2one head 并输出原始特征（NHWC），从而在导出阶段旁路掉 one2many 头。

依赖: ultralytics + torch（在装有 torch 的 conda 环境运行）。
"""
import argparse
import os

import torch
import torch.nn as nn

_HEAD_OUT_ORDER = "cls,box,cls,box,cls,box"  # stride 8/16/32 交替


def prune_to_one2one(model: nn.Module, nc: int) -> nn.Module:
    """对已加载的 ultralytics DetectionModel 做 one2one 剪枝。

    Args:
        model: ultralytics `YOLO(...).model`（DetectionModel）。
        nc:    类别数，须与模型检测头一致。

    Returns:
        同一模型实例，Detect.forward 已替换为只输出 one2one 逐尺度特征。
    """
    model.eval()

    det = model.model[-1]  # Detect head
    if not hasattr(det, "one2one_cv2") or not hasattr(det, "one2one_cv3"):
        raise RuntimeError(
            "模型检测头不含 one2one 分支（缺少 one2one_cv2/one2one_cv3）。"
            "请确认源模型是 YOLO26（end2end=True 训练权重）。"
        )
    if det.reg_max != 1:
        raise RuntimeError(f"yolo26 应为 reg_max=1（box 直接回归 4 通道），实际 {det.reg_max}")
    if det.nc != nc:
        raise ValueError(f"模型类别数 {det.nc} 与参数 --classes {nc} 不一致")

    nl = det.nl
    one2one_box = det.one2one_cv2  # ModuleList[stride]: [1,4,H,W]
    one2one_cls = det.one2one_cv3  # ModuleList[stride]: [1,nc,H,W]

    def e2e_forward(x):
        """Detect.forward 替换：逐尺度输出 one2one cls/box 原始特征（NHWC）。"""
        outs = []
        for i in range(nl):
            cls = one2one_cls[i](x[i]).permute(0, 2, 3, 1).contiguous()  # [1,H,W,nc]
            box = one2one_box[i](x[i]).permute(0, 2, 3, 1).contiguous()  # [1,H,W,4]
            outs += [cls, box]
        return outs

    # 用自定义 forward 替换 Detect.forward，保留 ultralytics 内部的 skip-connection 前向
    det.forward = e2e_forward
    return model


def load_pruned(weights: str, nc: int) -> nn.Module:
    """加载 YOLO26 权重并做 one2one 剪枝，返回剪枝后的 DetectionModel。"""
    from ultralytics import YOLO

    return prune_to_one2one(YOLO(weights).model, nc)


def main():
    ap = argparse.ArgumentParser(description="YOLO26 one2one 剪枝（去掉 one2many 头）")
    ap.add_argument("--weights", required=True, help="YOLO26 训练权重 .pt")
    ap.add_argument("--classes", type=int, required=True, help="类别数")
    ap.add_argument("--save", default=None, help="剪枝后另存 one2one 模型 .pt（可选）")
    args = ap.parse_args()

    model = load_pruned(args.weights, args.classes)
    nl = model.model[-1].nl
    print(f"剪枝完成: 保留 one2one 检测头, nl={nl}, 输出 {_HEAD_OUT_ORDER} (stride 8/16/32)")

    if args.save:
        os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
        torch.save(model.state_dict(), args.save)
        print("已另存:", args.save)


if __name__ == "__main__":
    main()
