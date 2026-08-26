# C++ API reference

## [icraft_utils.hpp](./icraft_utils.hpp)

### Function `calctime_detail`

- Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void calctime_detail(const std::string &runBackend, icraft::xrt::Session& session)
```

- 参数:

  **runBackend** – 指定后端 ("zg330" 或 "buyi" 等)
  
  **session** – 需要进行耗时统计的session

- 返回:

  None

- 说明:

对输入session进行详细的耗时统计，输出包括该session前向中包含的各个算子的TotalTime、MemcpyTime、HardTime、OtherTime。另外该函数会自动合并并输出session中所有hardop的TotalTime之和、HardTime之和以及每一个customop的TotalTime和HardTime。完整耗时统计信息会被存放在log文件夹中，部分汇总信息会直接在命令窗口输出。额外增加输出网络耗时的统计分析结果，输出在了命令行窗口并写入log文件夹的txt中。示例如下：

```shell
Total_TotalTime: 259.51346 ms, Total_MemcpyTime : 4.8511996 ms, Total_HardTime : 23.2614 ms, Total_OtherTime : 231.40085 ms .
Hardop_TotalTime: 21.121988 ms, Hardop_HardTime : 20.161438 ms.
Customop: GridSample,TotalTime: 2.79673 ms, HardTime : 2.42822 ms.
******************************************************
统计分析结果如下(The analysis results are as follows):
数据传入耗时(Data input time consumption):
Time(ms):3.142     Device:cdma
icore[npu]耗时(Icore [npu] time-consuming):
Time(ms):23.9187     Device:GridSample
数据传出耗时(Data output time consumption):
Time(ms):1.7092     Device:cdma
cpu算子耗时(CPU operator time consumption):
Time(ms):230.744     Device:Null
******************************************************
```

注意：输入session必须已经开启了计时功能，另外若输入session进行了算子合并那么耗时信息log文件中op_name为空值，此为正常现象。

### Function `getJrPath`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
std::pair<std::string, std::string> getJrPath(const std::string& run_backend, const std::string& folderPath, std::string& netname, std::string& targetFileName)
```

- 参数:

  **run_backend** – 是否是仿真(host)或运行至指定后端(buyi/zg330)

  **folderPath** – 指定模型文件所在的文件夹

  **netname** – 网络名称

  **targetFileName** – 指定模型的阶段

- 返回:

  指定文件夹中对应阶段的json文件路径和raw文件路径 (pair)

- 说明:

为了方便通过读入yaml的模型文件夹字段和stage字段找到对应的json文件路径，且保证在linux平台下指定为BY阶段的json.

### Function `openDevice`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
icraft::xrt::Device openDevice(const std::string& run_backend, const std::string& ip, bool mmu_Mode = true, bool cuda_Mode = false, std::string npu_addr = "0x40000000", std::string dma_addr = "0x80000000")
```

- 参数:

  **run_backend** – 是否是仿真(host)或运行至指定后端(buyi/zg330)

  **ip** – 设备的URL中的ip字段

  **mmu_Mode** – mmu模式开启与否

  **cuda_Mode** - 仿真模式下是否开启cudadevice

  **npu_addr** = 设备的URL中的npu_addr 字段

  **dma_addr** = 设备的URL中的dma_addr 字段

- 返回:

  打开的设备对象

- 说明:

通过指定是否运行仿真模式和选定的ip可以打开对应的HostDevice或者BuyiDevice，且根据mmu_Mode字段打开或者关闭设备的mmu模式。

### Function `loadNetwork`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
icraft::xir::Network loadNetwork(const std::string& JSON_PATH, const std::string& RAW_PATH)
```

- 参数:

  **JSON_PATH** – Json文件路径

  **RAW_PATH** – 指定raw的文件路径


- 返回:

  创建得到的网络对象

- 说明:

通过json和raw文件初始化network

### Function `initSession`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
icraft::xrt::Session initSession(const std::string& run_backend, const icraft::xrt::NetworkView& network, icraft::xrt::Device& device, int ocm_option = 4, bool mmuMode = true, bool open_speedmode = true, bool open_compressFtmp = true)
```

- 参数:

  **run_backend** – 是否是仿真(host)或运行至指定后端(buyi/zg330)

  **network** – 网络对象

  **device** – 设备对象

  **ocm_option** – ocm分配方案，支持配置0、1、2、3、-1；0表示关闭ocm优化；1表示选择方案1，2表示选择方案2，3表示选择方案3，-1表示遍历方案1和2选得分较高的方案。

  **mmuMode** –  是否打开mmu，true为打开

  **open_speedmode** –  是否打开speedmode，true为打开

  **open_compressFtmp** –  是否打开compressFtmp，true为打开

- 返回:

  Session 对象

- 说明:

通过指定是否运行仿真模式、network、device、在不同的后端上初始化session会话，而且通过指定mmu、open_compressFtmp、open_speedmode 选择是否开启对应优化功能。

注：若传入mmu为true 则该函数不会进行压缩ftmp和合并硬算子优化。

### Function `CvMat2Tensor`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
icraft::xrt::Tensor CvMat2Tensor(cv::Mat& img, const icraft::xrt::Network& network)
```

- 参数:

  **img** – cv::mat对象

  **network** – 网络对象

- 返回:

  tensor对象

- 说明:

Tensor构造函数，输入是已经经过所需前处理的mat，network参数则是用于获取网络对应位置输入数据的value的tensortype，通过tensortype中的数据存储类型将输入mat转换为对应的数据类型，且根据value完成输入tensor的形状、layout、数据类型的定义，最后将已经转换类型的mat数据copy给输入tensor，完成tensor的构造。 

### Function `data2Tensor`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
template <typename T>
icraft::xrt::Tensor data2Tensor(const T* input_data, const icraft::xir::Value& input_value)
```

- 参数:

  **input_data** – 指向类型T的指针

  **Value** – Value对象


- 返回:

  tensor对象

- 说明:

Tensor构造函数，根据输入数据的value的tensortype，通过tensortype中的数据存储类型将输入数据的类型转换为对应的数据类型，且根据value完成输入tensor的形状、layout、数据类型的定义，最后将已经转换类型的数据copy给输入tensor，完成tensor的构造。 相对于[CvMat2Tensor](#Function CvMat2Tensor),该函数更加普适。

### Function `getOutputNormratio`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
std::vector<float> getOutputNormratio(icraft::xir::NetworkView network)
```

- 参数:

  **network** – 网络对象（可以是network也可以是networkview）

- 返回:

  对应传入网络的输出数据的Normratio

- 说明:

注意输入网络要为实际需要的结构，保证拿到正确位置的Normratio

