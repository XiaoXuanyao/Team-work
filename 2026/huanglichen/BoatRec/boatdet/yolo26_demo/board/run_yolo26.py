#!/usr/bin/env python3
"""YOLO26 板载 NPU 推理（buyi backend）—— forward + 后处理 + 可视化检测框（board/ 子目录版）。

用法（板上 board/ 目录下）：python3 run_yolo26.py [cfg 相对 yolo26_demo 根路径]
默认 cfg：../cfg/yolo26_board.yaml（imodel/yolo26m 等模型，见 cfg）
"""
import os, sys, yaml, numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # yolo26_demo/
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "board"))
from pyrtutils import *
from icraft import xrt, xir
from yolo26_post import decode, nms, letterbox_center_pre, letterbox_inverse


def draw(img, dets, names, out_path):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255),
              (255, 255, 0), (0, 165, 255), (255, 0, 128), (0, 128, 255), (128, 0, 255),
              (255, 128, 0), (128, 255, 0), (0, 255, 128)]
    canvas = img.copy()
    for ci, p, (x1, y1, x2, y2) in dets:
        color = colors[ci % len(colors)]
        cv2.rectangle(canvas, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        label = "%s %.2f" % (names[ci], p)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(canvas, (int(x1), int(y1) - th - 6), (int(x1) + tw + 4, int(y1)), color, -1)
        cv2.putText(canvas, label, (int(x1) + 2, int(y1) - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(out_path, canvas)
    return len(dets)


def main(cfg_path):
    cfg = yaml.safe_load(open(os.path.join(ROOT, cfg_path)))
    im = cfg["imodel"]
    ds = cfg["dataset"]
    conf = cfg["param"].get("conf", 0.25)
    iou = cfg["param"].get("iou_thresh", 0.45)

    jp, rp = getJrPath(im["dir"], im["stage"], im["run_backend"])
    print("MODEL:", jp)
    network = loadNetwork(jp, rp)
    netinfo = Netinfo(network)
    print("INPUT_SHAPE :", netinfo.i_shape)
    print("OUTPUT_SHAPE:", netinfo.o_shape)
    print("DETPOST_ON  :", netinfo.DetPost_on, " IMAGE_MAKE:", netinfo.ImageMake_on, " MMU:", netinfo.mmu)

    device = openDevice(im["run_backend"], im["ip"],
                        im["mmuMode"], im["cudamode"])
    print("DEVICE OK:", device)
    session = initSession(im["run_backend"], network, device, im["ocm_option"],
                          im["mmuMode"], im["speedmode"], im["compressFtmp"])
    session.enableTimeProfile(True)
    session.apply()
    print("SESSION APPLY DONE")

    names = [l.strip() for l in open(os.path.join(ROOT, ds["names"])) if l.strip()]
    print("CLASSES(%d):" % len(names), names)
    nclass = len(names)

    target = (netinfo.i_cubic[0].h, netinfo.i_cubic[0].w) if netinfo.i_cubic else (640, 640)
    print("INPUT SIZE:", target)

    res_dir = os.path.join(ROOT, ds.get("res", "io/output"), "visual")
    os.makedirs(res_dir, exist_ok=True)

    for fn in sorted(os.listdir(os.path.join(ROOT, ds["dir"]))):
        if not fn.lower().endswith((".jpg", ".png", ".jpeg", ".bmp")):
            continue
        img = cv2.imread(os.path.join(ROOT, ds["dir"], fn))
        if img is None:
            print("SKIP", fn); continue
        h, w = img.shape[:2]
        canvas, scale, top, left = letterbox_center_pre(img, target[0])
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = numpy2Tensor(rgb[np.newaxis, ...], network)

        outputs = session.forward([tensor])
        print("=== %s ===" % fn)
        arrs = Tensor2Numpy(outputs)
        ids, scores, boxes = decode(arrs, nclass, target[0], conf)
        keep = nms(boxes, scores, iou)
        dets = [(ids[i], scores[i], letterbox_inverse(boxes[i], scale, top, left, w, h)) for i in keep]
        dets.sort(key=lambda d: -d[1])

        for i, a in enumerate(arrs):
            print("  numpy[%d] shape=%s min=%.3f max=%.3f" % (i, a.shape, a.min(), a.max()))
        print("  DETECTIONS(%d):" % len(dets))
        for ci, p, (x1, y1, x2, y2) in dets:
            print("    %-12s %.3f  box=(%.0f,%.0f)-(%.0f,%.0f)" % (names[ci], p, x1, y1, x2, y2))

        if dets:
            out_path = os.path.join(res_dir, "res_" + fn)
            n = draw(img, dets, names, out_path)
            print("  saved ->", out_path, "(%d box)" % n)

        if im["run_backend"] != "host":
            device.reset(1)

    xrt.Device.Close(device)
    print("DONE")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cfg/yolo26_board.yaml")
