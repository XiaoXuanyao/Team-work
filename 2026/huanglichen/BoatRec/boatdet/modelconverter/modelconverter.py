#!/usr/bin/env python3
"""modelconverter —— YOLO26 -> 复旦微布衣(BUYI)格式转换。

一键把训练得到的 YOLO26 权重转换为璞致板可部署的 *_BY.json/.raw。
实现模块在 src/（prune/export + 五阶段 parse/optimize/quantize/adapt/generate），
本文件是唯一主入口。

output 按"一模型一目录"组织：output/<name>/
    imodel/BY/<bits>/  五阶段中间模型（*_parsed/_optimized/_quantized/_adapted）
    temp/              中间产物（.onnx、pruned .pt、icraft 工作目录）
    <name>_BY.json/.raw   最终部署产物（模型根目录）

  python modelconverter.py prune      --weights input/yolo26.pt --classes 13 --name yolo26
  python modelconverter.py export     --weights input/yolo26.pt --classes 13 --name yolo26
  python modelconverter.py parse      --onnx <x.onnx> --name yolo26
  python modelconverter.py optimize   --name yolo26
  python modelconverter.py quantize   --name yolo26
  python modelconverter.py adapt      --name yolo26
  python modelconverter.py generate   --name yolo26
  python modelconverter.py compile    --onnx <x.onnx> --name yolo26
  python modelconverter.py all        --weights input/yolo26.pt --classes 13 --name yolo26
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src import export as export_mod
from src import compile as compile_mod
from src import prune as prune_mod
from src import parse as parse_mod
from src import optimize as optimize_mod
from src import quantize as quantize_mod
from src import adapt as adapt_mod
from src import generate as generate_mod

INPUT_DIR = os.path.join(HERE, "input")     # 输入 YOLO26 .pt
OUTPUT_DIR = os.path.join(HERE, "output")   # 一模型一目录
DEFAULT_NAME = "yolo26"


def _name(args) -> str:
    return getattr(args, "name", None) or DEFAULT_NAME


def model_dir(name: str) -> str:
    return os.path.join(OUTPUT_DIR, name)


def temp_dir(name: str) -> str:
    return os.path.join(model_dir(name), "temp")


def imodel_dir(name: str, bits: int) -> str:
    return os.path.join(model_dir(name), "imodel", "BY", str(bits))


def _default_onnx(name: str) -> str:
    return os.path.join(temp_dir(name), f"{name}.onnx")


def cmd_prune(args):
    name = _name(args)
    temp = temp_dir(name)
    os.makedirs(temp, exist_ok=True)
    m = prune_mod.load_pruned(args.weights, args.classes)
    nl = m.model[-1].nl
    print(f"剪枝完成: 保留 one2one 检测头, nl={nl}, 输出 {prune_mod._HEAD_OUT_ORDER}")
    if args.save:
        import torch
        os.makedirs(os.path.dirname(os.path.abspath(args.save)) or ".", exist_ok=True)
        torch.save(m.state_dict(), args.save)
        print("已另存:", args.save)


def cmd_parse(args):
    name = _name(args)
    os.makedirs(temp_dir(name), exist_ok=True)
    onnx = args.onnx or _default_onnx(name)
    j, r = parse_mod.run_parse(onnx, name, model_dir(name), temp_dir(name),
                               args.icraft, args.imgsz, args.bits)
    print("\nparse 完成:\n ", j, "\n ", r)
    parse_mod.verify(j, r, name)


def cmd_optimize(args):
    name = _name(args)
    imodel = imodel_dir(name, args.bits)
    j, r = optimize_mod.run_optimize(
        args.json or os.path.join(imodel, f"{name}_parsed.json"),
        args.raw or os.path.join(imodel, f"{name}_parsed.raw"),
        imodel, args.icraft,
    )
    print("\noptimize 完成:\n ", j, "\n ", r)
    optimize_mod.verify(j, r)


def cmd_quantize(args):
    name = _name(args)
    imodel = imodel_dir(name, args.bits)
    j, r = quantize_mod.run_quantize(
        args.json or os.path.join(imodel, f"{name}_optimized.json"),
        args.raw or os.path.join(imodel, f"{name}_optimized.raw"),
        imodel, args.icraft, args.qtset, args.bits, args.saturation, args.per,
        args.mix_precision,
    )
    print("\nquantize 完成:\n ", j, "\n ", r)
    quantize_mod.verify(j, r)


def cmd_adapt(args):
    name = _name(args)
    imodel = imodel_dir(name, args.bits)
    j, r = adapt_mod.run_adapt(
        args.json or os.path.join(imodel, f"{name}_quantized.json"),
        args.raw or os.path.join(imodel, f"{name}_quantized.raw"),
        imodel, args.icraft, args.custom_config, args.pass_on,
    )
    print("\nadapt 完成:\n ", j, "\n ", r)
    adapt_mod.verify(j, r)


def cmd_generate(args):
    name = _name(args)
    imodel = imodel_dir(name, args.bits)
    j, r = generate_mod.run_generate(
        args.json or os.path.join(imodel, f"{name}_adapted.json"),
        args.raw or os.path.join(imodel, f"{name}_adapted.raw"),
        imodel, args.icraft,
    )
    print("\ngenerate 完成:\n ", j, "\n ", r)
    generate_mod.verify(j, r)


def cmd_export(args):
    name = _name(args)
    os.makedirs(temp_dir(name), exist_ok=True)
    out = getattr(args, "out", None) or _default_onnx(name)
    export_mod.export(args.weights, out, args.classes, args.imgsz,
                      getattr(args, "opset", 17))
    print("导出完成:", out)
    if args.inspect:
        export_mod.inspect(out)


def cmd_compile(args):
    name = _name(args)
    model = model_dir(name)
    os.makedirs(temp_dir(name), exist_ok=True)
    onnx = getattr(args, "onnx", None) or _default_onnx(name)
    j, r = compile_mod.compile(
        onnx_path=onnx, net_name=name, outdir=model, icraft_cli=args.icraft,
        qtset=args.qtset, imgsz=args.imgsz, bits=args.bits, custom_config=args.custom_config,
    )
    # 最终 *_BY.json/.raw 复制到模型目录根
    for ext in (".json", ".raw"):
        shutil.copy2(os.path.join(imodel_dir(name, args.bits), f"{name}_BY{ext}"),
                     os.path.join(model, f"{name}_BY{ext}"))
    print("\n编译完成:\n ", j, "\n ", r)
    compile_mod.verify(j, r)
    print("最终产物:")
    print("  ", os.path.join(model, f"{name}_BY.json"))
    print("  ", os.path.join(model, f"{name}_BY.raw"))


def cmd_all(args):
    args.inspect = False
    cmd_export(args)
    cmd_compile(args)


def build_parser():
    ap = argparse.ArgumentParser(prog="modelconverter", description="YOLO26 -> BUYI 转换")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_name(sp, help_="模型名（决定 output/<name>/ 目录）"):
        sp.add_argument("--name", default=DEFAULT_NAME, help=help_)

    p = sub.add_parser("prune", help="one2one 剪枝（去 one2many 头）")
    add_name(p)
    p.add_argument("--weights", default=os.path.join(INPUT_DIR, "yolo26.pt"))
    p.add_argument("--classes", type=int, default=13)
    p.add_argument("--save", default=None, help="剪枝后另存 .pt（默认 output/<name>/temp/）")
    p.set_defaults(func=cmd_prune)

    pa = sub.add_parser("parse", help="icraft 阶段1: onnx -> *_parsed")
    add_name(pa)
    pa.add_argument("--onnx", default=None, help="one2one ONNX（默认 output/<name>/temp/）")
    pa.add_argument("--icraft", default="C:/Icraft/CLI")
    pa.add_argument("--imgsz", type=int, default=640)
    pa.add_argument("--bits", type=int, default=8)
    pa.set_defaults(func=cmd_parse)

    sp = sub.add_parser("optimize", help="icraft 阶段2: *_parsed -> *_optimized")
    add_name(sp); sp.add_argument("--json", default=None); sp.add_argument("--raw", default=None)
    sp.add_argument("--bits", type=int, default=8); sp.add_argument("--icraft", default="C:/Icraft/CLI")
    sp.set_defaults(func=cmd_optimize)

    sp = sub.add_parser("quantize", help="icraft 阶段3: *_optimized -> *_quantized")
    add_name(sp); sp.add_argument("--json", default=None); sp.add_argument("--raw", default=None)
    sp.add_argument("--bits", type=int, default=8); sp.add_argument("--icraft", default="C:/Icraft/CLI")
    sp.add_argument("--qtset", default=quantize_mod.DEFAULT_QTSET)
    sp.add_argument("--saturation", default="kld"); sp.add_argument("--per", default="channel")
    sp.add_argument("--mix_precision", default=None, help="混合精度: auto 或 <xx.csv>")
    sp.set_defaults(func=cmd_quantize)

    sp = sub.add_parser("adapt", help="icraft 阶段4: *_quantized -> *_adapted")
    add_name(sp); sp.add_argument("--json", default=None); sp.add_argument("--raw", default=None)
    sp.add_argument("--bits", type=int, default=8); sp.add_argument("--icraft", default="C:/Icraft/CLI")
    sp.add_argument("--custom_config", default=None, help="customop toml（可选）")
    sp.add_argument("--pass_on", default=None, help="启用的 pass，如 customop.ImageMakePass")
    sp.set_defaults(func=cmd_adapt)

    sp = sub.add_parser("generate", help="icraft 阶段5: *_adapted -> *_BY.json/.raw")
    add_name(sp); sp.add_argument("--json", default=None); sp.add_argument("--raw", default=None)
    sp.add_argument("--bits", type=int, default=8); sp.add_argument("--icraft", default="C:/Icraft/CLI")
    sp.set_defaults(func=cmd_generate)

    e = sub.add_parser("export", help="YOLO26.pt -> one2one.onnx")
    add_name(e)
    e.add_argument("--weights", default=os.path.join(INPUT_DIR, "yolo26.pt"))
    e.add_argument("--out", default=None, help="one2one ONNX 输出（默认 output/<name>/temp/）")
    e.add_argument("--classes", type=int, default=13)
    e.add_argument("--imgsz", type=int, default=640)
    e.add_argument("--opset", type=int, default=17)
    e.add_argument("--inspect", action="store_true")
    e.set_defaults(func=cmd_export)

    c = sub.add_parser("compile", help="五阶段编排: onnx -> *_BY.json/.raw")
    add_name(c)
    c.add_argument("--onnx", default=None, help="one2one ONNX（默认 output/<name>/temp/）")
    c.add_argument("--qtset", default=compile_mod.DEFAULT_QTSET)
    c.add_argument("--icraft", default="C:/Icraft/CLI")
    c.add_argument("--imgsz", type=int, default=640)
    c.add_argument("--bits", type=int, default=8)
    c.add_argument("--custom_config", default=None)
    c.set_defaults(func=cmd_compile)

    a = sub.add_parser("all", help="export + compile 全链路")
    add_name(a)
    a.add_argument("--weights", default=os.path.join(INPUT_DIR, "yolo26.pt"))
    a.add_argument("--classes", type=int, default=13)
    a.add_argument("--imgsz", type=int, default=640)
    a.add_argument("--qtset", default=compile_mod.DEFAULT_QTSET)
    a.add_argument("--icraft", default="C:/Icraft/CLI")
    a.add_argument("--bits", type=int, default=8)
    a.add_argument("--custom_config", default=None)
    a.set_defaults(func=cmd_all)

    return ap


def main():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ap = build_parser()
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
