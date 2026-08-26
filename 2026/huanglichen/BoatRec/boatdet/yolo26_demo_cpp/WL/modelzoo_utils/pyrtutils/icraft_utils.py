import icraft
from icraft import xir,xrt,host_backend,wl170backend
from icraft.host_backend import *
from icraft.wl170backend import *
import os
import platform
from .utils import *
import logging
import re
import sys
from typing import List
import datetime
STAGE = {
    "p": "parsed",
    "o": "optimized",
    "q": "quantized",
    "a": "adapted",
    # "g": "WL",
}

BACKEND = {
    "wl170": {
        "jr_suffix": "WL",
        "device": "wl170"
    }
}

ClusterID_POOL = {0, 1}

def checkBackend(run_backend):
    if (run_backend != "host") and (run_backend not in BACKEND):
        backends = sorted(list(BACKEND.keys()))
        valid_backends = f"{', '.join(['host']+backends[:-1])} and {backends[-1]}"
        raise Exception(f"The backend parameter passed to function openDevice <{run_backend}> is not supported.\
            \nEnsure that you pass the correct backend parameter!\
            \nThe backend parameter can only accept {valid_backends}!")

def getJrPath(folderPath,stage,run_backend):
    current_os = platform.system()
    current_arch = platform.machine()
    is_dev_env = current_os == "Windows" or (current_os == "Linux" and "x86" in current_arch)

    logging.info(f"Searching for model file in {folderPath}...")

    if run_backend in BACKEND:
        stage = f"{BACKEND[run_backend]['jr_suffix']}.json"
    elif run_backend == "host":
        # if is_dev_env:
        if stage == "g":
            for entry in os.scandir(folderPath):
                if entry.is_file() and (".json" in entry.name):
                    for backend in BACKEND:
                        if f"{BACKEND[backend]['jr_suffix']}.json" in entry.name:
                            logging.info(f"Found model file at {entry.path}")
                            raw_path = re.sub("json$", "raw", entry.path)
                            mprint("Info:imodel file found at:‌{}".format(entry.path), VERBOSE, 0)
                            return entry.path, raw_path
            raise RuntimeError("imodel path not right, please check yaml:imodel:dir")
        elif stage in STAGE:
            stage = f"{STAGE[stage]}.json"
        else:
            raise RuntimeError("imodel stage not right, please check yaml:imodel:dir")
        # For aarch64 linux with host backend, it will fall through to the file search loop
    else:
        checkBackend(run_backend)  # Recovers the check for invalid backends

    for entry in os.scandir(folderPath):
        if entry.is_file() and stage in entry.name:
            logging.info(f"Found model file at {entry.path}")
            raw_path = re.sub("json$", "raw", entry.path)
            mprint("Info:imodel file found at:‌{}".format(entry.path), VERBOSE, 0)     
            return entry.path, raw_path

    raise RuntimeError("imodel path not right, please check yaml:imodel:dir")


def loadNetwork(JSON_PATH, RAW_PATH):
    network = icraft.xir.Network.CreateFromJsonFile(JSON_PATH)
    network.lazyLoadParamsFromFile(RAW_PATH)
    return network


def openDevice(run_backend,ip,mmu_Mode = True,cuda_Mode= False,npu_addr = "0x40000000", dma_addr = "0x80000000"):
    logging.info(f"Opening device for backend {run_backend}...")
    checkBackend(run_backend)
    current_os = platform.system()
    current_arch = platform.machine()
    is_dev_env = current_os == "Windows" or (current_os == "Linux" and "x86" in current_arch)

    # DEVICE_URL = None
    if run_backend == "host":
        if cuda_Mode:
            return host_backend.CudaDevice.Default()
        return xrt.HostDevice.Default()
    elif is_dev_env:  # Windows or x86 Linux
        DEVICE_URL = f"socket://{BACKEND[run_backend]['device']}@{ip}:9981"
    else:  # aarch64 Linux
        DEVICE_URL = f"axi://{BACKEND[run_backend]['device']}"

    device = xrt.Device.Open(DEVICE_URL)
    return device


def initsimSession(network):
    session = xrt.Session.Create( [host_backend.HostBackend],network, [xrt.HostDevice.Default() ])
    return session


