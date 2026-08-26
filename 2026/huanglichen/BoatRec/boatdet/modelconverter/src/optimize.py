#!/usr/bin/env python3
"""icraft 独立 optimize 阶段封装。

调用 `icraft-optimize.exe`（命令行参数方式）对 parsed 网络做图结构优化
（icraft 五阶段第 2 阶段），产出 `*_optimized.json` / `*_optimized.raw`。

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


def optimize_cmd(json_in: str, raw_in: str, jr_path: str, icraft_cli: str) -> list:
    exe = os.path.join(_root(icraft_cli), "bin", "icraft-optimize.exe")
    return [
        exe,
        "--json", os.path.abspath(json_in),
        "--raw", os.path.abspath(raw_in),
        "--jr_path", os.path.abspath(jr_path),
        "--target", "BUYI",
    ]


def run_optimize(json_in: str, raw_in: str, jr_path: str, icraft_cli: str):
    """调用 icraft-optimize，产出 *_optimized.json/.raw。返回 (json_out, raw_out)。"""
    if not os.path.exists(_root(icraft_cli)):
        raise RuntimeError(f"icraft CLI 不存在: {icraft_cli}")
    for p in (json_in, raw_in):
        if not os.path.exists(p):
            raise RuntimeError("输入缺失: " + p)

    os.makedirs(jr_path, exist_ok=True)
    cmd = optimize_cmd(json_in, raw_in, jr_path, icraft_cli)
    print(">>>", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=jr_path)
    if proc.returncode != 0:
        raise RuntimeError(f"icraft optimize 失败 (returncode={proc.returncode})")

    with open(json_in, encoding="utf-8") as f:
        net_name = json.load(f).get("name")
    json_out = os.path.join(jr_path, f"{net_name}_optimized.json")
    raw_out = os.path.join(jr_path, f"{net_name}_optimized.raw")
    return json_out, raw_out


def verify(json_path: str, raw_path: str) -> None:
    for p in (json_path, raw_path):
        if not os.path.exists(p):
            raise RuntimeError("optimize 未产出: " + p)
    print(f"optimize 产物: {os.path.basename(json_path)} ({os.path.getsize(json_path)} B), "
          f"{os.path.basename(raw_path)} ({os.path.getsize(raw_path)} B)")


def main():
    ap = argparse.ArgumentParser(description="icraft 独立 optimize 阶段")
    ap.add_argument("--json", required=True, help="parsed 模型 .json")
    ap.add_argument("--raw", required=True, help="parsed 模型 .raw")
    ap.add_argument("--jr_path", required=True, help="输出目录（imodel/BY/<bits>）")
    ap.add_argument("--icraft", default="C:/Icraft/CLI", help="icraft CLI 根目录")
    args = ap.parse_args()

    j, r = run_optimize(args.json, args.raw, args.jr_path, args.icraft)
    print("\noptimize 完成:\n ", j, "\n ", r)
    verify(j, r)


if __name__ == "__main__":
    main()
