#!/usr/bin/env python3
"""
模型修补工具：将 YOLO 检测头的 Norm/Softmax 硬算子从 FPGA 解耦到 CPU。

用法:
  python3 patch_model.py                          # 修改 imodel/yolo26_0715_BY.json
  python3 patch_model.py path/to/model.json       # 指定模型路径
  python3 patch_model.py --restore                # 从备份恢复原始模型

原理:
  模型的检测头包含 sigmoid(类别得分) + 归一化操作。
  编译时这些操作被融合到 NPU 硬算子 (HardOp @buyit) 中，
  但如果 FPGA bitstream 不包含 Norm/Softmax 硬件模块，
  就需要把检测头相关的 HardOp 移到 CPU (@hostt) 上执行。
  主干网络 (backbone) 的卷积部分仍保留在 FPGA 上。
"""

import json
import os
import sys
import shutil

# 需要移到 CPU 的 HardOp op_id 列表
# 这些是检测头 (Detect Head) 的算子，包含 sigmoid/normalize
# 骨干网络 (Backbone) 的卷积 HardOp 留在 FPGA 上
# 修改前请用 check_model.py 查看模型结构确认 op_id
HEAD_OPS = [2240, 2242, 2244]


def backup_model(json_path: str) -> str:
    """创建 .json.bak 备份"""
    bak_path = json_path + ".bak"
    if not os.path.exists(bak_path):
        shutil.copy2(json_path, bak_path)
        print(f"[INFO] 备份创建: {bak_path}")
    else:
        print(f"[INFO] 备份已存在: {bak_path}")
    return bak_path


def restore_model(json_path: str) -> bool:
    """从 .json.bak 恢复"""
    bak_path = json_path + ".bak"
    if not os.path.exists(bak_path):
        print(f"[ERROR] 找不到备份: {bak_path}")
        return False
    shutil.copy2(bak_path, json_path)
    print(f"[INFO] 已从备份恢复: {bak_path} → {json_path}")
    return True


def list_hard_ops(data: dict):
    """列出模型中所有 HardOp 及其 compile_target"""
    print(f"\n{'='*60}")
    print("模型中的 HardOp 列表:")
    print(f"{'op_id':>6}  {'compile_target':<14}  {'output 形状(前3个)':<40}")
    print(f"{'-'*6}  {'-'*14}  {'-'*40}")
    for op in data.get('ops', []):
        if op.get('_type_key') != 'icraft::xir::HardOp':
            continue
        op_id = op.get('op_id', '?')
        ct = op.get('compile_target', '?')
        shapes = []
        for o in op.get('outputs', [])[:3]:
            s = str(o.get('dtype', {}).get('shape', []))
            shapes.append(s)
        shapes_str = ", ".join(shapes)
        mark = " ← HEAD" if op_id in HEAD_OPS else ""
        print(f"{op_id:>6}  {ct:<14}  {shapes_str:<40}{mark}")
    print()


def patch_model(json_path: str):
    """修改模型：将 HEAD_OPS 从 @buyit 改为 @hostt"""
    if not os.path.exists(json_path):
        print(f"[ERROR] 找不到模型文件: {json_path}")
        sys.exit(1)

    # 备份
    backup_model(json_path)

    with open(json_path, 'r') as f:
        data = json.load(f)

    # 显示修改前的状态
    list_hard_ops(data)

    # 执行修改
    modified = []
    for op in data.get('ops', []):
        op_id = op.get('op_id')
        if op_id in HEAD_OPS and op.get('_type_key') == 'icraft::xir::HardOp':
            old_target = op.get('compile_target', '?')
            if old_target != '@hostt':
                op['compile_target'] = '@hostt'
                modified.append((op_id, old_target, '@hostt'))

    if not modified:
        print("[INFO] 没有需要修改的算子 (可能已经是 @hostt)")
        return

    # 保存
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] 修改完成! 以下 {len(modified)} 个算子已移到 CPU:")
    for op_id, old, new in modified:
        print(f"  op_id={op_id}: {old} → {new}")
    print()


def main():
    if len(sys.argv) == 1:
        # 默认路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "imodel", "yolo26_0715_BY.json")
    elif sys.argv[1] == "--restore":
        # 恢复备份
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "imodel", "yolo26_0715_BY.json")
        if len(sys.argv) >= 3:
            json_path = sys.argv[2]
        restore_model(json_path)
        return
    elif sys.argv[1] in ("--list", "-l"):
        # 只查看，不修改
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "imodel", "yolo26_0715_BY.json")
        if len(sys.argv) >= 3:
            json_path = sys.argv[2]
        with open(json_path, 'r') as f:
            data = json.load(f)
        list_hard_ops(data)
        return
    else:
        json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"[ERROR] 找不到模型文件: {json_path}")
        print(f"用法: python3 patch_model.py [路径/model.json]")
        print(f"      python3 patch_model.py --list [路径/model.json]")
        print(f"      python3 patch_model.py --restore [路径/model.json]")
        sys.exit(1)

    patch_model(json_path)


if __name__ == "__main__":
    main()
