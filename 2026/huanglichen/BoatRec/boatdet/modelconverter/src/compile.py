#!/usr/bin/env python3
"""icraft BUYI(布衣) 编译编排。

按 icraft 五阶段依次调用各独立阶段模块，把 one2one ONNX 编译为可部署的
`*_BY.json` / `*_BY.raw`：

    parse  ->  optimize  ->  quantize  ->  adapt  ->  generate
  (parse)  (optimize)    (quantize)    (adapt)    (generate)

各阶段为独立 py 文件（一阶段一文件），可单独用 `modelconverter.py <stage>` 调用。

依赖: icraft CLI（Windows，默认 C:/Icraft/CLI，可 --icraft 指定）。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_QTSET = os.path.normpath(
    os.path.join(HERE, "..", "..", "example", "yolov10_icraft", "2_compile", "qtset")
)


def _imodel_dir(outdir: str, bits: int) -> str:
    return os.path.join(outdir, "imodel", "BY", str(bits))


def compile(
    onnx_path: str,
    net_name: str,
    outdir: str,
    icraft_cli: str,
    qtset: str = None,
    imgsz: int = 640,
    bits: int = 8,
    custom_config: str = None,
):
    """五阶段编排，产出 *_BY.json/.raw。返回 (json_out, raw_out)。"""
    if not os.path.exists(icraft_cli):
        raise RuntimeError(f"icraft CLI 不存在: {icraft_cli}")
    if not os.path.exists(onnx_path):
        raise RuntimeError("onnx 缺失: " + onnx_path)

    # 延迟 import，避免纯编排也要求全部依赖可用
    from . import parse as parse_mod
    from . import optimize as optimize_mod
    from . import quantize as quantize_mod
    from . import adapt as adapt_mod
    from . import generate as generate_mod

    imodel = _imodel_dir(outdir, bits)
    os.makedirs(imodel, exist_ok=True)

    # 1) parse
    j, r = parse_mod.run_parse(onnx_path, net_name, outdir, imodel, icraft_cli, imgsz, bits)
    # 2) optimize
    j, r = optimize_mod.run_optimize(j, r, imodel, icraft_cli)
    # 3) quantize
    j, r = quantize_mod.run_quantize(j, r, imodel, icraft_cli, qtset or DEFAULT_QTSET, bits)
    # 4) adapt
    j, r = adapt_mod.run_adapt(j, r, imodel, icraft_cli, custom_config)
    # 5) generate
    j, r = generate_mod.run_generate(j, r, imodel, icraft_cli)
    return j, r


def verify(json_path: str, raw_path: str) -> None:
    for p in (json_path, raw_path):
        if not os.path.exists(p):
            raise RuntimeError("编译产物缺失: " + p)
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    hs = sum(1 for op in d.get("ops", []) if op.get("_type_key") == "icraft::xir::HardOp")
    outs = [op for op in d.get("ops", []) if str(op.get("_type_key", "")).endswith("Output")]
    print(f"编译完成: {os.path.basename(json_path)} ({len(d.get('ops', []))} ops, HardOp={hs}), "
          f"{os.path.basename(raw_path)} ({os.path.getsize(raw_path)} B)")
    for op in outs:
        dt = op.get("inputs", [{}])[0].get("dtype", {})
        print("  主输出", op.get("name"), dt.get("shape"), dt.get("layout"))


def main():
    ap = argparse.ArgumentParser(description="icraft BUYI 五阶段编译编排")
    ap.add_argument("--onnx", required=True, help="one2one ONNX 路径")
    ap.add_argument("--name", default="yolo26", help="模型名")
    ap.add_argument("--outdir", default=None, help="产物目录（默认 modelconverter/output）")
    ap.add_argument("--icraft", default="C:/Icraft/CLI", help="icraft CLI 根目录")
    ap.add_argument("--qtset", default=DEFAULT_QTSET, help="量化校准集目录")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--bits", type=int, default=8)
    ap.add_argument("--custom_config", default=None, help="customop toml（可选）")
    args = ap.parse_args()

    outdir = args.outdir or os.path.join(os.path.dirname(HERE), "output")
    j, r = compile(args.onnx, args.name, outdir, args.icraft, args.qtset,
                   args.imgsz, args.bits, args.custom_config)
    print("\n", j, "\n", r)
    verify(j, r)


if __name__ == "__main__":
    main()
