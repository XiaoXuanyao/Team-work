#!/usr/bin/env python3
"""icraft 独立 parse 阶段封装。

调用 `icraft-parse.exe`（命令行参数方式）执行框架模型导入（icraft 五阶段第 1 阶段），
产出 `*_parsed.json` / `*_parsed.raw`。

注：icraft 无 `compile` 命令，各阶段由独立 exe（icraft-parse/optimize/quantize/adapt/generate）驱动。

依赖: icraft CLI（Windows，默认 C:/Icraft/CLI，可 --icraft 指定）。
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(icraft_cli: str) -> str:
    """icraft_cli 可为 CLI 根目录或某个 exe 直接路径，返回 CLI 根目录。"""
    if icraft_cli.lower().endswith(".exe"):
        return os.path.dirname(icraft_cli)
    return icraft_cli


def parse_cmd(
    net_name: str,
    onnx_path: str,
    jr_path: str,
    icraft_cli: str,
    imgsz: int = 640,
) -> list:
    """构造 icraft-parse.exe 命令行。"""
    exe = os.path.join(_root(icraft_cli), "bin", "icraft-parse.exe")
    return [
        exe,
        "--net_name", net_name,
        "--network", os.path.abspath(onnx_path),
        "--jr_path", os.path.abspath(jr_path),
        "--framework", "onnx",
        "--target", "buyi",
        "--inputs", f"1,{imgsz},{imgsz},3",
        "--inputs_layout", "NHWC",
        "--pre_method", "resize",
        "--pre_scale", "255.0,255.0,255.0",
        "--pre_mean", "0.0,0.0,0.0",
        "--channel_swap", "0,1,2",
    ]


def run_parse(
    onnx_path: str,
    net_name: str,
    outdir: str,
    workdir: str,
    icraft_cli: str,
    imgsz: int = 640,
    quant_bits: int = 8,
):
    """调用 icraft-parse，产出 *_parsed.json/.raw。"""
    if not os.path.exists(_root(icraft_cli)):
        raise RuntimeError(f"icraft CLI 不存在: {icraft_cli}")

    quant_dir = str(quant_bits)
    out_imodel = os.path.join(outdir, "imodel", "BY", quant_dir)
    os.makedirs(out_imodel, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)

    cmd = parse_cmd(net_name, onnx_path, out_imodel, icraft_cli, imgsz)
    print(">>>", " ".join(cmd), "(cwd:", workdir + ")")
    proc = subprocess.run(cmd, cwd=workdir)
    if proc.returncode != 0:
        raise RuntimeError(f"icraft parse 失败 (returncode={proc.returncode})")

    json_out = os.path.join(out_imodel, f"{net_name}_parsed.json")
    raw_out = os.path.join(out_imodel, f"{net_name}_parsed.raw")
    return json_out, raw_out


def verify(json_path: str, raw_path: str, net_name: str) -> None:
    import json as _json

    for p in (json_path, raw_path):
        if not os.path.exists(p):
            raise RuntimeError("parse 未产出: " + p)
    with open(json_path, encoding="utf-8") as f:
        d = _json.load(f)
    print(f"parse 产物: {os.path.basename(json_path)} ({len(d.get('ops', []))} ops), "
          f"{os.path.basename(raw_path)} ({os.path.getsize(raw_path)} B)")
    for op in d.get("ops", []):
        t = op.get("_type_key", "")
        if t.endswith("Input"):
            dt = op.get("outputs", [{}])[0].get("dtype", {})
            print("  INPUT", dt.get("shape"), dt.get("layout"))


def main():
    ap = argparse.ArgumentParser(description="icraft 独立 parse 阶段")
    ap.add_argument("--onnx", required=True, help="one2one ONNX 路径")
    ap.add_argument("--name", default="yolo26", help="模型名")
    ap.add_argument("--outdir", default=None, help="产物目录（默认 modelconverter/output）")
    ap.add_argument("--workdir", default=None, help="编译工作目录")
    ap.add_argument("--icraft", default="C:/Icraft/CLI", help="icraft CLI 根目录")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--bits", type=int, default=8)
    args = ap.parse_args()

    # 默认路径：modelconverter/output（作为最终产物）与 output/temp/icraft_build
    mc_root = os.path.dirname(HERE)  # modelconverter/
    outdir = args.outdir or os.path.join(mc_root, "output")
    workdir = args.workdir or os.path.join(outdir, "temp", "icraft_build")

    j, r = run_parse(args.onnx, args.name, outdir, workdir, args.icraft, args.imgsz, args.bits)
    print("\nparse 完成:\n ", j, "\n ", r)
    verify(j, r, args.name)


if __name__ == "__main__":
    main()