### Function `getInputNormratio`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
std::vector<float> getInputNormratio(icraft::xir::NetworkView network)
```

- 参数:

  **network** – 网络对象（可以是network也可以是networkview）

- 返回:

  对应传入网络的输入数据的Normratio

- 说明:

注意输入网络要为实际需要的结构，保证拿到正确位置的Normratio

### Function `removeOutputCast`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void removeOutputCast(icraft::xir::Network& network, bool mmu, icraft::xir::Array<int> idx_list = {})
```

- 参数:

  **network** – 输入网络结构

  **mmu** – bool值，表示是否开启了MMU，如果开启MMU则传入true，未开启MMU传入false;

  **idx_list** – 指定需要删除指定pattern（cast&Pruneaxis）的输出分支的索引值数组；默认为空，将删除所有输出分支的指定pattern（cast&Pruneaxis）；也可配置idx_list={0} 表示删除第1个输出分支的指定pattern（cast&Pruneaxis），分支索引值从0开始计数。

- 返回:

  删除指定输出分支上的指定pattern（cast&Pruneaxis）的算子，并按照原来output算子的ifm顺序重连了hardop<->output后的网络结构。

- 说明:

  removeOutputCast()是用于删除指定输出分支上的指定pattern（cast&Pruneaxis）的一个函数，不仅能在特定分支上找出并删除pattern（cast&Pruneaxis），还能按照原来output算子的ifm顺序重新连接hardop<->output，返回一个新的Network。该网络前向后会按照框架下output顺序输出tensor

- 注意：

  如需使用该函数用于多个sessions的链接，必须关闭MMU，并将链接的输入输出端所有的cpu算子全部删除，即使用removeOutputCast(network1,false)&removeInputCast(network2,false)

### Function `removeInputCast`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void removeInputCast(icraft::xir::Network& network, bool mmu, icraft::xir::Array<int> idx_list = {})
```

- 参数:

  **network** – 输入网络结构

  **mmu** – bool值，表示是否开启了MMU，如果开启MMU则传入true，未开启MMU传入false;

  **idx_list** – 指定需要删除指定pattern（Alignaxis&cast）的输入分支的索引值数组；默认为空，将删除所有输入分支的指定pattern（Alignaxis&cast）；也可配置idx_list={0} 表示删除第1个输入分支的指定pattern（Alignaxis&cast），分支索引值从0开始计数。

- 返回:

  删除指定输入分支上的指定pattern（Alignaxis&cast）的算子，并按照原来input算子的ofm顺序重连了input<->hardop后的网络结构。

- 说明:

  removeInputCast()是用于删除指定输入分支上的cpu算子（Alignaxis&cast）的一个函数，不仅能在特定分支上找出并删除pattern（Alignaxis&cast），还能按照原来input算子的ofm顺序重新连接input<->hardop，返回一个新的Network

- 注意：

  如需使用该函数用于多个sessions的链接，必须关闭MMU，并将链接的输入输出端所有的cpu算子全部删除，即使用removeOutputCast(network1,false)&removeInputCast(network2,false)

### Function `dumpOutputFtmp`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void dumpOutputFtmp(icraft::xir::NetworkView network, std::vector<icraft::xrt::Tensor>& output_tensors, std::string dump_format, std::string log_path)
```

- 参数:

  **network** – 输入网络的networkview结构

  **output_tensors** – 网络session.forward的结果

  **dump_format** – 指定dump特征图使用的格式；支持SFB/SFT/SQB/SQT/HQB/HQT等

  **log_path** – 指定的特征图存放路径

- 返回:

  将网络output_ftmp按输出顺序、指定的格式存放至指定路径

- 注意：

  如推理多张图片，则最终只会保存最后一次输入图片对应的输出结果

### Function `replaceFtmp`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void replaceFtmp(const icraft::xrt::zg330::ZG330Backend &zg_backend, int v_id, std::string ftmp_path)

void replaceFtmp(const icraft::xrt::BuyiBackend &by_backend, int v_id, std::string ftmp_path)
```

- 参数:

  **zg_backend/by_backend** – ZG330后端/Buyi后端对象

  **v_id** – 需要替换ftmp对应的value id

  **ftmp_path** – 用于替换的ftmp文件路径

- 返回:

  无

- 说明:

  将指定backend中指定v_id对应的feature map替换为ftmp_path文件中的内容。
  注意：Buyi后端版本目前暂不支持，调用会抛出异常。如果在Host/OCM上的值也会被跳过。

### Function `dumpFtmps`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void dumpFtmps(const std::string &network_name, const icraft::xrt::zg330::ZG330Backend &zg_backend)

void dumpFtmps(const std::string &network_name, const icraft::xrt::BuyiBackend &buyi_backend)
```

- 参数:

  **network_name** – 网络名称，用于生成日志目录 `./logs/<network_name>`

  **zg_backend/buyi_backend** – ZG330/BUYI后端对象

- 返回:

  无

- 说明:

  将后端中非Host且非OCM的所有中间feature maps (ftmps) dump到 `./logs/<network_name>/` 目录下，文件名为 `<v_id>.ftmp`。

### Function `listIOProcessOps`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
template <typename BackendType>
void listIOProcessOps(icraft::xrt::Session &net_sess)
```

- 参数:

  **net_sess** – 网络Session对象

- 返回:

  无

- 说明:

  打印出所有标记为 "io_process" 的算子信息，以及它们是否运行在指定的 `BackendType` 上。

### Function `dumpImkOutAsImage`

Defined in [icraft_utils.hpp](./icraft_utils.hpp)

```cpp
void dumpImkOutAsImage(const icraft::xrt::Tensor &imk_out_tensor, const std::string &log_path, int imk_port = 0, int channel_bits = 8)

