# eval_local —— 本机 FP32 验证（不需板子）

> 与板上评估（`yolo26_demo/` 顶层脚本，icraft 运行时）环境隔离：
> 本目录脚本依赖项目 `.conda`（ultralytics + pycocotools + torch），在 PC 上跑。

## 用途

训练/微调后、上板前，先在本机用 FP32 验证模型质量（one2one 分支 + NMS，
与板上 int8+DetPost 的前后处理参数一致：conf=0.001, iou=0.45, imgsz=640）。

## 用法（项目根目录）

```powershell
& .conda\python.exe boatdet\yolo26_demo\eval_local\fp32_eval.py `
    --weights boatdet\modelconverter\input\chusai.pt `
              boatdet\modelconverter\input\chusai_finetune.pt
```

- 输出：`yolo26_demo/io/output/preds_fp32_<权重名>.json`（COCO 格式，含 shapes，可复用）
- 打印每模型 mAP50-95 / mAP50 / mAP75 + 每类 AP
- 更多参数见 `fp32_eval.py --help`

## 文件

| 文件 | 说明 |
|---|---|
| `fp32_eval.py` | 参数化 FP32 评估（--weights 可多个；复用 `../eval_coco_metrics.py` 的指标构建） |
| `chusai_local.yaml` | 本机数据集配置（训练机 data.yaml 的 path 已改为本机路径） |
