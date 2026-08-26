#!/usr/bin/env python3
"""YOLO26s chusai 微调 —— 推荐配置（MuSGD + freeze=10）

关键改动 vs 原脚本：
1. optimizer="MuSGD"（显式）：默认 'auto' 会忽略 lr0/momentum，且本场景
   iterations = 100 × 3593/64 ≈ 5610 < 10000 → auto 实际选 AdamW(lr≈0.0006)。
   MuSGD（ultralytics 8.4.x 引入）用 Muon 正交化更新 2D/4D 权重，并**自动给
   检测头（cv3 / one2one_cv3）3× lr**，正适配 freeze=10 只训 neck/head。
2. lr0=0.01, momentum=0.9：MuSGD 标准参数（auto 在大迭代时也是这套）。
3. cos_lr=True：余弦退火，微调收敛更稳（默认 False=线性衰减）。
4. 其余参数与原来一致。

前置要求：
- 训练机 ultralytics 版本 >= 8.4（MuSGD 在 ultralytics/optim/muon.py，8.4.x 才有；
  旧版本会报 NotImplementedError）。本机 .conda 为 8.4.118。
- data.yaml 的 train/val 指向训练机实际路径（当前 3593/891 划分）。

AB 实验提示：想对比学习率档位时，把 MuSGD 换 SGD 并分别试 lr0=0.005 / 0.002
（同 seed，各 100 epoch），对比 FP32 val 的 mAP 即可。
"""
from ultralytics import YOLO

model = YOLO("yolo26s.pt")

model.train(
    data="/data/datasets/chusai_4yolo/data.yaml",
    epochs=100,
    imgsz=640,
    batch=64,
    device=0,
    workers=8,
    cache=True,
    project="",
    name="yolo26s_chusai2",
    exist_ok=True,
    seed=42,
    end2end=True,
    freeze=10,
    amp=False,
    # ---- 微调优化器/学习率（改动点）----
    optimizer="MuSGD",   # 显式指定；不要用 auto（会忽略下方 lr 设置）
    lr0=0.01,            # MuSGD 标准 lr；检测头自动 3×lr（无需手动调）
    momentum=0.9,
    lrf=0.01,            # 保持默认（最终 lr = lr0 × lrf）
    cos_lr=True,         # 余弦退火
    warmup_epochs=3.0,   # 默认 3 epoch；随机初始化的 head 靠 warmup 兜底
)