void dumpImkOutAsImage(icraft::xrt::Device device, uint64_t pl_addr, int width, int height, int chn = 3, const std::string &dump_path = "io/output/imagemake", const std::string &runBackend = "buyi", const std::string &prefix = "")
```

- 参数 (Tensor版本):

  **imk_out_tensor** – Imagemake输出的Tensor

  **log_path** – 输出路径

  **imk_port** – Imagemake端口号 (默认0)

  **channel_bits** – 通道位宽 (8或16)

- 参数 (Device版本):

  **device** – 设备对象

  **pl_addr** – PL端物理地址

  **width** – 图像宽

  **height** – 图像高

  **chn** – 通道数 (默认3)

  **dump_path** – 输出路径 (默认 "io/output/imagemake")

  **runBackend** – 运行后端 ("buyi" 或 "zg330")

  **prefix** – 文件名前缀

- 返回:

  无

- 说明:

  将Imagemake的输出保存为图片(png)和二进制文件(ftmp)。
  Tensor版本支持8bit (4通道转RGB) 和 16bit (1通道) 数据。
  Device版本直接从物理地址读取数据，支持Buyi (8SC4转BGR) 和 ZG330 (8SC3转BGR) 格式。

## [NetInfo.hpp](./NetInfo.hpp)

### Struct `Cubic`

Defined in [NetInfo.hpp](./NetInfo.hpp)

```cpp
struct Cubic
{
    int h = 0;
    int w = 0;
    int c = 0;
};
```

- 说明:
  用于存储三维形状 (Height, Width, Channel) 的辅助结构体。

### Class `NetInfo`

Defined in [NetInfo.hpp](./NetInfo.hpp)

```cpp
class NetInfo
```

- 说明:
  网络信息类，用于解析和存储 `icraft::xir::Network` 的关键元数据，如输入输出形状、FPGA算子配置、量化参数等。通常由 `network` 对象初始化。

#### Constructors

```cpp
NetInfo() = default;
NetInfo(const icraft::xir::Network &network);
```

- 参数:
  **network** – 用于初始化的 `icraft::xir::Network` 对象。构造函数会自动解析网络的各个算子，提取输入输出形状、检测是否存在 ImageMake/Resize/DetPost 等特殊算子、获取量化比例 `o_scale` 等信息。

#### Member Variables

- **network**: `icraft::xir::Network`
  保存传入的网络对象。

- **i_shape**, **o_shape**: `std::vector<std::vector<int>>`
  网络的输入和输出张量形状。

- **i_cubic**, **o_cubic**: `std::vector<Cubic>`
  网络输入和输出形状的三维表示 (H, W, C)。

- **head_hardop_i_shape**: `std::vector<std::vector<int>>`
  第一个硬件算子（如 FPGA convolution 或 ImageMake/WarpAffine 等）的输入形状。

- **o_scale**: `std::vector<float>`
  输出张量的量化 scale 或 norm_ratio。

- **fpga_op**: `std::unordered_set<std::string>`
  网络中包含的 FPGA 自定义算子类型集合。

- **bit**, **detpost_bit**: `int`
  主网络和 DetPost 后处理算子的位宽 (默认 8)。

- **mmu**: `bool`
  是否开启 MMU 模式。根据网络 tag `speedmode` 或 `compressFtmp` 自动推断，默认为 true。

- **Flags**:
  - **resize_on**: 是否包含 Resize 算子。
  - **swaporder_on**: 是否包含 SwapOrder 算子。
  - **ImageMake_on**: 是否包含 ImageMake 算子。
  - **DetPost_on**: 是否包含 DetPost (或 DetPostZG) 后处理算子。
  - **WarpAffine_on**: 是否包含 WarpAffine 算子。

- **Operations**:
  - **ImageMakes_**: 存储 ImageMake 算子对象列表。
  - **DetPost_**: 存储 DetPost 算子对象。
  - **WarpAffine_**: 存储 WarpAffine 算子对象。

#### Member Functions

```cpp
virtual std::unordered_set<std::string> fpgaOPlist(icraft::xir::Network &network)
```

- 参数:
  **network** – 需要分析的网络对象。

- 返回:
  包含网络中自定义算子类型的集合。

- 说明:
  遍历网络算子，识别特殊算子（Resize, SwapOrder, ImageMake, DetPost, WarpAffine 等）并更新类成员标志位 (`resize_on`, `ImageMake_on` 等)。构造函数会自动调用此函数。

## [PicPre.hpp](./PicPre.hpp)

### Class `PicPre`

Defined in [PicPre.hpp](./PicPre.hpp)

图片预处理类，基于OpenCV实现，提供图片的读取、Resize、Pad、Crop等操作，自动计算变换比例和Padding信息，用于后续的坐标还原。常用于检测网络的前处理流程。

```cpp
class PicPre
```

#### Enums

- **ResizeModes**:
  - `BOTH_SIDE`: 强制Resize到指定尺寸 (可能形变)
  - `LONG_SIDE`: 按长边等比例缩放
  - `SHORT_SIDE`: 按短边等比例缩放

- **PadModes**:
  - `BR`: 仅在右下角填充
  - `AROUND`: 四周填充

- **YUVFormat**:
  - `NOT_YUV`: 普通图像
  - `YUV_NV12`, `YUV_NV21`: YUV图像格式

#### Constructors

```cpp
PicPre(const std::string &filename, int flags = cv::IMREAD_COLOR);
PicPre(const cv::Mat &img, int height = 0, int width = 0, YUVFormat yuv_fmt = YUVFormat::NOT_YUV);
```

- 参数:
  - **filename**: 图片路径
  - **flags**: OpenCV读取标志，默认读入彩色图 (BGR)
  - **img**: 输入的 OpenCV Mat 对象
  - **height/width**: YUV 图像的高宽 (仅 YUV 格式需要手动指定，因为 YUV 数据在 Mat 中通常是单通道大尺寸)
  - **yuv_fmt**: 指定输入是否为 YUV 格式

#### Member Functions

##### Resize

```cpp
PicPre &Resize(std::pair<int, int> dst_shape_hw, int mode = LONG_SIDE, int interpolation = cv::INTER_LINEAR)
```

- 说明:
  图片缩放函数。根据模式计算缩放比例，并执行 Resize 操作。如果是 YUV 格式会使用专门的 Resize 实现。
- 参数:
  - **dst_shape_hw**: 目标尺寸 `{height, width}`
  - **mode**: 缩放模式 (`PicPre::ResizeModes`)
  - **interpolation**: 插值方式
- 返回:
  `*this` (即 PicPre 对象引用，支持链式调用，如 `img.Resize({...}).rPad()`)

##### rPad

```cpp
void rPad(int pad_mode = PadModes::AROUND)
```

- 说明:
  Resize 后的填充函数。将图像填充到 `Resize` 设定的 `dst_shape_hw` 尺寸。会自动更新 padding 信息。
- 参数:
  - **pad_mode**: 填充模式 (`PicPre::PadModes`)

##### rCenterCrop

```cpp
void rCenterCrop(std::pair<int, int> crop_shape_hw)
```

- 说明:
  中心裁剪函数。直接裁剪中心区域。
- 参数:
  - **crop_shape_hw**: 裁剪尺寸 `{height, width}`

##### Getters

```cpp
std::pair<int, int> getResizedHW();     // 返回 Resize 后的实际图像尺寸 (不含 Pad)
std::pair<float, float> getResizedRatio(); // 返回缩放比例 {ratio_h, ratio_w}
std::pair<float, float> getRatio();     // 同上
std::pair<int, int> getPadInfo();       // 返回填充信息 {top, left}
std::pair<int, int> getPad();           // 同上
```

#### Member Variables

- **src_dims**: `std::tuple<int, int, int>` (C, H, W) 原始图像维度
- **ori_img**: `cv::Mat` 原始图像副本
- **src_img**: `cv::Mat` 处理过程中的源图像 (Resize 前)
- **dst_img**: `cv::Mat` 处理后的图像 (Resize/Pad/Crop 后)


## [modelzoo_utils.hpp](./modelzoo_utils.hpp)

### Function `nms_soft`

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
std::vector<std::tuple<int, float, cv::Rect2f>> nms_soft(std::vector<int>& id_list, std::vector<float>& socre_list, std::vector<cv::Rect2f>& box_list, float IOU, int max_nms = 3000)
```

