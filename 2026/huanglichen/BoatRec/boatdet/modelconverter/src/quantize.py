#!/usr/bin/env python3
"""icraft 独立 quantize 阶段封装。

调用 `icraft-quantize.exe`（命令行参数方式）用校准集对 optimized 网络做量化
（icraft 五阶段第 3 阶段），产出 `*_quantized.json` / `*_quantized.raw`。

依赖: icraft CLI（Windows，默认 C:/Icraft/CLI）+ qtset 量化校准集。
"""
import argparse
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_QTSET = os.path.normpath(
    os.path.join(HERE, "..", "..", "example", "yolov10_icraft", "2_compile", "qtset")
)


def _root(icraft_cli: str) -> str:
    if icraft_cli.lower().endswith(".exe"):
        return os.path.dirname(icraft_cli)
    return icraft_cli


def _qtset_forward(qtset: str) -> tuple:
    """解析校准集：优先 qtset/images + qtset/images.txt，回退 qtset/coco + qtset/coco.txt。"""
    for sub, lst in (("images", "images.txt"), ("coco", "coco.txt")):
        d, l = os.path.join(qtset, sub), os.path.join(qtset, lst)
        if os.path.isdir(d) and os.path.isfile(l):
            return d, l
    return None, None


def quantize_cmd(
    json_in: str,
    raw_in: str,
    jr_path: str,
    icraft_cli: str,
    forward_dir: str,
    forward_list: str,
    bits: int = 8,
    saturation: str = "kld",
    per: str = "channel",
    forward_mode: str = "image",
    mix_precision: str = None,
) -> list:
    exe = os.path.join(_root(icraft_cli), "bin", "icraft-quantize.exe")
    cmd = [
        exe,
        "--json", os.path.abspath(json_in),
        "--raw", os.path.abspath(raw_in),
        "--jr_path", os.path.abspath(jr_path),
        "--target", "buyi",
        "--forward_mode", forward_mode,
        "--forward_dir", os.path.abspath(forward_dir),
        "--forward_list", os.path.abspath(forward_list),
        "--saturation", saturation,
        "--per", per,
        "--bits", str(bits),
    ]
    if mix_precision:
        cmd += ["--mix_precision", mix_precision]
    return cmd


def run_quantize(
    json_in: str,
    raw_in: str,
    jr_path: str,
    icraft_cli: str,
    qtset: str = None,
    bits: int = 8,
    saturation: str = "kld",
    per: str = "channel",
    mix_precision: str = None,
):
    """调用 icraft-quantize，产出 *_quantized.json/.raw。返回 (json_out, raw_out)。"""
    if not os.path.exists(_root(icraft_cli)):
        raise RuntimeError(f"icraft CLI 不存在: {icraft_cli}")
    for p in (json_in, raw_in):
        if not os.path.exists(p):
            raise RuntimeError("输入缺失: " + p)

    qtset = qtset or DEFAULT_QTSET
    forward_dir, forward_list = _qtset_forward(qtset)
    if not forward_dir or not forward_list:
        raise RuntimeError(
            f"校准集缺失（需含 images/images.txt 或 coco/coco.txt），请用 --qtset 指定: {qtset}")

    os.makedirs(jr_path, exist_ok=True)
    cmd = quantize_cmd(json_in, raw_in, jr_path, icraft_cli,
                       forward_dir, forward_list, bits, saturation, per,
                       mix_precision=mix_precision)
    print(">>>", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=jr_path)
    if proc.returncode != 0:
        raise RuntimeError(f"icraft quantize 失败 (returncode={proc.returncode})")

    with open(json_in, encoding="utf-8") as f:
        net_name = json.load(f).get("name")
    json_out = os.path.join(jr_path, f"{net_name}_quantized.json")
    raw_out = os.path.join(jr_path, f"{net_name}_quantized.raw")
    return json_out, raw_out


def verify(json_path: str, raw_path: str) -> None:
    for p in (json_path, raw_path):
        if not os.path.exists(p):
            raise RuntimeError("quantize 未产出: " + p)
    print(f"quantize 产物: {os.path.basename(json_path)} ({os.path.getsize(json_path)} B), "
          f"{os.path.basename(raw_path)} ({os.path.getsize(raw_path)} B)")


def main():
    ap = argparse.ArgumentParser(description="icraft 独立 quantize 阶段")
    ap.add_argument("--json", required=True, help="optimized 模型 .json")
    ap.add_argument("--raw", required=True, help="optimized 模型 .raw")
    ap.add_argument("--jr_path", required=True, help="输出目录（imodel/BY/<bits>）")
    ap.add_argument("--icraft", default="C:/Icraft/CLI", help="icraft CLI 根目录")
    ap.add_argument("--qtset", default=DEFAULT_QTSET, help="量化校准集目录")
    ap.add_argument("--bits", type=int, default=8)
    ap.add_argument("--saturation", default="kld")
    ap.add_argument("--per", default="channel")
    ap.add_argument("--mix_precision", default=None, help="混合精度: auto 或 <xx.csv>（关键算子用更高位宽）")
    args = ap.parse_args()

    j, r = run_quantize(args.json, args.raw, args.jr_path, args.icraft,
                        args.qtset, args.bits, args.saturation, args.per,
                        args.mix_precision)
    print("\nquantize 完成:\n ", j, "\n ", r)
    verify(j, r)


if __name__ == "__main__":
    main()
