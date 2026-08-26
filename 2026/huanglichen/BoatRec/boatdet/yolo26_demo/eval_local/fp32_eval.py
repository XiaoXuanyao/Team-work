#!/usr/bin/env python3
"""本机 FP32 验证（ultralytics + pycocotools，依赖项目 .conda，不用板子）。

对 1~N 个 .pt 权重在验证集上跑 ultralytics predict（end2end 模型默认走 one2one 分支 + NMS），
输出 COCO 格式 preds_fp32_<name>.json 并打印 mAP 指标（含每类）。

用法（项目根目录）：
  & .conda\python.exe boatdet\yolo26_demo\eval_local\fp32_eval.py ^
      --weights boatdet\modelconverter\input\chusai.pt boatdet\modelconverter\input\chusai_finetune.pt

参数：
  --weights  一个或多个 .pt（必需）
  --data     数据集 yaml（默认本目录 chusai_local.yaml）
  --split    val 划分（默认 val）
  --conf     后处理置信度（默认 0.001，与板上评估一致）
  --iou      后处理 NMS IoU（默认 0.45）
  --imgsz    推理尺寸（默认 640）
  --out      预测 json 输出目录（默认 yolo26_demo/io/output）
"""
import os, sys, json, time, argparse

import numpy as np
from ultralytics import YOLO
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_coco_metrics import build_gt, build_dets  # noqa: E402  复用指标构建逻辑（同目录）


def compute_metrics(preds_path, labels_dir):
    preds = json.load(open(preds_path, encoding="utf-8"))
    names = preds["names"]; nc = len(names)
    shapes = preds["shapes"]
    img_ids = {fn: i + 1 for i, fn in enumerate(sorted(shapes))}
    gt = build_gt(names, labels_dir, shapes)
    dets = build_dets(preds["results"], img_ids)
    coco = COCO(); coco.dataset = gt; coco.createIndex()
    dt = coco.loadRes(dets)
    ev = COCOeval(coco, dt, "bbox"); ev.evaluate(); ev.accumulate()
    p = np.asarray(ev.eval["precision"], float)
    mv = lambda x: float(x[x > -1].mean()) if x[x > -1].size else float("nan")
    per = [(mv(p[0, :, i, 0, -1]), mv(p[:, :, i, 0, -1])) for i in range(nc)]
    return (mv(p[:, :, :, 0, -1]), mv(p[0, :, :, 0, -1]), mv(p[5, :, :, 0, -1]), per, len(dets), names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", nargs="+", required=True, help="一个或多个 .pt")
    ap.add_argument("--data", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "chusai_local.yaml"))
    ap.add_argument("--split", default="val")
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--iou", type=float, default=0.45)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    import yaml as _yaml
    data = _yaml.safe_load(open(args.data, encoding="utf-8"))
    img_dir = os.path.join(data["path"], data[args.split])
    labels_dir = os.path.join(data["path"], "labels", args.split)
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png", ".jpeg")))
    print("VAL IMAGES:", len(files), "| labels:", labels_dir)

    out_dir = args.out or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "io", "output"))
    os.makedirs(out_dir, exist_ok=True)
    all_metrics = {}
    for w in args.weights:
        name = os.path.splitext(os.path.basename(w))[0]
        print("=" * 70)
        print("VALIDATING:", name)
        m = YOLO(w)
        print("  arch params: %.2fM" % (sum(p.numel() for p in m.model.parameters()) / 1e6))
        names = list(m.names.values()) if isinstance(m.names, dict) else list(m.names)
        results = []; shapes = {}
        t0 = time.time()
        for i in range(0, len(files), 32):
            paths = [os.path.join(img_dir, f) for f in files[i:i + 32]]
            res = m.predict(source=paths, imgsz=args.imgsz, conf=args.conf, iou=args.iou,
                            max_det=300, device="cpu", workers=0, verbose=False)
            for r in res:
                fn = os.path.basename(r.path)
                h, w = r.orig_shape
                shapes[fn] = [w, h]
                for b in r.boxes:
                    x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
                    results.append({"image": fn, "category_id": int(b.cls[0]),
                                    "score": float(b.conf[0]), "bbox": [x1, y1, x2 - x1, y2 - y1]})
            print("  [%d/%d] elapsed %ds" % (min(i + 32, len(files)), len(files), time.time() - t0), flush=True)
        out = os.path.join(out_dir, "preds_fp32_%s.json" % name)
        json.dump({"names": names, "results": results, "shapes": shapes}, open(out, "w"), ensure_ascii=False)
        ap5095, ap50, ap75, per, ndets, _ = compute_metrics(out, labels_dir)
        all_metrics[name] = (ap5095, ap50, ap75, per, ndets)
        print(">>> %s  FP32:  mAP50-95=%.4f  mAP50=%.4f  mAP75=%.4f  (dets=%d)" % (name, ap5095, ap50, ap75, ndets))
        for i, (a50, a) in enumerate(per):
            print("    %-24s AP50=%.4f  AP50-95=%.4f" % (names[i], a50, a))
        print()
    print("=" * 70)
    print("SUMMARY (FP32):")
    for name, (ap5095, ap50, ap75, _, ndets) in all_metrics.items():
        print("  %-24s mAP50-95=%.4f  mAP50=%.4f  mAP75=%.4f  dets=%d" % (name, ap5095, ap50, ap75, ndets))


if __name__ == "__main__":
    main()