- 参数:

  **id_list** – 与输入框对应的类别信息

  **score_list** – 与输入框对应的置信度信息

  **box_list** – 输入框信息，要求框的类型为cv::Rect2f

  **iou** – iou阈值

  **max_nms** – 进行非极大抑制前框的数量上限

- 返回:

  经过软件nms筛选之后的框的信息，包括类别、置信度、框的坐标。

- 说明:

  nms_soft是使用c++ stl函数在cpu上完成的非极大抑制功能的函数，在yolo类检测目标框数量较少的情况下，使用nms_soft会快于nms_hard

注意：确保送入该函数的框已在在外部进行了置信度阈值筛选

### Function `coordTrans`

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
std::vector<std::vector<float>> coordTrans(std::vector<std::tuple<int, float, cv::Rect2f>>& nms_res, PicPre& img, bool check_border = true)
```

- 参数:

  **nms_res** –  筛选之后的框的信息，包括类别、置信度、框的坐标

  **img** – picpre对象

  **check_border** – 是否对超边界框进行约束

- 返回:

  检测框在原图上的类别、置信度、坐标信息。

- 说明:

  nms_res中包含的框的坐标是针对前处理之后的图片检测出来的，前处理相关的pad ratio信息记录在picpre对象中，根据前处理信息还原框在原图上的坐标。

### Function `visualize`

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
void visualize(std::vector<std::vector<float>>& output_res, const cv::Mat& img, const std::string resRoot, const std::string name, const std::vector<std::string>& names)
```

- 参数:

  **output_res** – 检测框在原图上的类别、置信度、坐标信息

  **img** – 原图mat对象

  **resRoot** – 结果存放路径

  **name** – 图片名称

  **names** – 类别映射

- 返回:

  None

- 说明:

  根据检测框在原图上的类别、置信度、坐标信息，将其可视化在原图上，其中类别信息通过类别映射为实际标签，最终存储在resRoot中，存图名称根据图片名称决定存储结果名称

### Function `saveRes`

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
void saveRes(std::vector<std::vector<float>>& output_res, std::string resRoot, std::string name)
```

- 参数:

  **output_res** – 检测框在原图上的类别、置信度、坐标信息

  **resRoot** – 结果存放路径

  **name** – 图片名称

- 返回:

  None

- 说明:

  将原图上检测出来框的类别、置信度、坐标信息，以txt的方式存储到resRoot中，目的是为了后续进行精度测试。

### Function drawText

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
void drawText(cv::Mat &input_img, const std::string &text, const std::string &model_name, cv::Scalar color)
void drawText(cv::Mat &input_img, const std::string &text, cv::Scalar color)
void drawTextTopLeft(cv::Mat &input_img, const std::string &text, cv::Scalar color)
void drawTextFourConer(cv::Mat &input_img, const std::string &text, const std::string &fps, cv::Scalar color)
void drawTextOnTwoCorners(cv::Mat &input_img, const std::string &text, const std::string &fps, cv::Scalar color, int top_margin = 10, int left_margin = 10)
```

- 说明:
  在图像上绘制文本信息（如FPS、模型名称等）。提供多种布局方式（左上角、四角、指定位置等）。

### Function randomColor / classColor

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
cv::Scalar randomColor()
cv::Scalar classColor(int id)
```

- 说明:
  生成颜色。`randomColor` 生成随机颜色，`classColor` 根据 id 生成固定颜色（基于预设的 20 色调色板）。

### Function FlipPer4

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
void FlipPer4(int16_t *tensor_data, int size)
```

- 说明:
  辅助函数，用于将 buffer 中的数据每 4 个一组进行反转 (ABCD -> DCBA)。通常用于处理某些硬件的大小端或数据排列差异。

### Function nms

Defined in [modelzoo_utils.hpp](./modelzoo_utils.hpp)

```cpp
std::vector<int> nms(std::vector<cv::Rect> &box_list, std::vector<float> &score_list, std::vector<int> &id_list, const float &conf, const float &iou, const int &NOC)
```

- 参数:
  - **box_list**: 推理出的 bbox列表
  - **score_list**: 置信度列表
  - **id_list**: 类别 id 列表
  - **conf**: 筛选置信度阈值
  - **iou**: 筛选 iou 阈值
  - **NOC**: 类别数量 (Number of Classes)
- 返回:
  保留的框在 `box_list` 中的索引列表。
- 说明:
  通用 NMS 实现，支持多类别。

## [et_device.hpp](./et_device.hpp)

### Function enableCameraVTC

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void enableCameraVTC(icraft::xrt::Device& device, uint64_t base_addr = 0x40080000)
```

- 参数:

  **device** – 输入icraft::xrt::Device，对预设的寄存器进行读写需要device

  **base_addr** – CameraVTC模块寄存器基地址

- 返回:

  None

- 说明:

  使能Camera VTC模块。

### Function yuv2rgb

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void yuv2rgb(icraft::xrt::Device& device, uint64_t base_addr = 0x40080000)
```

- 参数:

  **device** – 输入icraft::xrt::Device，对预设的寄存器进行读写需要device

  **base_addr** – YUV2RGB模块寄存器基地址

- 返回:

  None

- 说明:

  使能PL端YUV转RGB模块。

### Function `fpgaNms`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
std::vector<int> fpgaNms(icraft::xrt::Device& device,const std::vector<int16_t> & nms_pre_data, std::vector<int> nms_pre_idx,int bbox_num, const float& iou, uint64_t base_addr = 0x100001C00)
```

- 参数:

  **Device** – 输入icraft::xrt::Device，对预设的寄存器进行读写需要device

  **nms_pre_data** – 一维数组包含多个框的位置信息和类别信息，按照框的置信度大小从高到低排序的,一个框的信息表示为{x1,y1,x2,y2,class}。

  **nms_pre_idx** – 所有的框按照置信度从高到低排列后,nms_pre_idx 记录了数组中排序后框在原未排序数组中的idx

  **bbox_num** – 框的个数

  **iou** – iou阈值

  **base_addr** – fpgaNms的寄存器基地址，默认配置为当前版本下正确基地址。

- 返回:

  筛选出的框在原未排序数组中的idx

- 说明:

按照函数参数说明配置输入参数即可启动硬件nms模块，另外输入框的信息要预先经过置信度阈值筛选。

### Function `fpgaDma`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void fpgaDma(Tensor& img_tensor, Device& device, uint64_t imk_write_addr = std::numeric_limits<uint64_t>::max(), uint64_t imk_base_addr = 0x100000400, uint64_t dma_base_addr = 0x1000C0000)
```

