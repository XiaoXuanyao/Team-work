#!/usr/bin/env python3
"""icraft 独立 adapt 阶段封装。

调用 `icraft-adapt.exe`（命令行参数方式）对 quantized 网络做自定义算子适配
（icraft 五阶段第 4 阶段），产出 `*_adapted.json` / `*_adapted.raw`。

默认**不启用** DetPost/ImageMake 自定义算子，以保持逐尺度原始 cls/box 特征输出，
与 run_yolo26.py 的 decode() 匹配。如需 DetPost 硬件后处理，用 --custom_config 指定
customop toml（如 `config/customop/yolov26.toml`）。

依赖: icraft CLI（Windows，默认 C:/Icraft/CLI，可 --icraft 指定）。
"""
import argparse
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(icraft_cli: str) -> str:
    if icraft_cli.lower().endswith(".exe"):
        return os.path.dirname(icraft_cli)
    return icraft_cli


def adapt_cmd(json_in: str, raw_in: str, jr_path: str, icraft_cli: str,
              custom_config: str = None, pass_on: str = None) -> list:
    exe = os.path.join(_root(icraft_cli), "bin", "icraft-adapt.exe")
    cmd = [
        exe,
        "--json", os.path.abspath(json_in),
        "--raw", os.path.abspath(raw_in),
        "--jr_path", os.path.abspath(jr_path),
        "--target", "BUYI",
    ]
    if custom_config:
        cmd += ["--custom_config", os.path.abspath(custom_config)]
    if pass_on:
        cmd += ["--pass_on", pass_on]
    return cmd


def run_adapt(json_in: str, raw_in: str, jr_path: str, icraft_cli: str,
              custom_config: str = None, pass_on: str = None):
    """调用 icraft-adapt，产出 *_adapted.json/.raw。返回 (json_out, raw_out)。"""
    if not os.path.exists(_root(icraft_cli)):
        raise RuntimeError(f"icraft CLI 不存在: {icraft_cli}")
    for p in (json_in, raw_in):
        if not os.path.exists(p):
            raise RuntimeError("输入缺失: " + p)

    os.makedirs(jr_path, exist_ok=True)
    cmd = adapt_cmd(json_in, raw_in, jr_path, icraft_cli, custom_config, pass_on)
    print(">>>", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=jr_path)
    if proc.returncode != 0:
        raise RuntimeError(f"icraft adapt 失败 (returncode={proc.returncode})")

    with open(json_in, encoding="utf-8") as f:
        net_name = json.load(f).get("name")
    json_out = os.path.join(jr_path, f"{net_name}_adapted.json")
    raw_out = os.path.join(jr_path, f"{net_name}_adapted.raw")
    return json_out, raw_out


def verify(json_path: str, raw_path: str) -> None:
    for p in (json_path, raw_path):
        if not os.path.exists(p):
            raise RuntimeError("adapt 未产出: " + p)
    print(f"adapt 产物: {os.path.basename(json_path)} ({os.path.getsize(json_path)} B), "
          f"{os.path.basename(raw_path)} ({os.path.getsize(raw_path)} B)")


def main():
    ap = argparse.ArgumentParser(description="icraft 独立 adapt 阶段")
    ap.add_argument("--json", required=True, help="quantized 模型 .json")
    ap.add_argument("--raw", required=True, help="quantized 模型 .raw")
    ap.add_argument("--jr_path", required=True, help="输出目录（imodel/BY/<bits>）")
    ap.add_argument("--icraft", default="C:/Icraft/CLI", help="icraft CLI 根目录")
    ap.add_argument("--custom_config", default=None, help="customop toml（DetPost/ImageMake，可选）")
    ap.add_argument("--pass_on", default=None, help="启用的 pass，如 customop.ImageMakePass")
    args = ap.parse_args()

    j, r = run_adapt(args.json, args.raw, args.jr_path, args.icraft, args.custom_config, args.pass_on)
    print("\nadapt 完成:\n ", j, "\n ", r)
    verify(j, r)


if __name__ == "__main__":
    main()
