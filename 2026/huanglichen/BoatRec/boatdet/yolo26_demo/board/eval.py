#!/usr/bin/env python3
"""板上批量评估（DetPost 或软件后处理自动选择）：--model 指定模型（imodel/<name>）。

用法（板上 board/ 目录下）：
  python3 eval.py --model chusai_finetune2              # 默认：新定稿，auto 选解码
  python3 eval.py --model chusai_detpost                # 旧定稿
  python3 eval.py --model chusai_imk --mode soft        # 强制软件后处理（无 DetPost 模型）
输出：../io/output/preds_<model>.json（{names, results, fwd_times}）。
本机指标：eval_local/eval_coco_metrics.py --preds ... --labels ... --shapes ...
"""
import os, sys, time, json, argparse
import numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # yolo26_demo/
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "board"))
from pyrtutils import *
from icraft import xrt, xir
from yolo26_post import (NAMES_CHUSAI, decode, decode_detpost, nms,
                         letterbox_center_pre, letterbox_inverse)


def main():
    ap = argparse.ArgumentParser(description="板上批量评估（DetPost/软件后处理）")
    ap.add_argument("--model", default="chusai_finetune2", help="imodel/<name>")
    ap.add_argument("--mode", choices=["auto", "detpost", "soft"], default="auto",
                    help="解码方式：auto=按模型 DetPost_on 自动选择（默认）")
    ap.add_argument("--imgdir", default="/root/boatdet/chusai_4yolo/images")
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--iou", type=float, default=0.45)
    args = ap.parse_args()

    jp, rp = getJrPath("imodel/" + args.model, "g", "buyi")
    network = loadNetwork(jp, rp)
    netinfo = Netinfo(network)
    print("MODEL:", jp)
    print("DETPOST_ON:", netinfo.DetPost_on, "IMAGE_MAKE:", netinfo.ImageMake_on)
    print("o_shape:", netinfo.o_shape)

    files = sorted(f for f in os.listdir(args.imgdir)
                   if f.lower().endswith((".jpg", ".png", ".jpeg")))
    print("VAL IMAGES:", len(files))

    device = openDevice("buyi", "127.0.0.1", True, False)
    sess = initSession("buyi", network, device, 4, True, False, False)
    sess.enableTimeProfile(True); sess.apply()

    use_detpost = (args.mode == "detpost") or (args.mode == "auto" and netinfo.DetPost_on)
    print("DECODE:", "DetPost" if use_detpost else "soft")
    if use_detpost:
        strides = [640 // c.h for c in netinfo.o_cubic]
        print("o_scale:", netinfo.o_scale, "strides:", strides)

    results = []; fwd_times = []
    total = len(files)
    for idx, fn in enumerate(files, 1):
        img = cv2.imread(os.path.join(args.imgdir, fn))
        if img is None:
            print("SKIP", fn); continue
        h, w = img.shape[:2]
        canvas, scale, top, left = letterbox_center_pre(img, 640)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = numpy2Tensor(rgb[np.newaxis, ...], network)
        dmaInit("buyi", netinfo.ImageMake_on, netinfo.i_shape[0][1:], tensor, device)
        t0 = time.perf_counter()
        outputs = sess.forward([tensor])
        fwd_ms = (time.perf_counter() - t0) * 1000
        fwd_times.append(fwd_ms)

        if use_detpost:
            ids, scores, boxes = decode_detpost(outputs, netinfo.o_scale, strides, args.conf)
        else:
            arrs = Tensor2Numpy(outputs)
            ids, scores, boxes = decode(arrs, len(NAMES_CHUSAI), 640, args.conf)
        keep = nms(boxes, scores, args.iou)
        for i in keep:
            x1, y1, x2, y2 = letterbox_inverse(boxes[i], scale, top, left, w, h)
            results.append({"image": fn, "category_id": int(ids[i]), "score": float(scores[i]),
                            "bbox": [x1, y1, x2 - x1, y2 - y1]})
        device.reset(1)
        if idx % 100 == 0 or idx == total:
            print("[%d/%d] done" % (idx, total), flush=True)

    fwd_times = np.array(fwd_times)
    print("DETECTIONS:", len(results))
    print("FWD mean=%.2f median=%.2f min=%.2f max=%.2f ms" % (
        fwd_times.mean(), np.median(fwd_times), fwd_times.min(), fwd_times.max()))
    out = os.path.join(ROOT, "io", "output", "preds_%s.json" % args.model)
    json.dump({"names": NAMES_CHUSAI, "results": results, "fwd_times": fwd_times.tolist()},
              open(out, "w"))
    print("SAVED", out)
    xrt.Device.Close(device)
    print("DONE")


if __name__ == "__main__":
    main()
