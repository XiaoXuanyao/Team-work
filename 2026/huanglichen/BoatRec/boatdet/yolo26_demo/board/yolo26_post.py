#!/usr/bin/env python3
"""yolo26 后处理公共模块（纯 numpy/cv2，可在本机与板上共用）。

供 run_yolo26.py / eval_yolo26.py / eval_detpost.py / probe_detpost.py / bench_imk.py 复用，
避免 decode/nms/letterbox/类别表在多处重复。

两类解码：
- decode()          : 软件后处理（无 DetPost），class/box 张量成对交替，float 输出
- decode_detpost()  : DetPost 硬件输出解码（int8 候选，每候选 80 字节，见 docs/04/03 §6）
"""
import numpy as np, cv2

# 13 类船舶（chusai 数据集，与训练 names 顺序一致）
NAMES_CHUSAI = ["hangmu","huweijian","bujijian","denglujian","haijingchuan",
                "junyongtuochuan","buyuchuan","tuochuan","huolunjizhuangxiangchuan",
                "youlue","youting","fanchuan","minyongshiyanchuan"]
NOC = len(NAMES_CHUSAI)   # 13
NOH = 3                   # 检测头数（stride 8/16/32）
ANCHOR_LENGTH = 80        # DetPost 每候选字节数


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def letterbox_center_pre(img, target, color=114):
    """letterbox 居中：等比缩放保持纵横比 + 上下/左右对称 pad。
    与 ultralytics LetterBox（center=True）一致。返回 (canvas, r, top, left)。"""
    h, w = img.shape[:2]
    r = min(target / h, target / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((target, target, 3), color, dtype=np.uint8)
    top = (target - nh) // 2
    left = (target - nw) // 2
    canvas[top:top + nh, left:left + nw] = resized
    return canvas, r, top, left


def letterbox_inverse(box, scale, top, left, ow, oh):
    """letterbox 居中逆映射：640 坐标减 pad 偏移后除以统一比例回原图（xywh 输入，xyxy 输出，截断到图内）。"""
    cx, cy, bw, bh = box
    x1 = max(0.0, min((cx - left - bw / 2) / scale, ow))
    y1 = max(0.0, min((cy - top - bh / 2) / scale, oh))
    x2 = max(0.0, min((cx - left + bw / 2) / scale, ow))
    y2 = max(0.0, min((cy - top + bh / 2) / scale, oh))
    return [x1, y1, x2, y2]


def decode(outputs, nclass, input_size=640, conf=0.001):
    """软件后处理解码：class/box 张量成对交替（3 尺度），stride 已还原。
    返回 (ids, scores, boxes_xywh_on_input)。"""
    ids, scores, boxes = [], [], []
    for si in range(0, len(outputs), 2):
        cls = outputs[si][0]       # [H,W,nclass]
        box = outputs[si + 1][0]   # [H,W,4]
        _H, _W = cls.shape[0], cls.shape[1]
        stride = input_size / _H
        c = cls.reshape(-1, nclass)
        best_idx = np.argmax(c, axis=1)
        prob = sigmoid(c[np.arange(len(c)), best_idx])
        mask = prob > conf
        ys, xs = np.nonzero(mask.reshape(_H, _W))
        for yy, xx in zip(ys, xs):
            ci = best_idx[yy * _W + xx]
            p = prob[yy * _W + xx]
            b = box[yy, xx]
            x1 = xx + 0.5 - b[0]
            y1 = yy + 0.5 - b[1]
            x2 = xx + 0.5 + b[2]
            y2 = yy + 0.5 + b[3]
            x = (x2 + x1) / 2 * stride
            y = (y2 + y1) / 2 * stride
            w = (x2 - x1) * stride
            h = (y2 - y1) * stride
            ids.append(int(ci))
            scores.append(float(p))
            boxes.append([x, y, w, h])
    return ids, scores, boxes


def decode_detpost(output_tensors, o_scale, strides, conf):
    """DetPost 硬件输出解码（YOLO26 anchor-free, box 无 DFL）。
    输出 3 张量（每尺度一个）[1,1,obj,80] int8，每候选 80 字节：
      [0:13] cls logits（pad 到 64） [64:68] box ltrb [74:75] loc_x [76:77] loc_y [78:79] anchor_index
    o_scale 6 值 = 3 尺度 × {cls, box}。返回 (ids, scores, boxes_xywh_on_640)。"""
    from icraft import xrt  # 仅板上环境需要
    ids, scores, boxes = [], [], []
    for head in range(NOH):
        arr = np.asarray(output_tensors[head].to(xrt.HostDevice.MemRegion())).flatten()
        obj_num = arr.size // ANCHOR_LENGTH
        cls_scale = o_scale[head * 2]
        box_scale = o_scale[head * 2 + 1]
        stride = strides[head]
        for obj in range(obj_num):
            base = obj * ANCHOR_LENGTH
            loc_x = (arr[base + ANCHOR_LENGTH - 5] << 8) + (arr[base + ANCHOR_LENGTH - 6] & 0xff)
            loc_y = (arr[base + ANCHOR_LENGTH - 3] << 8) + (arr[base + ANCHOR_LENGTH - 4] & 0xff)
            cls_logits = arr[base:base + NOC]
            prob = sigmoid(cls_logits * cls_scale)
            ci = int(np.argmax(prob)); p = float(prob[ci])
            if p <= conf:
                continue
            bx = arr[base + 64:base + 68].astype(np.float32) * box_scale
            x1 = loc_x + 0.5 - bx[0]; y1 = loc_y + 0.5 - bx[1]
            x2 = loc_x + 0.5 + bx[2]; y2 = loc_y + 0.5 + bx[3]
            x = (x1 + x2) / 2 * stride; y = (y1 + y2) / 2 * stride
            w = (x2 - x1) * stride; h = (y2 - y1) * stride
            ids.append(ci); scores.append(p); boxes.append([x, y, w, h])
    return ids, scores, boxes


def nms(boxes, scores, iou_thresh):
    """软件 NMS（cv2.dnn.NMSBoxes，输入 xywh）。返回保留索引。"""
    if not boxes:
        return []
    boxes_f = np.array(boxes, dtype=np.float32)
    keep = cv2.dnn.NMSBoxes(boxes_f.tolist(), np.array(scores, dtype=np.float32).tolist(),
                            0.0, iou_thresh)
    if keep is None:
        return []
    return np.array(keep).reshape(-1).tolist()
