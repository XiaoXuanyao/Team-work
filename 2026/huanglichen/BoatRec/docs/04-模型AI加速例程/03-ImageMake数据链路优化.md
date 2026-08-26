# 03 ImageMake 数据链路优化与硬件后处理 DetPost

> 璞致板（FMQL100TAI900/ql100aiu）YOLO26（13 类船舶 chusai 模型）推理提速记录。
> **fp32 host 预处理 253ms → ImageMake 硬件预处理 38.5ms → DetPost 硬件后处理 20.9ms（约 12×）**，
> 精度由 FP32 mAP@0.5:0.95=0.638 微降至 DetPost 0.591（旧定稿，量化+硬件损失约 7%）。
> **2026-08-15 更新：MuSGD 微调模型 chusai_finetune2 成为新定稿（板上 0.619，见 §1）。**

## 1 提速链路与最终结论

| 方案 | mAP@0.5:0.95 | mAP@0.5 | mAP@0.75 | forward | 相对 fp32 | 说明 |
|---|---|---|---|---|---|---|
| fp32 host 预处理 | 0.638 | 0.840 | — | 253ms | 1× | 精度基准（chusai 直接训练） |
| ImageMake | 0.598 | 0.790 | — | 38.5ms | 6.6× | 硬件预处理（含量化优化） |
| chusai + DetPost | 0.591 | 0.785 | 0.695 | 20.9ms | 12.1× | 旧定稿（直接训练模型） |
| **chusai_finetune2 + DetPost** | **0.619** | **0.805** | **0.722** | **20.93ms** | **12.1×** | **新定稿（MuSGD 微调，无 mix 编译）** |

> **定稿（2026-08-15）**：采用 **chusai_finetune2（v2，MuSGD 微调）+ DetPost** 方案。
> FP32 0.671 → 板上 0.619（量化损失 -7.8%，与直接训练相当），速度 20.9ms 不变。
> 较旧定稿 chusai+DetPost（0.591/0.785）全面领先（+2.8 点 mAP50-95、+2.0 AP50、+2.7 AP75）。
> 微调与实验细节见 `00-例程/05-微调与量化实验.md`。

## 2 耗时瓶颈

- **fp32（253ms）**：瓶颈在 host CPU 输入预处理子图 `Resize→Add→AlignAxis→Cast`（~215ms），NPU 仅 ~7.8ms。
- **ImageMake（38.5ms）**：NPU 推理 19.1ms + **CPU 输出解码 Cast/PruneAxis ~16ms** + ImageMake 1.9ms。
  输出解码不可精简，只能下沉到 DetPost 硬件。

## 3 硬件/位流确认

- **ImageMake、DetPost 均已在当前 custop2 位流**（`Enable_ImageMake/Enable_DetPost=true`，RTL `image_make_top.v`/`icore_post_top.v`），**无需重编译 Vivado**。
- 地址映射：CDMA 内部 `0x8000_0000`/系统 `0x1000C0000`；ImageMake 内部 `0x8000_0400`/系统 `0x100000400`。

## 4 编译流程（本地）

```powershell
# 1) customop DLL 复制到 icraft bin（首次；DetPost 必须复制，否则 adapt 报 dll 不存在）
Copy-Item C:\Icraft\CustomOp_v3.31.1\customop.ImageMake*.dll C:\Icraft\CLI\bin\
Copy-Item C:\Icraft\CustomOp_v3.31.1\customop.DetPost*.dll    C:\Icraft\CLI\bin\

# 2) 量化（⚠️ 与 DetPost 组合时【禁用】--mix_precision，必须全 int8；--qtset 指定任务校准集）
python modelconverter.py quantize --name chusai_finetune2 --bits 8 --qtset qtset\chusai

# 3) adapt 插入 ImageMake + DetPost（必须带 --pass_on 显式开启）
python modelconverter.py adapt --name chusai_finetune2 --bits 8 `
    --custom_config config\customop\chusai_detpost.toml `
    --pass_on "customop.ImageMakePass,customop.DetPostPass"

# 4) generate 后上传 *_BY.json/.raw 到板上 imodel/<name>/
```

> ⚠️ **编译坑（2026-08-15 实测）**：`quantize --mix_precision auto` **与 DetPost 不兼容**。
> mix 版产物异常：DetPost 输出 128→64 通道、`data_thr` 溢出（[-22]→[-4933]）、
> generate 主输出 `[1,80,80,64]`、HardOp 16（正常 5）、BY ops 27（正常 10），
> 板上 DetPost 输出 0 候选（运行时 shape `(1,1,0,40)`），评估 mAP 全 0。
> **必须不带 mix（全 int8）重编译**，产物恢复 128 通道、`data_thr` 正常量级。
> 排查线索：generate 输出通道 / data_thr 量级 / BY json ops 数。