def initSession(run_backend, network, device, ocm_option=-1, mmuMode=True, open_speedmode=True, open_compressFtmp=True, icluster_id=0):
    checkBackend(run_backend)
    current_os = platform.system()
    current_arch = platform.machine()
    is_dev_env = current_os == "Windows" or (current_os == "Linux" and "x86" in current_arch)

    if run_backend == "host":
        session = xrt.Session.Create([host_backend.HostBackend], network.view(0), [device])
    elif run_backend == "wl170":
        if icluster_id not in ClusterID_POOL:
            raise Exception(f"The icluster_id parameter passed to initSession <{icluster_id}> is not supported.")
        session = xrt.Session.Create([wl170backend.WL170Backend, host_backend.HostBackend], network.view(0), [xrt.WL170Device(device).getICluster(icluster_id), xrt.HostDevice.Default()])
        wl_backend = wl170backend.WL170Backend(session.backends[0])
        if not open_compressFtmp:
            wl_backend.disableEtmOptimize()
        # if not open_speedmode:
        #     wl_backend.disableMergeHardop()
        if ocm_option == 0:
            wl_backend.disableOcmOptimize()
        elif ocm_option not in [-1, 1]:
            ocm_options = {
                4: OcmOptMethod.Option4,
                3: OcmOptMethod.Option3,
                2: OcmOptMethod.Option2,
                # 1: OcmOptMethod.Option1
            }
            if ocm_option in ocm_options:
                wl_backend.setOcmOptMethod(ocm_options[ocm_option])
            else:
                raise Exception(f"The ocm_option parameter passed to initSession <{ocm_option}> is not supported.")
    
    return session

def icraftRun(session:xrt.Session, input_tensors:List[xrt.Tensor]):
    output = session.forward(input_tensors)
    # 手动搬运toHost
    ps_output_tensors = []
    for item in output:
        while not item.waitForReady(datetime.timedelta(seconds=100)):pass
        ps_output_tensors.append(item.to(xrt.HostDevice.MemRegion()))
    return ps_output_tensors
def numpy2Tensor(input_array: np.ndarray,message) -> icraft.xrt.Tensor:
    if isinstance(message, xir.Network):
        network = message
        if "InputNode" in network.ops[0].typeKey():
            input_value = network.ops[0].outputs[0]
        else:
            input_value = network.ops[0].inputs[0]
    elif(isinstance(message, xir.Value)):
        input_value = message
    else:
        raise Exception("Error:输入numpy2Tensor的参数2类型错误,只能是Network类型和Value")
    input_tensortype = input_value.tensorType()
    # input_dtype = input_value.dtype.getStorageType()
    input_dtype = input_tensortype.getStorageType()
    input_tensortype.setShape(list(input_array.shape))

    if str(input_dtype) == '"@fp(32)"':
        input_array = input_array.astype(np.float32)
    elif str(input_dtype) == '"@fp(16)"':
        input_array = input_array.astype(np.float16)
    elif str(input_dtype) == '"@uint(8)"':
        input_array = input_array.astype(np.uint8)
    elif str(input_dtype) == '"@uint(16)"':
        input_array = input_array.astype(np.uint16)
    elif str(input_dtype) == '"@sint(8)"':
        input_array = input_array.astype(np.int8)
    elif str(input_dtype) == '"@sint(16)"':
        if input_array.dtype==np.uint16: print('warnning : 你的输入是uint16，但我们仅支持int16，现在将其强转成int16输入')
        input_array = input_array.astype(np.int16)
    return  xrt.Tensor(input_array,input_tensortype)

def Tensor2Numpy(outputs: List[icraft.xrt.Tensor]) -> List[np.ndarray]:
    """
    Convert icraft.Tensor to numpy.ndarray.
    """
    # Normalize inputs to list
    if not isinstance(outputs, list):
        outputs = [outputs]
    
    numpy_arrays = []
    for idx, item in enumerate(outputs):
        try:
            chunk = item.chunk()
            byte_size = chunk.byte_size
            offset = item.offset()
            tensor_shape = item.dtype().shape
            input_dtype = item.dtype().element_dtype
            
            if str(input_dtype) == '"@fp(32)"':
                np_dtype = np.float32
            elif str(input_dtype) == '"@fp(16)"':
                np_dtype = np.float16
            elif str(input_dtype) == '"@uint(8)"':
                np_dtype = np.uint8
            elif str(input_dtype) == '"@uint(16)"':
                np_dtype = np.uint16
            elif str(input_dtype) == '"@sint(8)"':
                np_dtype = np.int8
            elif str(input_dtype) == '"@sint(16)"':
                np_dtype = np.int16
            # Create numpy buffer and read tensor data
            py_buffer = np.zeros(shape=tensor_shape, dtype=np_dtype)
            #到时候需要进一步判断 需要转换的数据类型
            item.read(py_buffer, offset, byte_size)
            numpy_arrays.append(py_buffer)
        except Exception as e:
            raise RuntimeError(f"Failed to convert tensor at index {idx}: {e}")
    
    return numpy_arrays

def dumpOutputFtmp(network,output_tensors,dump_format,log_path):
    try :
        if not os.path.exists(log_path):
            os.makedirs(log_path)
    except OSError as e:
        print(f"Error: 无法创建路径 {log_path} - {e}", file=sys.stderr)
        return False
    # dump网络output算子的输出
    network_outp = network.outputs()
    for i in range(len(network_outp)):
        filename =  str(i)+".ftmp"
        with open(os.path.join(log_path, filename),'wb') as f:
            output_tensors[i].dump(f,dump_format)
