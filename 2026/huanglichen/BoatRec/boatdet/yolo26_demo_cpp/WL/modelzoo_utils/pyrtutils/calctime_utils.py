import pandas as pd
import numpy as np
import inspect
from .analyze_time_utils import analyze_time
from .icraft_utils import BACKEND

TIME_TYPES = ["total_time", "memcpy_time", "hard_time", "other_time"]
TIME_TYPES_PRINT = [''.join([x.capitalize() for x in time_type.split('_')]) for time_type in TIME_TYPES]

def run_once(func):
    seen_varnames = set()  # 用于存储已经传入的变量名
    def wrapper(*args, **kwargs):
        # 获取调用栈信息
        frame = inspect.currentframe().f_back
        arg_info = inspect.getargvalues(frame)

        # 提取调用时的变量名
        varnames = []
        for arg in args:
            # 查找当前帧中与 arg 对应的变量名
            for name, value in frame.f_locals.items():
                if value is arg:
                    varnames.append(name)
                    break

        # 将变量名转换为可哈希的键
        varnames_key = tuple(varnames)

        # 如果变量名没有被记录过，则执行函数
        if varnames_key not in seen_varnames:
            result = func(*args, **kwargs)
            seen_varnames.add(varnames_key)  # 记录变量名
            return result
        else:
            # print(f"函数 {func.__name__} 已经为变量名 {varnames_key} 执行过，跳过执行。")
            return None  # 或者返回一个默认值
    return wrapper


def save_time(runBackend, network, times, filenames):
    # times为字典，"op_id":[总时间，传输时间, 硬件时间，余下时间]
    # 保存每一层op_id、op_name、op_type、时间
    headers = ["op_id", "op_name", "op_type"] + TIME_TYPES + ["is_io_process"]

    op_id = sorted(times.keys())
    ori_ops_list = [op.op_id for op in network.ops]
    max_id = max(ori_ops_list) if ori_ops_list else 0
    op_name= np.array([network.getOpById(op_idn).name.replace("Node","")  if op_idn <= max_id else "" for op_idn in op_id])
    op_type = np.array([network.getOpById(op_idn).typeKey().replace("Node","") if op_idn <= max_id else "icraft::xir::HardOp" for op_idn in op_id ])
    list_values  = np.array([list(times[op_idn])  for op_idn in op_id])
       
    for i, time_type in enumerate(TIME_TYPES):
        exec(f"{time_type} = list_values[:, i]")

    if runBackend == 'wl170':
        io_process_list = []
        for op in network.ops:
            if op.getTag("io_process") and bool(op.getTag("io_process")) == True:
                io_process_list.append(op.op_id)
        
        is_io_process = [op_idn in io_process_list for op_idn in op_id]
    local_vars = locals()
    dict_time = {colnm: local_vars[colnm] for colnm in headers}
    pf = pd.DataFrame(dict_time)
    if not np.sum(pf[TIME_TYPES[0]]):
        pf[TIME_TYPES[0]] = sum([pf[x] for x in TIME_TYPES[1:]])
    
    if pd.__version__.startswith('1.'):
        file_path=pd.ExcelWriter(filenames)
        pf.to_excel(file_path, encoding='utf-8', index=False)
        file_path.save()
    elif pd.__version__.startswith('2.'):
        with pd.ExcelWriter(filenames) as file_path: 
            pf.to_excel(file_path, index=False)
    else:
        print('Please use pandas version 1.x or 2.x')
    return pf

