#!/usr/bin/env python3
"""COCO 指标计算（离线，本机）。
输入：板上 eval_yolo26.py 产出的 preds.json（含 results + names）、验证集 YOLO labels 目录、
      图片宽高清单 json（img_shapes.json）。输出 P/R/mAP50/mAP50-95 + 每类 AP。

用法：
  python3 eval_coco_metrics.py --preds preds.json --labels <labels_dir> --shapes img_shapes.json
"""
import os, sys, json, argparse
import numpy as np


def build_gt(preds_names, labels_dir, shapes):
    names = preds_names
    nc = len(names)
    img_ids = {fn: i + 1 for i, fn in enumerate(sorted(shapes.keys()))}
    annotations = []
    ann_id = 1
    for fn in sorted(shapes.keys()):
        w, h = shapes[fn]
        lbl = os.path.join(labels_dir, fn.rsplit(".", 1)[0] + ".txt")
        if not os.path.exists(lbl):
            continue
        for line in open(lbl):
            line = line.strip()
            if not line:
                continue
            p = line.split()
            cls = int(p[0]); cx, cy, bw, bh = [float(x) for x in p[1:5]]
            x1, y1 = (cx - bw / 2) * w, (cy - bh / 2) * h
            bw_px, bh_px = bw * w, bh * h
            annotations.append({
                "id": ann_id, "image_id": img_ids[fn], "category_id": cls + 1,
                "bbox": [x1, y1, bw_px, bh_px], "area": bw_px * bh_px,
                "iscrowd": 0, "segmentation": [],
            })
            ann_id += 1
    gt = {
        "images": [{"id": img_ids[f], "file_name": f, "width": shapes[f][0], "height": shapes[f][1]} for f in shapes],
        "annotations": annotations,
        "categories": [{"id": i + 1, "name": names[i]} for i in range(nc)],
    }
    return gt


def build_dets(preds_results, img_ids):
    dets = []
    for r in preds_results:
        x, y, bw, bh = r["bbox"]
        dets.append({"image_id": img_ids[r["image"]], "category_id": r["category_id"] + 1,
                     "bbox": [x, y, bw, bh], "score": float(r["score"])})
    return dets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True, help="preds.json")
    ap.add_argument("--labels", required=True, help="YOLO labels 目录（若含 train/val 子目录则自动取 val）")
    ap.add_argument("--shapes", required=True, help="img_shapes.json {name:[w,h]}")
    ap.add_argument("--split", default="val", help="labels 为数据集根目录时的划分（默认 val）")
    args = ap.parse_args()

    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    preds = json.load(open(args.preds, encoding="utf-8"))
    shapes = json.load(open(args.shapes, encoding="utf-8"))
    names = preds["names"]
    nc = len(names)

    # GT labels 目录智能识别：根目录下含 train/val 子目录（YOLO 数据集布局）时自动取指定划分
    labels_dir = args.labels
    sub = os.path.join(labels_dir, args.split)
    if os.path.isdir(sub):
        labels_dir = sub
        print("labels dir ->", labels_dir)

    img_ids = {fn: i + 1 for i, fn in enumerate(sorted(shapes.keys()))}
    gt = build_gt(names, labels_dir, shapes)
    dets = build_dets(preds["results"], img_ids)

    coco = COCO(); coco.dataset = gt; coco.createIndex()
    coco_dt = coco.loadRes(dets)
    ev = COCOeval(coco, coco_dt, "bbox")
    ev.evaluate(); ev.accumulate()
    p = ev.eval["precision"]

    def mv(x):
        x = np.asarray(x, float); x = x[x > -1]
        return float(x.mean()) if x.size else float("nan")

    ap5095 = mv(p[:, :, :, 0, -1])
    ap50 = mv(p[0, :, :, 0, -1])
    ap75 = mv(p[5, :, :, 0, -1])
    print("mAP@0.5:0.95 = %.3f" % ap5095)
    print("mAP@0.5     = %.3f" % ap50)
    print("mAP@0.75    = %.3f" % ap75)
    print("\n===== per-class =====")
    for i in range(nc):
        print("  %-24s AP50=%.3f  AP50-95=%.3f" % (
            names[i], mv(p[0, :, i, 0, -1]), mv(p[:, :, i, 0, -1])))


if __name__ == "__main__":
    main()