customop toml 关键段（`config/customop/chusai_detpost.toml`）：
```toml
[ImageMake]
forward_dll = "C:/Icraft/CLI/bin/customop.ImageMake.dll"
no_imkpad = 1
quantized = true
[DetPost]
forward_dll = "C:/Icraft/CLI/bin/customop.DetPost.dll"
quantized = true
thr_f = 0.001
cmp_en = 1
groups = 3
anchor_num = 1   # YOLO26 anchor-free
position = -1
```
> 编译端插件位于 `C:\Icraft\CustomOp_v3.31.1\`（含 DetPost/GridSample/SegPost/WarpAffine），
> 板上运行库 `/usr/lib/aarch64-linux-gnu/libcustomop.DetPost.so`。

## 5 关键运行要点（调试结论）

1. **ImageMake 正确调用**：每帧 `dmaInit(...)` 搬输入 + `forward` + `device.reset(1)`。
   缺 `dmaInit`/`reset` 会报 `ImageMake Timeout`/`accept {0} data`。apply 时自动配置 ImageMake 寄存器。
2. **输入预处理用 letterbox 居中**（`r=min(640/h,640/w)` 等比 + pad 114 居中），
   不用 `cv2.resize` 拉伸（变形掉精度）。输入必须 640×640 uint8。
   坐标逆映射：`(x - pad_left)/r`（统一比例 r）。
3. **adapt 必须 `--pass_on`**：只给 `--custom_config` 不传 `--pass_on`，ImageMake/DetPost 节点不会插入
   （此前误判为 mix_precision 破坏 ImageMake，实为缺 pass_on）。

## 6 DetPost 输出解码（YOLO26 anchor-free, box 无 DFL）

DetPost 输出 3 张量（每尺度一个），shape `[1,1,obj_num,80]` int8，每候选 80 字节：
```
[0:13] cls logits（13 类，pad 到 64） [64:68] box ltrb 偏移（无 DFL，直接乘 box_scale）
[74:75] location_x  [76:77] location_y  [78:79] anchor_index
```
解码（`o_scale` 6 值 = 3 尺度 × {cls,box}，stride=[8,16,32]）：
```python
prob = sigmoid(cls_logits * cls_scale)          # 取 argmax
x1 = loc_x+0.5 - box[0]*box_scale; y1 = loc_y+0.5 - box[1]*box_scale
x2 = loc_x+0.5 + box[2]*box_scale; y2 = loc_y+0.5 + box[3]*box_scale
x = (x1+x2)/2*stride; w = (x2-x1)*stride        # y,h 同理
```
> `anchor_length=80` 由 `_getReal_out_channles` 计算（`_mid_c(13)=64 + _last_c(4)=16`）。
> 参考 `boatdet/example/yolov10_icraft/3_deploy/src/postprocess_yolov10.hpp`。

## 7 量化损失与优化

- **损失**：FP32→int8 量化损失（mAP@0.5:0.95）：chusai 直接训练 -7.9%（0.642→0.591）、
  chusai_finetune2 -7.8%（0.671→0.619）——两者相当，主要来自 int8 本身，无法消除。
- **优化**：换任务校准集单独作用有限。`--mix_precision auto` 对 **ImageMake 版（无 DetPost）**
  有效（难类 tuochuan AP50 0.416→0.459、bujijian 0.731→0.764，AP50-95 0.594→0.598）；
  但**与 DetPost 组合会破坏编译产物**（见 §4 坑），DetPost 版必须全 int8。

## 8 关键路径速查

| 项 | 路径 |
|---|---|
| 位流（含 ImageMake/DetPost） | `data/bitstream/ai7100_top_custop2_puzhi_swap.bin` |
| customop 配置 | `boatdet/modelconverter/config/customop/chusai_imk.toml`、`chusai_detpost.toml` |
| 编译脚本 | `boatdet/modelconverter/src/quantize.py`（`--mix_precision`/`--qtset`）、`adapt.py`（`--pass_on`） |
| 解码+评估脚本 | 板上 `boatdet/yolo26_demo/board/eval.py`（--model）、`board/diag.py --task bench`；本机 `eval_local/eval_coco_metrics.py`、`eval_local/fp32_eval.py` |
| 模型产物 | 旧定稿 `boatdet/modelconverter/output/chusai_detpost/imodel/BY/8/`；板上 `imodel/chusai_detpost/` |
| 新定稿产物 | `boatdet/modelconverter/output/chusai_finetune2/imodel/BY/8/`；板上 `imodel/chusai_finetune2/`（无 mix 编译） |
| 板上评估/上板 | `board/eval.py --model <name>`（默认新定稿）、`board/diag.py --task probe`（结构探测）、`eval_local/board_eval.py`（上板工具） |
| 校准集 | `boatdet/modelconverter/qtset/chusai/`（11 张船舶图） |
| YOLOv10 DetPost 解码参考 | `boatdet/example/yolov10_icraft/3_deploy/src/postprocess_yolov10.hpp` |
| icraft 插件 | `C:\Icraft\CustomOp_v3.31.1\`；板上 `/usr/lib/aarch64-linux-gnu/libcustomop.DetPost.so` |
| dmaInit 实现 | `boatdet/yolo26_demo/pyrtutils/et_device.py` |
| 硬件布局文档 | `C:\Icraft\CLI v3.31.1\docs\extensibility\customop.html` |

> pycocotools 取 AP：用 `ev.eval["precision"]` 按官方公式（`precision[:, :, :, 0, -1]`=AP50-95、
> `precision[0, :, :, 0, -1]`=AP50），勿直接索引 `precision[0]`（会算错）。