- 参数:

  **img_tensor** – imagemake的输入tensor

  **device** – 输入icraft::xrt::Device，对预设的寄存器进行读写需要device

  **imk_write_addr**   –  ImageMake写入PLDDR的基地址，默认如果不传入该参数，将在ImageMake forward时配置该地址

  **imk_base_addr**  – ImageMake的寄存器基地址，默认为0x100000400，即input_port = 0对应的寄存器基地址

  **dma_base_addr** – fpgaDma的寄存器基地址，默认配置为当前版本下input_port = 0对应的寄存器基地址。

- 返回:

  None

- 说明:

用于初始化imk和dma模块的寄存器地址，并启动imk数据搬移的一个函数，通过device对预设的寄存器进行读写配置完成启动。

注意：

- 该函数并未进行imagemake 硬算子的初始化，因此要部署不同网络，且输入数据量不同，需要调用initOp接口对imagemake进行初始化，例如[dma_imk_Init](#Function dma_imk_Init)。
- 在多线程psin的情况下，建议提前配置好imk硬件相关imk_write_addr、imk_base_addr的参数，来避免在imk forward时才进行初始化配置，没有留足够的时间，容易导致多线程之间结果错位。

### Function fpgaWarpaffine

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void fpgaWarpaffine(std::vector<std::vector<float>>& M_inversed, Device& device,uint64_t base_addr = 0x100002800)
```

- 参数:

  **M_inversed** –仿射变换中变换矩阵的逆矩阵，尺寸为2x3的浮点数组;

  **device**– 设备对象；

  **base_addr** – fpgaWarpaffine的寄存器基地址，默认配置为当前版本下正确基地址。

- 返回:

  无返回值。

- 说明:

  该函数是用于配置WarpAffine硬算子寄存器参数的一个函数；用户自行计算得到变换矩阵的逆矩阵之后，可在运行时通过该函数配置WarpAffine硬算子寄存器，通过不同的变换矩阵可以在WarpAffine硬算子前向时实现对输入数据不同的仿射变化操作，目前支持平移、放缩、裁剪等，不支持旋转。

- 注意：

  必须先带WarpAffine硬算子完成编译，否则无法使用该函数。

### Function fpgaArgmax2d

Defined in [et_device.hpp](./et_device.hpp)

```cpp
Tensor fpgaArgmax2d(Device& dev, int wsize, int hsize, int valid_csize, int csize,uint64_t arbase,uint64_t last_araddr,uint64_t base_addr = 0x100003000)
```

- 参数:

  **dev** – 输入icraft::xrt::Device

   **wsize** - ftmp的width

  **hsize** - ftmp的height

  **valid_csize** - ftmp的(有效)channel数

  **arbase** - ftmp 在plddr的初始地址

  **last_araddr** - ftmp 在plddr的结束地址

  **base_addr** – fpgaArgmax2d的寄存器基地址，默认配置为当前版本下正确基地址。

- 返回:

  经过硬件argmax2d筛选之后的最值。

- 说明:

  fpgaArgmax2d是用于启动硬件fpga模块argmax2d的一个函数，通过dev对预设的寄存器进行读写配置完成启动。若ftmp尺寸为320x320x22，fpga_argmax2d耗时约0.13ms

  注意：fpga_argmax2d的输出结果在plddr，需要手动搬运至ps端接后续处理



### Function `nms_hard`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
std::vector<std::tuple<int, float, cv::Rect2f>> nms_hard(std::vector<cv::Rect2f>& box_list, std::vector<float>& score_list, std::vector<int>& id_list, const float& iou, icraft::xrt::Device& device, int max_nms = 3000)
```

- 参数:

  **box_list** – 输入框信息，要求框的类型为cv::Rect2f

  **score_list** – 与输入框对应的置信度信息

  **id_list** – 与输入框对应的类别信息

  **iou** – iou阈值

  **device** – 输入icraft::xrt::Device

  **max_nms** – 进行非极大抑制前框的数量上限

- 返回:

  经过硬件nms筛选之后的框的信息，包括类别、置信度、框的坐标。

- 说明:

  nms_hard是用于启动硬件fpga模块nms的一个函数，通过device对预设的寄存器进行读写配置完成启动。

   \*   若最终输出检测数量为500个，nms_hard耗时约0.638ms

   \*   若最终输出检测数量为100个，nms_hard耗时约0.297ms

   \*   当最终检测数量小于30个的情况下，采用nms_soft会比nms_hard速度快。

注意：确保送入该函数的框已在在外部进行了置信度阈值筛选，该函数适配大部分yolo系列模型后处理的hard nms函数，其调用了FPGA_NMS模块

### Function `dmaInit`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void dmaInit(const std::string& runBackend, const bool& has_ImageMake, Tensor& img_tensor, Device& device)
```

- 参数:

  **runBackend** – 是否是仿真(host)或运行至指定后端(buyi/zg330)

  **has_ImageMake** – 网络中是否有imagemake 硬算子

  **img_tensor** – imagemake的输入tensor

  **device** – 输入icraft::xrt::Device，对预设的寄存器进行读写需要device

- 返回:

  None

- 说明:

通过是否是仿真运行时网络中是否有imagemake 硬算子判断是否需要调用setFpgaDma进行配置imk模块并启动imk数据搬移。

### Function `dma_imk_Init`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void dma_imk_Init(const std::string& run_backend, const bool& has_ImageMake, Operation& ImageMake_ ,Tensor& img_tensor, Device& device,Session &session)
```

- 参数:

  **run_backend** – 是否是仿真(host)或运行至指定后端(buyi/zg330)

  **has_ImageMake** – 网络中是否有imagemake 硬算子

  **ImageMake_** – 对应网络中的imagemake 硬算子

  **img_tensor** – imagemake的输入tensor

  **device** – 输入icraft::xrt::Device，对预设的寄存器进行读写需要device

  **session** – 网络对应session

- 返回:

  None

- 说明:

上述[dmaInit](#Function dmaInit)函数中是不去初始化imk算子的，如果要部署不同网络，且输入数据量不同，则要重新初始化imk；如果在前向工程中部署的是相同的网络，那么则不需要初始化，但是即便初始化了也无妨。若必须要初始化可调用dma_imk_Init函数。

### Function `updateDetpost`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void updateDetpost(NetInfo& netinfo, float conf)
```

- 参数:

  **netinfo** – 输入根据network构建的NetInfo

  **conf** – 对应cfg/yaml中的框筛选阈值conf

- 返回:

  空

- 说明:

此函数作用为 如果配置文件cfg/yaml中conf值与compile/custom_op中DetPost算子预设的conf值不一致，则更新Detpost的筛选阈值为cfg/yaml中的筛选阈值。

- 注意事项：
  需要位于创建Netinfo后，initSession前。

### Function hardResizePS

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void hardResizePS(icraft::xrt::Device& dev, const int CAMERA_WIDTH, const int CAMERA_HEIGHT, const int FRAME_WIDTH, const int FRAME_HEIGHT, camera_fmt fmt, crop_position crop, uint64_t base_addr = 0x40080000)
```

- 参数:

  **dev** – 输入icraft::xrt::Device

  **CAMERA_WIDTH** – 摄像头输入图像宽度

  **CAMERA_HEIGHT** – 摄像头输入图像高度

  **FRAME_WIDTH** – Resize后图像宽度

  **FRAME_HEIGHT** – Resize后图像高度

  **fmt** – 摄像头输入格式(RGB565, RGB, RGBA, YUV422)

  **crop** – 裁剪位置(center, top_left, top_right, bottom_left, bottom_right)

  **base_addr** – 模块基地址

- 返回:

  None

- 说明:

  配置PS端Hard Resize模块。

### Function hardResizePL

Defined in [et_device.hpp](./et_device.hpp)

```cpp
template <typename DeviceType>
void hardResizePL(DeviceType& device, int x0, int y0, int x1, int y1, int RATIO_W, int RATIO_H, int CAMERA_WIDTH, int CAMERA_HEIGHT,uint64_t base_addr = 0x40080000)
```

- 参数:

  **device** – 输入device (DeviceType为模板类型)

  **x0** – 起始x0 坐标位置 （0~FRAME_W）

  **y0** – 起始y0 坐标位置 （0~FRAME_H）

  **x1** – 终止x1 坐标位置 （0~FRAME_W）

  **y1** – 终止y1 坐标位置 （0~FRAME_H）

  **RATIO_W** – x方向行步长

  **RATIO_H** – y方向列步长

  **CAMERA_WIDTH** – 图像X方向总长度 （FRAME_W）

  **CAMERA_HEIGHT** –  图像y方向总长度 （FRAME_H）

  **base_addr** – 配置寄存器的默认基地址

- 返回:

  None

- 说明:

hardResizePL是位于plin数据流上面的一个fpga模块，可以完成plin端输入图片（常用从摄像头取帧）的裁剪下采样前处理，hardResizePL函数即是配置hardResizePL模块如何对输入图片进行处理的一个函数。

注意：hardResizePL是plin数据流上的一个必要环节，plin模型下必须进行初始化，另外目前hardResizePL只支持裁剪图片和整数倍下采样。

### Function preprocess_plin

Defined in [et_device.hpp](./et_device.hpp)

```cpp
template <typename DeviceType>
std::tuple<int, int, int, int > preprocess_plin(DeviceType& device,const int CAMERA_WIDTH,const int CAMERA_HEIGHT,const int NET_W, const int NET_H,crop_position crop,uint64_t base_addr = 0x40080000)
```

- 参数:

  **device** – 输入device (DeviceType为模板类型)

  **CAMERA_WIDTH** – 原始输入（摄像头）图像X方向总长度

  **CAMERA_HEIGHT** – 原始输入（摄像头）图像y方向总长度

  **NET_W** – 实际输入网络图像的X方向总长度

  **NET_H** –  实际输入网络图像的X方向总长度

  **crop** – 图片裁剪方式

  **base_addr** – 配置寄存器的默认基地址

- 返回:

  根据指定的图片裁剪方式和原图尺寸及目标图尺寸裁剪后得到的新的图片相对于原图的偏移和采样步长，常用于在原图上进行可视化。

- 说明:

通过输入原始输入（摄像头）图像和实际输入网络图像的尺寸，确定图片裁剪方式，该函数会自动计算hardResizePL所需要的参数并进行寄存器配置和模块启动。

### Function initImageMake

Defined in [et_device.hpp](./et_device.hpp)

```cpp
template <typename DeviceType>
void initImageMake(DeviceType& device, int imk_port, int64_t ImageMakeWidth, int64_t ImageMakeHeight, int64_t ImageMakeChannel, uint64_t ImageMakeWddrBase_a, uint64_t bits, const std::vector<float>& premean_, const std::vector<float>& prescale_data)
```

- 参数:

  **device** – 设备对象(BuyiDevice或ZG330Device)

  **imk_port** – ImageMake端口(0-3)

  **ImageMakeWidth** – 图像宽度

  **ImageMakeHeight** – 图像高度

  **ImageMakeChannel** – 图像通道数

  **ImageMakeWddrBase_a** – 写入DDR基地址

  **bits** – 数据位宽(8 or 16)

  **premean_** – 均值

  **prescale_data** – 缩放因子

- 返回:

  None

- 说明:

  初始化ImageMake硬件算子寄存器。特定设备(ZG330)有特化实现。

### Function runImageMakeForward

Defined in [et_device.hpp](./et_device.hpp)

```cpp
template <typename DeviceType>
void runImageMakeForward(DeviceType& device, int imk_port, int64_t ImageMakeWidth, int64_t ImageMakeHeight, int64_t ImageMakeChannel, uint64_t ImageMakeWddrBase_a, uint64_t bits, bool verbose = false, int sleep_time = 0)
```

- 参数:

  **device** – 设备对象

  **imk_port** – ImageMake端口

  **ImageMakeWidth** – 图像宽度

  **ImageMakeHeight** – 图像高度

  **ImageMakeChannel** – 图像通道数

  **ImageMakeWddrBase_a** – 写入DDR基地址

  **bits** – 数据位宽

  **verbose** – 是否打印调试信息

  **sleep_time** – 轮询等待时的休眠时间(us)

- 返回:

  None

- 说明:

  启动ImageMake前向计算并等待完成。

### Function `PLDDRMemRegion::Plddr_memcpy`

Defined in [et_device.hpp](./et_device.hpp)

```cpp
void Plddr_memcpy(uint64_t read_bottom, uint64_t read_top, uint64_t write_bottom, uint64_t write_top, icraft::xrt::Device& device)
```

- 参数:

  **read_bottom** –PLDDR上src的起始地址;

  **read_top** –PLDDR上src的结束地址;

  **write_bottom**–PLDDR上dest的起始地址;

  **write_top** –PLDDR上dest的结束地址;

  **device**– 设备对象；

- 返回:

  无返回值。

- 说明:

  PLDDRMemRegion::Plddr_memcpy()是将PLDDR上src的数据拷贝给PLDDR上dst的一个函数；需用户给定src存储在PLDDR上的起始&结束地址，以及需要将src拷贝到dest在PLDDR上的起始&结束地址。

- 注意：

  src和dest地址长度需一致，且必须是64整数倍

### Class `Camera`

摄像头类，plin数据流下，一般模型的输入都是从摄像头传入，需要用到该类

- 初始化方法：

  ```cpp
  Camera(BuyiDevice device, uint64_t buffer_size, uint64_t base_addr = 0x40080000)
  ```

  **device** – 设备对象

  **buffer_size** – 摄像头传入数据大小 （若为1K分辨率的RGB565输入，则为1920x1080x2 ）

- 成员函数:

  - `void take(const MemChunk& memchunk)`

    抓取一帧，传到psddr-udmabuf空间上camera_buf处,同时启动imk，将PL_resize处理后图像送入PLDDR中,用于前向推理

  - `bool wait(int wait_time_ms = 100)`

    等待cam的1帧数据写入ps ddr（udmabuf）

  - `void get(int8_t* frame, const MemChunk& memchunk)`

    将psddr-udmabuf空间camera_buf上数据搬到PSDDR

### Class `Display_pHDMI_RGB565`

Hdmi显示抽象类，plin数据流下，显示需要用到该类

- 初始化方法：

```cpp
Display_pHDMI_RGB565(BuyiDevice device, uint64_t buffer_size, MemChunk chunck)
```

  **device** – 设备对象

  **buffer_size** – 显示数据量大小 （若输出1K分辨率的RGB565，则为1920x1080x2 ）

- 成员函数:

  - `void show(int8_t* frame)`

    将处理后的图片数据显示

### Class Display_sHDMI_RGBA

Defined in [et_device.hpp](./et_device.hpp)

Hdmi显示抽象类，用于DemoV1板子，framebuffer驱动。

- 初始化方法：

```cpp
Display_sHDMI_RGBA(const char *dev)
```

  **dev** – framebuffer设备路径 (e.g., "/dev/fb0")

- 成员函数:

  - `void show(int8_t* frame)`

    全屏显示图像帧

  - `void draw_top_left(int8_t *frame)`

  - `void draw_top_right(int8_t *frame)`

  - `void draw_bottom_left(int8_t *frame)`

  - `void draw_bottom_right(int8_t *frame)`

  - `void draw_pixel(int x, int y, uint32_t color)`

  - `void fill_pixel(uint32_t color)`


## [task_queue.hpp](./task_queue.hpp)

### struct `InputMessageForIcore`

- 结构体变量:

  **buffer_index** – 缓存区id

  **image_tensor** – Tensor对象

  **ai** – 是否包含AI推理任务

  **error_frame** – 该帧是否为错帧，默认为false

- 说明:

  该结构体常在多线程任务队列的plin工程中用于初始化icore的输入信息任务队列，例如：`auto icore_task_queue = std::make_shared<Queue<InputMessageForIcore>>(thread_num);`

  buffer_index用于在InputMessageForIcore和IcoreMessageForPost传递 缓存区id信息，来表明改结构体变量中的tensor对象是来自哪一个`camera_buf_group`

  error_frame：若在前向推理中出错，那么该变量将被置为true，后续信息传递到IcoreMessageForPost中，则跳过针对该IcoreMessage的后处理操作。

### struct `IcoreMessageForPost`

- 结构体变量:

  **buffer_index** – 缓存区id

  **icore_tensor** – Tensor对象

  **ai** – 是否包含AI推理任务

  **error_frame** – 该帧是否为错帧，默认为false

- 说明:

  该结构体常在多线程任务队列的plin工程中用于初始化icore的输出信息任务队列，例如：
  
  ```cpp
  auto post_task_queue = std::make_shared<Queue<IcoreMessageForPost>>(thread_num);
  ```

  buffer_index用于在InputMessageForIcore和IcoreMessageForPost传递 缓存区id信息，后处理线程会通过

  ```cpp
  camera.get(display_data, camera_buf_group[post_msg.buffer_index]);
  ```

  将对应的输入数据从psddr-udmabuf空间上camera_buf处拿到psddr上的display_data中用于后处理

  error_frame：若在前向推理中出错，那么该变量将被置为true，并且传递到IcoreMessageForPost中，跳过针对该IcoreMessage的后处理操作。

## [bit_masks.hpp](./bit_masks.hpp)

### Bit Mask Macros

Defined in [bit_masks.hpp](./bit_masks.hpp)

```cpp
#define BIT_MASK_0 0b00000001
#define BIT_MASK_1 0b00000010
#define BIT_MASK_2 0b00000100
#define BIT_MASK_3 0b00001000
#define BIT_MASK_4 0b00010000
#define BIT_MASK_5 0b00100000
#define BIT_MASK_6 0b01000000
#define BIT_MASK_7 0b10000000
#define BIT_MASK_FULL 0b11111111
```

- 说明:

  定义了8位位掩码宏。

## [algorithm_utils.hpp](./algorithm_utils.hpp)

### Function `cal_distance`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
inline float cal_distance(float x1, float y1, float x2, float y2)
```

- 参数:

  **x1, y1** – 点1坐标

  **x2, y2** – 点2坐标

- 返回:

  曼哈顿距离 (|x2-x1| + |y2-y1|)

### Function `abs_mean`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
inline T abs_mean(T a1, T a2)
```

- 说明:
  计算两个数的平均值的绝对值。

### Function `cal_dis`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
inline float cal_dis(T x1, T y1, T x2, T y2)
```

- 参数:

  **x1, y1** – 点1坐标

  **x2, y2** – 点2坐标

- 返回:

  欧几里得距离

### Function `sigmoid`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

提供了多种重载，用于对标量、向量或数组片段进行sigmoid计算。

```cpp
// 1
template <typename T> static inline float sigmoid(T const &x)
// 2
template <typename T> static inline std::vector<float> sigmoid(const std::vector<T> &x)
//3
template <typename T> static inline std::vector<float> sigmoid(const T *x, int startptr, int calcnum)
```

- 说明:

  计算Sigmoid激活函数值。

### Function `arcSigmoid`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
static inline float arcSigmoid(T const &x)
```

- 说明:
  计算 Sigmoid 的反函数 (Logit)。

### Function `sumExp`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
static inline float sumExp(const T *x, int startptr, int calcnum)
```

- 说明:
  计算数组片段的指数和。

### Function `softmax`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
static inline std::vector<float> softmax(const T *x, int startptr, int calcnum)
```

- 说明:

  计算Softmax。

### Function `dfl`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T, typename D>
static inline std::vector<float> dfl(const T *x, D alpha, int startptr, int info_length)
```

- 说明:
  Distribution Focal Loss 计算辅助函数。

### Function `checkBorder`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
static inline float checkBorder(T const &x, T const &a, T const &b)
```

- 参数:

  **x** – 输入值

  **a** – 下界

  **b** – 上界

- 返回:

  返回截断在[a, b]范围内的值。

### Function `topK`

Defined in [algorithm_utils.hpp](./algorithm_utils.hpp)

```cpp
template <typename T>
static inline std::vector<std::pair<int, T>> topK(std::vector<T> &v, int k)
```

- 参数:

  **v** – 输入向量

  **k** – 前k个

- 返回:

  返回前k大的值及其索引的pair向量。

## [demo_utils.hpp](./demo_utils.hpp)

### Function `getLabelName`

Defined in [demo_utils.hpp](./demo_utils.hpp)

```cpp
inline std::vector<std::string> getLabelName(const std::string &name_path)
```

- 参数:

  **name_path** – names文件路径

- 返回:

  每个index对应的标签名称列表

### Function `getDetPostNormratio`

Defined in [demo_utils.hpp](./demo_utils.hpp)

```cpp
inline std::vector<float> getDetPostNormratio(icraft::xir::Network network)
```

- 参数:

  **network** – 网络对象

- 返回:

  从RuntimeNetwork中获取DetPostNode的量化参数信息

### Function `get_date_timestamp_string`

Defined in [demo_utils.hpp](./demo_utils.hpp)

```cpp
inline std::string get_date_timestamp_string()
```

- 返回:
  当前日期和时间的字符串 (yyyy-mm-dd_HH:MM:SS.mmm)

### Function `is_in_bbox`

Defined in [demo_utils.hpp](./demo_utils.hpp)

```cpp
inline bool is_in_bbox(int x, int y, int x0, int y0, int w, int h)
```

- 说明:
  判断点(x,y)是否在矩形框内

### Function `printout_hex`

Defined in [demo_utils.hpp](./demo_utils.hpp)

```cpp
inline void printout_hex(const uint8_t *data, size_t data_sz, size_t limit = 64)
```

- 说明:
  以十六进制打印数据

## [file_utils.hpp](./file_utils.hpp)

### Function `read_node_urls`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline void read_node_urls(const YAML::Node &node, const std::string &key, std::vector<std::string> &urls)
```

- 说明:
  从YAML节点读取URL列表

### Function `toVector`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline std::vector<std::string> toVector(const std::string &txt_path)
```

- 说明:
  读取文本文件每一行到vector中

### Function `checkDir`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline void checkDir(const std::string path)
```

- 说明:
  检查目录是否存在，不存在则创建

### Function `getFilename`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline std::string getFilename(const std::string &img_path)
```

- 说明:
  从路径获取文件名(不含后缀)

### Function `listFilenames`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline std::vector<std::string> listFilenames(const std::filesystem::path &directory_path)
```

- 说明:
  列出目录下的所有从文件名，并按文件名排序

### Function `getFullFilePathsFromList`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline std::vector<std::string> getFullFilePathsFromList(const std::filesystem::path &directory_path, const std::filesystem::path &txt_fn)
```

- 说明:
  根据列表文件获取完整的图片路径列表

### Function `progress`

Defined in [file_utils.hpp](./file_utils.hpp)

```cpp
inline void progress(int index, int total)
```

- 说明:
  打印进度条

## [fps_calculator.hpp](./fps_calculator.hpp)

### Class `FPSCalculator`

Defined in [fps_calculator.hpp](./fps_calculator.hpp)

计算帧率的辅助类。

- 成员函数:
  - `void tick()`: 每处理一帧调用一次
  - `float getFPS() const`: 获取最近计算的FPS值

## [log_utils.hpp](./log_utils.hpp)

### Logging Macros

Defined in [log_utils.hpp](./log_utils.hpp)

封装了spdlog的宏。

- `LOG_DEBUG(pre, fmt, ...)`
- `LOG_INFO(pre, fmt, ...)`
- `LOG_WARN(pre, fmt, ...)`
- `LOG_ERROR(pre, fmt, ...)`

## [pcie_arm_utils.hpp](./pcie_arm_utils.hpp)

### Function `initHostIn`

Defined in [pcie_arm_utils.hpp](./pcie_arm_utils.hpp)

```cpp
template <typename DeviceType>
inline std::vector<icraft::xrt::MemChunk> initHostIn(DeviceType device, unsigned int buffer_num, unsigned int buffer_size)
```

- 说明:
  初始化ARM端，等待Host连接，并分配plddr内存块

### Function `initHostIn_psddr`

Defined in [pcie_arm_utils.hpp](./pcie_arm_utils.hpp)

```cpp
template <typename DeviceType>
inline std::vector<icraft::xrt::MemChunk> initHostIn_psddr(DeviceType device, unsigned int buffer_num, unsigned int buffer_size)
```

- 说明:
  初始化ARM端，等待Host连接，并分配udma (psddr)内存块

## [vis_helper.hpp](./vis_helper.hpp)

### Class `DisplayRange`

Defined in [vis_helper.hpp](./vis_helper.hpp)

封装OpenCV mat的一个矩形子区域。

- 构造函数:
  `DisplayRange(int startrow, int endrow, int startcol, int endcol, const cv::Mat &mat)`

### Class `ProgressPrinter`

Defined in [vis_helper.hpp](./vis_helper.hpp)

线程安全的控制台多行进度条打印类。

### Function `classColorYUV`

Defined in [vis_helper.hpp](./vis_helper.hpp)

```cpp
inline YUVColor classColorYUV(int id)
```

- 说明:
  根据class ID获取预定义的YUV颜色

### Function `BGR2YUV`

Defined in [vis_helper.hpp](./vis_helper.hpp)

```cpp
inline YUVColor BGR2YUV(const cv::Scalar &bgr)
```

- 参数:
  **bgr** – OpenCV Scalar (BGR)

- 返回:
  对应的 YUVColor 结构体

- 说明:
  将 BGR 颜色转换为 YUV 颜色。

### Function drawRectangleNV21

Defined in [vis_helper.hpp](./vis_helper.hpp)

```cpp
inline void drawRectangleNV21(cv::Mat &nv21_mat, const cv::Rect &rect, const YUVColor &color, int thickness)
```

- 说明:
  直接在NV21格式的Mat上绘制矩形框

### Function `draw_marker`

Defined in [demo_utils.hpp](./demo_utils.hpp)

```cpp
inline void draw_marker(cv::Mat &input_img, int marker_x, int marker_y, int marker_sz, int thickness, cv::Scalar color)
```

- 参数:
  **input_img** – 输入图像
  **marker_x/y** – 标记中心坐标
  **marker_sz** – 标记尺寸
  **thickness** – 线条粗细
  **color** – 颜色

- 说明:
  在图像指定位置绘制十字标记。