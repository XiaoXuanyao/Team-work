#!/usr/bin/env python3
"""上板工具：上传模型/脚本 → 板上执行评估或诊断 → 拉回结果（paramiko，需项目 .conda）。

用法（项目根目录）：
  & .conda\python.exe boatdet\yolo26_demo\eval_local\board_eval.py --model chusai_finetune2
  & .conda\python.exe boatdet\yolo26_demo\eval_local\board_eval.py --model chusai_finetune2 --task probe
  & .conda\python.exe boatdet\yolo26_demo\eval_local\board_eval.py --model chusai_finetune2 --task bench --model chusai_imk
  & .conda\python.exe boatdet\yolo26_demo\eval_local\board_eval.py --model chusai_finetune2 --skip-eval

参数：
  --model   模型名（imodel/<name>，本机编译产物在 modelconverter/output/<name>/imodel/BY/8/）
  --task    eval（默认：批量评估并拉回 preds）/ probe（结构探测）/ bench（ImageMake 基准）
  --pass    板子 root 密码（默认 fmsh）
  --host    板 IP（默认 169.254.135.20）
  --skip-eval 只上传不执行（同步脚本用）
"""
import os, sys, argparse, paramiko

BASE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.abspath(os.path.join(BASE, "..", "board"))
MC_OUT = os.path.abspath(os.path.join(BASE, "..", "..", "modelconverter", "output"))

REMOTE_BASE = "/root/boatdet/yolo26_demo"
REMOTE_BOARD = REMOTE_BASE + "/board"
FILES_ALWAYS = ["run_yolo26.py", "eval.py", "diag.py", "yolo26_post.py"]  # board/ 脚本（每次同步）


def main():
    ap = argparse.ArgumentParser(description="上板评估/探测工具")
    ap.add_argument("--model", default="chusai_finetune2")
    ap.add_argument("--task", choices=["eval", "probe", "bench"], default="eval")
    ap.add_argument("--pass", dest="pwd", default="fmsh")
    ap.add_argument("--host", default="169.254.135.20")
    ap.add_argument("--nimg", type=int, default=6, help="bench 图片数")
    ap.add_argument("--skip-eval", action="store_true", help="只上传脚本不执行")
    args = ap.parse_args()

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(args.host, username="root", password=args.pwd, timeout=10)
    print("CONNECTED", flush=True)

    def run(cmd, timeout=60):
        _, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        print("$ %s => %d" % (cmd, code), flush=True)
        if out.strip():
            print(out.strip()[-1500:], flush=True)
        if err.strip():
            print("[stderr]", err.strip()[-800:], flush=True)
        return code

    sftp = cli.open_sftp()
    # 1) board/ 脚本（每次同步到板上 board/ 子目录）
    run("mkdir -p %s" % REMOTE_BOARD)
    for f in FILES_ALWAYS:
        local = os.path.join(BOARD_DIR, f)
        if os.path.exists(local):
            sftp.put(local, "%s/%s" % (REMOTE_BOARD, f))
            print("PUT script:", f, flush=True)
    # 2) 模型产物（本地编译目录 → 板上 imodel/<name>/）
    model_dir = os.path.join(MC_OUT, args.model, "imodel", "BY", "8")
    if not os.path.isdir(model_dir):
        print("!! 未找到本机编译产物:", model_dir, flush=True)
        sys.exit(1)
    run("mkdir -p %s/imodel/%s" % (REMOTE_BASE, args.model))
    for f in ("%s_BY.json" % args.model, "%s_BY.raw" % args.model):
        sftp.put(os.path.join(model_dir, f), "%s/imodel/%s/%s" % (REMOTE_BASE, args.model, f))
        print("PUT model:", f, flush=True)
    sftp.close()
    print("UPLOAD DONE", flush=True)

    if args.skip_eval:
        cli.close()
        print("SYNC ONLY DONE")
        return

    if args.task == "probe":
        cmd = "cd %s && python3 diag.py --task probe --model %s" % (REMOTE_BOARD, args.model)
    elif args.task == "bench":
        cmd = "cd %s && python3 diag.py --task bench --model %s --nimg %d" % (REMOTE_BOARD, args.model, args.nimg)
    else:
        cmd = "cd %s && python3 eval.py --model %s" % (REMOTE_BOARD, args.model)

    print("=== RUN ON BOARD: %s ===" % cmd, flush=True)
    _, stdout, stderr = cli.exec_command(cmd, timeout=1800)
    chan = stdout.channel
    chan.settimeout(180)
    buf = b""
    while True:
        try:
            chunk = chan.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                print(line.decode(errors="replace"), flush=True)
        except Exception as e:
            print("[recv timeout]", e, flush=True)
            break
    code = chan.recv_exit_status()
    print("EXIT", code, flush=True)

    if args.task == "eval" and code == 0:
        sftp = cli.open_sftp()
        src = "%s/io/output/preds_%s.json" % (REMOTE_BASE, args.model)
        dst = os.path.join(os.path.dirname(BOARD_DIR), "io", "output", "preds_%s.json" % args.model)
        sftp.get(src, dst)
        sftp.close()
        print("PULL DONE ->", dst, flush=True)
    cli.close()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
