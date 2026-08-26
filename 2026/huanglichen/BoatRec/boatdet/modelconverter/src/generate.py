#!/usr/bin/env python3
"""icraft 独立 generate 阶段封装。

调用 `icraft-generate.exe`（命令行参数方式）对 adapted 网络做代码生成
（icraft 五阶段第 5 阶段），产出最终片上部署模型 `*_BY.json` / `*_BY.raw`
（net_name + "_BY"）。

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


def generate_cmd(json_in: str, raw_in: str, jr_path: str, icraft_cli: str,
                 ddr_base: int = 4096) -> list:
    exe = os.path.join(_root(icraft_cli), "bin", "icraft-generate.exe")
    return [
        exe,
        "--json", os.path.abspath(json_in),
        "--raw", os.path.abspath(raw_in),
        "--jr_path", os.path.abspath(jr_path),
        "--ddr_base", str(ddr_base),
    ]


def run_generate(json_in: str, raw_in: str, jr_path: str, icraft_cli: str,
                 ddr_base: int = 4096):
    """调用 icraft-generate，产出 *_BY.json/.raw。返回 (json_out, raw_out)。"""
    if not os.path.exists(_root(icraft_cli)):
        raise RuntimeError(f"icraft CLI 不存在: {icraft_cli}")
    for p in (json_in, raw_in):
        if not os.path.exists(p):
            raise RuntimeError("输入缺失: " + p)

    os.makedirs(jr_path, exist_ok=True)
    cmd = generate_cmd(json_in, raw_in, jr_path, icraft_cli, ddr_base)
    print(">>>", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=jr_path)
    if proc.returncode != 0:
        raise RuntimeError(f"icraft generate 失败 (returncode={proc.returncode})")

    with open(json_in, encoding="utf-8") as f:
        net_name = json.load(f).get("name")
    json_out = os.path.join(jr_path, f"{net_name}_BY.json")
    raw_out = os.path.join(jr_path, f"{net_name}_BY.raw")
    return json_out, raw_out


def verify(json_path: str, raw_path: str) -> None:
    for p in (json_path, raw_path):
        if not os.path.exists(p):
            raise RuntimeError("generate 未产出: " + p)
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    outs = [op for op in d.get("ops", []) if str(op.get("_type_key", "")).endswith("Output")]
    hs = sum(1 for op in d.get("ops", []) if op.get("_type_key") == "icraft::xir::HardOp")
    print(f"generate 产物: {os.path.basename(json_path)} ({len(d.get('ops', []))} ops), "
          f"{os.path.basename(raw_path)} ({os.path.getsize(raw_path)} B)")
    print(f"HardOp: {hs}, 主输出: {len(outs)}")
    for op in outs:
        dt = op.get("inputs", [{}])[0].get("dtype", {})
        print("  OUTPUT", op.get("name"), dt.get("shape"), dt.get("layout"))


def main():
    ap = argparse.ArgumentParser(description="icraft 独立 generate 阶段")
    ap.add_argument("--json", required=True, help="adapted 模型 .json")
    ap.add_argument("--raw", required=True, help="adapted 模型 .raw")
    ap.add_argument("--jr_path", required=True, help="输出目录（imodel/BY/<bits>）")
    ap.add_argument("--icraft", default="C:/Icraft/CLI", help="icraft CLI 根目录")
    ap.add_argument("--ddr_base", type=int, default=4096)
    args = ap.parse_args()

    j, r = run_generate(args.json, args.raw, args.jr_path, args.icraft, args.ddr_base)
    print("\ngenerate 完成:\n ", j, "\n ", r)
    verify(j, r)


if __name__ == "__main__":
    main()
