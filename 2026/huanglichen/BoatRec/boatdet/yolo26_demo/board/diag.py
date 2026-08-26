#!/usr/bin/env python3
"""板上诊断工具：--task 选择功能。

用法（板上 board/ 目录下）：
  python3 diag.py --task probe --model chusai_finetune2   # 探测 DetPost 运行时输出结构
  python3 diag.py --task bench --model chusai_imk --nimg 6  # ImageMake 基准（letterbox 居中，画框保存）
"""
import os, sys, time, argparse
import numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # yolo26_demo/
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "board"))
from pyrtutils import *
from icraft import xrt, xir
from yolo26_post import NAMES_CHUSAI, decode, nms, letterbox_center_pre, letterbox_inverse


def task_probe(args):
    """输出结构探测：o_shape/o_scale/strides + 3 head 输出 shape/dtype/数值。排查 DetPost 输出异常用。"""
    jp, rp = getJrPath("imodel/" + args.model, "g", "buyi")
    network = loadNetwork(jp, rp)
    netinfo = Netinfo(network)
    print("o_shape:", netinfo.o_shape)
    print("o_scale:", netinfo.o_scale)
    print("strides:", [640 // c.h for c in netinfo.o_cubic])

    files = sorted(f for f in os.listdir(args.imgdir)
                   if f.lower().endswith((".jpg", ".png", ".jpeg")))
    fn = files[0]
    img = cv2.imread(os.path.join(args.imgdir, fn))
    canvas, _, _, _ = letterbox_center_pre(img, 640)
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    tensor = numpy2Tensor(rgb[np.newaxis, ...], network)

    device = openDevice("buyi", "127.0.0.1", True, False)
    sess = initSession("buyi", network, device, 4, True, False, False)
    sess.enableTimeProfile(True); sess.apply()

    dmaInit("buyi", netinfo.ImageMake_on, netinfo.i_shape[0][1:], tensor, device)
    outputs = sess.forward([tensor])
    print("\n=== OUTPUTS (%s) ===" % fn)
    for i, out in enumerate(outputs):
        arr = np.asarray(out.to(xrt.HostDevice.MemRegion()))
        print("head", i, "dtype", arr.dtype, "shape", arr.shape, "flat bytes:", arr.size * arr.itemsize)
        if arr.size:
            flat = arr.flatten()
            print("  min", arr.min(), "max", arr.max())
            print("  first %d vals:" % args.nvals, flat[:args.nvals].tolist())
    device.reset(1)
    xrt.Device.Close(device)
    print("DONE")


def task_bench(args):
    """ImageMake 基准：letterbox 居中 640，每帧 dmaInit+forward+reset，软解码+画框保存。"""
    jp, rp = getJrPath("imodel/" + args.model, "g", "buyi")
    network = loadNetwork(jp, rp)
    netinfo = Netinfo(network)
    print("ImageMake_on:", netinfo.ImageMake_on, "input:", netinfo.i_shape)

    imgs = sorted(f for f in os.listdir(args.imgdir)
                  if f.lower().endswith((".jpg", ".png", ".jpeg")))[:args.nimg]
    device = openDevice("buyi", "127.0.0.1", True, False)
    sess = initSession("buyi", network, device, 4, True, False, False)
    sess.enableTimeProfile(True); sess.apply()

    fwd_times = []
    for k, name in enumerate(imgs):
        img = cv2.imread(os.path.join(args.imgdir, name))
        h, w = img.shape[:2]
        canvas, r, top, left = letterbox_center_pre(img, 640)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = numpy2Tensor(rgb[np.newaxis, ...], network)
        dmaInit("buyi", netinfo.ImageMake_on, netinfo.i_shape[0][1:], tensor, device)
        t0 = time.perf_counter()
        outputs = sess.forward([tensor])
        fwd_ms = (time.perf_counter() - t0) * 1000
        fwd_times.append(fwd_ms)
        arrs = Tensor2Numpy(outputs)
        ids, scores, boxes = decode(arrs, len(NAMES_CHUSAI), 640, 0.001)
        keep = nms(boxes, scores, 0.45)
        dets = []
        for i in keep:
            x1, y1, x2, y2 = letterbox_inverse(boxes[i], r, top, left, w, h)
            dets.append((NAMES_CHUSAI[ids[i]], round(scores[i], 3), [int(x1), int(y1), int(x2), int(y2)]))
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(img, "%s %.2f" % (NAMES_CHUSAI[ids[i]], scores[i]),
                        (int(x1), max(0, int(y1) - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        print("[%d] %s fwd=%.1fms dets=%d %s" % (k, name, fwd_ms, len(dets), dets[:3]))
        cv2.imwrite(os.path.join(ROOT, "io", "output", "visual", "imbk640_%d.jpg" % k), img)
        device.reset(1)

    fwd_times = np.array(fwd_times)
    print("=== ImageMake forward (letterbox center 640) === mean=%.2f min=%.2f max=%.2f ms"
          % (fwd_times.mean(), fwd_times.min(), fwd_times.max()))
    xrt.Device.Close(device)
    print("DONE")


def main():
    ap = argparse.ArgumentParser(description="板上诊断工具")
    ap.add_argument("--task", choices=["probe", "bench"], default="probe")
    ap.add_argument("--model", default=None, help="imodel/<name>（默认：probe→chusai_finetune2, bench→chusai_imk）")
    ap.add_argument("--imgdir", default="/root/boatdet/chusai_4yolo/images")
    ap.add_argument("--nimg", type=int, default=6, help="bench 图片数")
    ap.add_argument("--nvals", type=int, default=128, help="probe dump 前 N 个数值")
    args = ap.parse_args()

    if args.model is None:
        args.model = "chusai_finetune2" if args.task == "probe" else "chusai_imk"
    print("TASK:", args.task, "MODEL:", args.model)

    if args.task == "probe":
        task_probe(args)
    else:
        task_bench(args)


if __name__ == "__main__":
    main()