def simple_analyze_time(runBackend, net_df: pd.DataFrame):
    cast_thresh = 0.001

    #网络各阶段耗时细则
    IMK, POST, WARP, CENTER_CUSTOMOP = False, False, False, False
    imk_customop_time, post_customop_time, other_customop_time, post_cast_time, cpuop_time = 0, 0, 0, 0, 0
    imk_list, post_list, warp_list, other_customop_list = [], [], [], ['npu']  #device
    
    op_types = ["Hardop", "IO"]
    hardop_details = {op_type: {time_type: 0 for time_type in TIME_TYPES} for op_type in op_types}
    customop_details = {"customop_name":[], TIME_TYPES[0]:[], TIME_TYPES[2]:[]}
    # 统计所有customop的totaltime&hardop_hardtime
    customop_df = net_df[np.array(list(map(lambda x: x.startswith("customop::"), net_df["op_type"])))]
    imk_total_time = 0
    for op_type in customop_df["op_type"].unique():
        op_name = op_type.split("::")[1]
        customop_details["customop_name"].append(op_name)
        for time_type in TIME_TYPES[0::2]:
            op_timen = np.sum(customop_df[customop_df["op_type"] == op_type][time_type])
            customop_details[time_type].append(op_timen)
        if op_name == "ImageMake":
            IMK = True
            imk_list.append(op_name)
            imk_customop_time = customop_details[TIME_TYPES[2]][-1]
            imk_total_time = customop_details[TIME_TYPES[0]][-1]
        elif op_name[-4:] == "Post":
            POST = True
            post_list.append(op_name)
            post_customop_time += customop_details[TIME_TYPES[0]][-1]
        else:
            CENTER_CUSTOMOP = True
            other_customop_list.append(op_name)
    customop_total_time = sum(customop_details[TIME_TYPES[0]])
    if CENTER_CUSTOMOP:
        other_customop_time = customop_total_time - imk_total_time - post_customop_time
    cpuop_time = np.sum(net_df[TIME_TYPES[0]]) - customop_total_time
    # 统计所有hardop的totaltime&hardop_hardtime
    if runBackend == "wl170":
        for io_flag, op_type in enumerate(op_types):
            io_flag = bool(io_flag)
            for time_type in TIME_TYPES:
                hardop_details[op_type][time_type] = np.sum(net_df[(net_df["op_type"] == "icraft::xir::HardOp") * (net_df["is_io_process"] == io_flag)][time_type])
            cpuop_time -= hardop_details[op_type][TIME_TYPES[0]]
    
    # 统计所有hardop的totaltime&hardop_hardtime
    hardop_details["Hardop"][TIME_TYPES[0]] -= hardop_details["Hardop"][TIME_TYPES[1]]

    for op_type in op_types:
        print(", ".join(list(map(lambda x: f'{op_type}_{TIME_TYPES_PRINT[x]}: {hardop_details[op_type][TIME_TYPES[x]]:.4f} ms', range(len(TIME_TYPES))))))
    for i, op_name in enumerate(customop_details["customop_name"]):
        print(f"Customop: {op_name}, {', '.join([f'{TIME_TYPES_PRINT[x]}: {customop_details[TIME_TYPES[x]][i]:.4f} ms' for x in range(0, len(TIME_TYPES), 2)])}")

    # 获取输入icore的时间
    if IMK:
        icore_in_time = imk_customop_time
    else:
        icore_in_time = hardop_details["IO"][TIME_TYPES[1]]
        # 若imk和post list为空，则为cdma搬数
        imk_list.append("cdma")
    if not post_list:
        post_list.append("cdma")
    icore_process_time = hardop_details["IO"][TIME_TYPES[0]] - hardop_details["IO"][TIME_TYPES[1]]
    # 获取icore的时间 
    icore_time = hardop_details["Hardop"][TIME_TYPES[0]]
    # 若网络中间含有其它customop,需加上该硬算子时间    
    if CENTER_CUSTOMOP:
        icore_time = icore_time + other_customop_time
    # 纯CPU端算子耗时
    cpu_time = cpuop_time

    splitstr = "******************************************************"
    print(splitstr)
    # 网络各阶段耗时细则
    print("网络各阶段耗时细则：")
    print(f"数据传入时间(ms): {icore_in_time:.4f}, Device: {imk_list}")
    print(f"数据处理时间(ms): {icore_process_time:.4f}, Device: {other_customop_list}")
    print(f"网络主体时间(Network Backbone)(ms): {icore_time:.4f}, Device: {other_customop_list}")
    # 获取icore输出的时间
    if POST:
        icore_out_time = post_customop_time
        print(f"后处理硬算子时间(ms): {icore_out_time:.4f}, Device: {post_list}")
    # else:
    #     icore_out_time = post_cast_time
    #     cpu_time = cpuop_time - post_cast_time
    # print(f"数据传出时间:{icore_out_time:.4f}, Device:{post_list}")
    print(f"CPU算子耗时(ms): {cpu_time:.4f}, Device: ['null']")
    print(f"{splitstr}\nPSIN模式主要用于部署调试、对齐精度等，用户仅需关注以下耗时即可，其余耗时大部分情况可以在实际的数据通路中被优化：")
    print(f"Hardop_HardTime(ms): {hardop_details['Hardop'][TIME_TYPES[2]]:.4f}")
    for i, op_name in enumerate(customop_details["customop_name"]):
        print(f"Customop: {op_name}, HardTime(ms): {customop_details['hard_time'][i]:.4f}")
    print(splitstr)


@run_once
def calctime_detail(runBackend, sess, network, name=''):
    if runBackend not in BACKEND:
        print('Not supported runBackend passed to the function <calctime_detail>:', runBackend)
        return

    # 计算时间, 输入：session、network、保存表名
    result = sess.timeProfileResults() #获取时间，[总时间，传输时间, 硬件时间，余下时间]
    if not name:
        name = f"{network.name}_time.xlsx"
    net_df = save_time(runBackend, network, result, name)

    # 统计所有op的各项时间
    total_time = [np.sum(net_df[x]) for x in TIME_TYPES]
    print(f"\n{', '.join(list(map(lambda x: f'Total_{TIME_TYPES_PRINT[x]}: {total_time[x]:.4f} ms', range(len(TIME_TYPES)))))}")
    # 耗时分析
    simple_analyze_time(runBackend, net_df)
    print("For details about running time meassage of the network, check the", name)
    