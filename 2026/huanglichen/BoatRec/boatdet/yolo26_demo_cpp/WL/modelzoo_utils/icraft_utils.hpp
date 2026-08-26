#pragma once

// mzu includes
#include "algorithm_utils.hpp"
#include "et_device.hpp"
#include "file_utils.hpp"
#include "demo_utils.hpp"
#include "log_utils.hpp"

// icraft includes
#include <icraft-xrt/core/session.h>
#include <icraft-xrt/dev/host_device.h>
#include <icraft-xrt/dev/wl170_device.h>
#include <icraft-backends/hostbackend/utils.h>
#include <icraft-backends/hostbackend/backend.h>
#include <icraft-backends/wl170backend/wl170backend.hpp>
#include "icraft-xir/serialize/json.h"
#include "icraft-xir/ops/align_axis.h"
#include "icraft-xir/ops/prune_axis.h"
#include "icraft-xir/ops/cast.h"
#include <icraft-backends/hostbackend/cuda/device.h>

#include <opencv2/opencv.hpp>
#include <fstream>
#include <regex>

std::map<std::string, std::string> STAGE = {
	{"p", "parsed"},
	{"o", "optimized"},
	{"q", "quantized"},
	{"a", "adapted"},
	//{"g", "WL"},
};

std::map<std::string, std::map<std::string, std::string>> BACKEND = {
	{
		"wl170",
		{
			{"jr_suffix", "WL"},
			{"device", "wl170"}
		}
	},
};

std::set<int> ClusterID_POOL = {0, 1};

struct FPAIConfig
{
	std::string device_url = "axi://wl170";									 // wl170设备URL
	bool speed_mode = false;												 // 是否开启极速模式
	bool compress_ftmp = false;												 // 是否压缩ftmp
	bool mmu_mode = true;													 // 是否开启MMU模式
	int ocm_option = -1;													 // OCM选项
	std::string run_backend = "wl170";										 // 运行后端，wl170
	bool enable_profile = false;											 // 是否启用性能分析
};

inline void calctime_detail(const std::string &runBackend, icraft::xrt::Session &session)
{
	if (BACKEND.find(runBackend) == BACKEND.end())
	{
		std::cout << fmt::format("Not Supported Backend: {}", runBackend) << std::endl;
		return;
	}

	//--- Get network name and setup output file
	auto network_name = session->network_view.network()->name;
	checkDir("./logs/");
	std::string filePath = "./logs/" + network_name + "_time" + ".txt";
	std::ofstream ofs(filePath.c_str(), std::ios::out);

	float total_hard_time = 0;
	float total_time = 0;
	float total_memcpy_time = 0;
	float total_other_time = 0;
	float hardop_total_time = 0;
	float hardop_hard_time = 0;
	float hardop_memcpy_time = 0;
	float io_total_time = 0;
	float io_memcpytime = 0;
	float io_hardtime = 0;
	float io_othertime = 0;
	float io_process_time = 0;

	bool imk_on = false;
	bool post_on = false;

	float out_cast_time = 0;
	float icore_in_time = 0;
	float icore_out_time = 0;
	float icore_time = 0;
	float cpu_time = 0;
	float customop_total_time = 0;
	float customop_hard_time = 0;
	std::string in_fpgaop = "cdma";
	std::string out_fpgaop = "cdma";
	std::string icore_fpgaop = "npu";
	std::string cpu_op = "Null";
	std::vector<std::tuple<std::string, float, float>> customops;
	std::map<std::string, float> customop_total_times;
	std::map<std::string, float> customop_hard_times;

	auto result = session.timeProfileResults();

	if (runBackend == "wl170")
	{
		for (auto&& [op_id, time] : result) {
			// time1: total_time, time2: memcpy_time, time3: hard_time, time4: other_time
			auto&& op = session->network_view.getOpById(op_id);
			auto&& [time1, time2, time3, time4] = time;
			auto&& op_name = op->name;
			auto&& op_typekey = op->typeKey();
			bool is_io_process = (op.getTag("io_process") == icraft::xir::Bool(true));

			if (!time1) time1 = time2 + time3 + time4;
			ofs << fmt::format("op_id: {}, op_type: {}, op_name: {}, total_time: {}, memcpy_time: {}, hard_time: {}, other_time: {}, is_io_process: {}\n", op_id, op_typekey, op->name, time1, time2, time3, time4, is_io_process);

			total_time += time1;
			total_memcpy_time += time2;
			total_hard_time += time3;
			total_other_time += time4;

			if (op_typekey == "icraft::xir::HardOpNode")
			{
				// is_io_process Op
				if (is_io_process)
				{
					io_total_time += time1;
					io_memcpytime += time2;
					io_hardtime += time3;
					io_othertime += time4;
				}
				// HardOp
				else
				{
					hardop_total_time += time1;
					hardop_memcpy_time += time2;
					hardop_hard_time += time3;
				}
			}
		}
		cpu_time = total_time - hardop_total_time - io_total_time;
		hardop_total_time -= hardop_memcpy_time;
	}
	if (cpu_time < 0)
		cpu_time = 0;
	icore_time += hardop_total_time;
	io_process_time = io_total_time - io_memcpytime;

	std::string splitstr = "******************************************************\n";
	std::vector<std::string> summary = { splitstr };
	summary.emplace_back(fmt::format("Total_TotalTime: {} ms, Total_MemcpyTime: {} ms, Total_HardTime: {} ms, Total_OtherTime: {} ms\n", total_time, total_memcpy_time, total_hard_time, total_other_time));
	summary.emplace_back(fmt::format("Hardop_TotalTime: {} ms, Hardop_MemcpyTime: {} ms, Hardop_HardTime: {} ms\n", hardop_total_time, hardop_memcpy_time, hardop_hard_time));
	summary.emplace_back(fmt::format("IO_TotalTime: {} ms, IO_MemcpyTime: {} ms, IO_HardTime: {} ms, IO_OtherTime: {} ms\n", io_total_time, io_memcpytime, io_hardtime, io_othertime));
	for (const auto& pair : customop_total_times)
	{
		summary.emplace_back(fmt::format("Customop: {}, TotalTime: {} ms, HardTime : {} ms\n", pair.first.substr(0, pair.first.size() - 4).substr(10), pair.second, customop_hard_times[pair.first]));
	}
	summary.emplace_back(splitstr);
	summary.emplace_back("统计分析结果如下(The analysis results are as follows):\n");
	summary.emplace_back(fmt::format("数据传入耗时(Data input time consumption):\nTime(ms): {}     Device: {}\n", io_memcpytime, in_fpgaop));
	summary.emplace_back(fmt::format("数据处理耗时(Data process time consumption):\nTime(ms): {}     Device: {}\n", io_process_time, icore_fpgaop));
	summary.emplace_back(fmt::format("网络主体耗时(Network Backbone time consumption):\nTime(ms): {}     Device: {}\n", icore_time, icore_fpgaop));
	summary.emplace_back(fmt::format("cpu算子耗时(CPU operator time consumption):\nTime(ms): {}     Device: {}\n", cpu_time, cpu_op));
	summary.emplace_back(splitstr);
	summary.emplace_back("PSIN模式主要用于部署调试、对齐精度等，用户仅需关注以下耗时即可，其余耗时大部分情况可以在实际的数据通路中被优化：\n");
	summary.emplace_back(fmt::format("Hardop_HardTime(ms): {}\n", hardop_hard_time));
	for (const auto& pair : customop_total_times)
	{
		if (pair.first.find("ImageMake") != std::string::npos) continue;
		summary.emplace_back(fmt::format("Customop: {}, HardTime(ms): {}\n", pair.first.substr(0, pair.first.size() - 4).substr(10), customop_hard_times[pair.first]));
	}
	summary.emplace_back(splitstr);
	for (auto& line : summary)
	{
		ofs << line;
		std::cout << line;
	}

	ofs.close();

	std::cout << "For details about running time meassage of the network, check the " + network_name + "_time" + ".txt" + " in path: " + "./logs/" << std::endl;

};

inline void checkBackend(const std::string &run_backend, const std::string &func_name="checkBackend")
{
	if ((run_backend.compare("host") != 0) && (BACKEND.find(run_backend) == BACKEND.end()))
	{
		ICRAFT_LOG(EXCEPT).append(
			"The backend parameter passed to function {} <{}> is not supported.\
			\nEnsure that you pass the correct backend parameter!\
			\nThe backend parameter can only accept host and wl170!",
			func_name, run_backend
		);
	}
#if defined(__aarch64__) || defined(_M_ARM64)
	if (run_backend.compare("host") == 0)
	{
		ICRAFT_LOG(EXCEPT).append(
			"The backend parameter passed to function {} <{}> is not supported.\
			\nEnsure that you pass the correct backend parameter!\
			\nThe backend parameter can only accept wl170!",
			func_name, run_backend
		);
	}
#endif
}

inline icraft::xrt::Device openDevice(const std::string &run_backend, const std::string &ip,
									  bool mmu_Mode = true, bool cuda_Mode = false,
									  std::string npu_addr = "0x40000000", std::string dma_addr = "0x80000000")
{
	checkBackend(run_backend, "openDevice");
	
	std::string URL_PATH;
	icraft::xrt::Device device;
#if defined(_WIN32) || defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
	URL_PATH = "socket://" + BACKEND[run_backend]["device"] + "@" + ip + ":9981";
#elif defined(__aarch64__) || defined(_M_ARM64)
	URL_PATH = "axi://" + BACKEND[run_backend]["device"];
#else
	ICRAFT_LOG(EXCEPT).append("Unknown architecture.");
#endif

	if (run_backend.compare("host") == 0)
	{
		if (cuda_Mode)
		{
			return icraft::xrt::CudaDevice::Default();
		}
		return icraft::xrt::HostDevice::Default();
	}
	device = icraft::xrt::Device::Open(URL_PATH);
	return device;
}

inline std::pair<std::string, std::string> getJrPath(const std::string &run_backend, const std::string &folderPath, std::string &targetFileName)
{
	checkBackend(run_backend, "getJrPath");

	if (BACKEND.find(run_backend) != BACKEND.end())
	{
		targetFileName = BACKEND[run_backend]["jr_suffix"] + ".json";
	}
	else if (run_backend.compare("host") == 0)
	{
		if (targetFileName.compare("g") == 0)
		{
			for (const auto& entry : std::filesystem::directory_iterator(folderPath))
			{
				for (auto backend = BACKEND.begin(); backend != BACKEND.end(); ++backend)
				{
					if (entry.is_regular_file() && entry.path().filename().string().find(backend->second["jr_suffix"] + ".json") != std::string::npos)
					{
						spdlog::info("Found model file at:{}", entry.path().string());
						std::regex regex_last("json(?!.*json)", std::regex::icase);
						std::string raw_path = std::regex_replace(entry.path().string(), regex_last, "raw");
						return { entry.path().string(), raw_path };
					}
				}
			}
		}
		else if (STAGE.count(targetFileName) > 0)
		{
			targetFileName = STAGE[targetFileName] + ".json";
		}
		else
			throw std::runtime_error("imodel stage not right, please check yaml:imodel:stage");
	}

	if (targetFileName.find(".json") == std::string::npos)
	{
		throw std::runtime_error("imodel path not right, please check yaml:imodel:dir");
	}
	else
	{
		for (const auto& entry : std::filesystem::directory_iterator(folderPath))
		{
			if (entry.is_regular_file() && entry.path().filename().string().find(targetFileName) != std::string::npos)
			{
				spdlog::info("Found model file at:{}", entry.path().string());

				std::regex regex_last("json(?!.*json)", std::regex::icase);
				std::string raw_path = std::regex_replace(entry.path().string(), regex_last, "raw");

				return { entry.path().string(), raw_path };
			}
		}
	}
}

inline void apply_instruction_errata_patch(icraft::xir::Network & network) {
	// 与 run_llm 保持一致的指令补丁逻辑。
	// 如果目标不是对应的核类型，就直接跳过。
	if (network->ai_target != icraft::xir::ZhugeTarget(icraft::xir::ZhugeTarget::ZhugeTarget::Core::ZG330)) {
		return;
	}

	for (auto& op : network->ops) {
		if (!op.is<icraft::xir::HardOp>()) {
			continue;
		}

		auto hardop = op.cast<icraft::xir::HardOp>();
		auto instr = hardop->instr[0].data<uint64_t>();
		const auto instr_count = hardop->instr[0].tensorType()->shape[0];
		for (int64_t index = 0; index < instr_count; ++index) {
			const auto mask = instr[index] & 0xff00000f;
			if (mask == 0x05000001 || mask == 0x05000000) {
				instr[index] &= 0x0000ffffffffffffULL;
			}
		}
	}
}

inline icraft::xir::Network loadNetwork(const std::string &JSON_PATH, const std::string &RAW_PATH)
{
	icraft::xir::Network network = icraft::xir::Network::CreateFromJsonFile(JSON_PATH);
	network.lazyLoadParamsFromFile(RAW_PATH);
	apply_instruction_errata_patch(network);
	return network;
}

inline icraft::xrt::Session initSession(const std::string &run_backend, const icraft::xrt::NetworkView &network, icraft::xrt::Device &device,
										int ocm_option = -1, bool mmuMode = true, bool open_speedmode = true, bool open_compressFtmp = true,
										int icluster_id = 0)
{
	checkBackend(run_backend, "initSession");

	icraft::xrt::Session session;
	if (run_backend.compare("host") == 0)
	{
		session = icraft::xrt::Session::Create<icraft::xrt::HostBackend>(network, {device});
	}
	else if (run_backend.compare("wl170") == 0)
	{
		if (ClusterID_POOL.find(icluster_id) == ClusterID_POOL.end())
		{
			ICRAFT_LOG(EXCEPT).append(
				"The icluster_id parameter passed to initSession <{}> is not supported.\
				\nEnsure that you pass the correct icluster_id parameter!\
				\nThe icluster_id parameter can only accept 0 and 1!",
				icluster_id
			);
		}
		session = icraft::xrt::Session::Create<icraft::xrt::WL170Backend, icraft::xrt::HostBackend>(network, { {device.cast<icraft::xrt::wl170::WL170Device>().getICluster(icluster_id)}, {icraft::xrt::HostDevice::Default()} });
		auto wl_backend = session->backends[0].cast<icraft::xrt::WL170Backend>();
		if (!open_compressFtmp)
			wl_backend.disableEtmOptimize();
		if (!open_speedmode)
			wl_backend.disableMergeHardop();
		if ((ocm_option != -1) && (ocm_option != 1))
		{
			if (ocm_option == 2)
			{
				wl_backend.setOcmOptMethod(icraft::xrt::OcmOptMethod::Option2);
			}
			else if (ocm_option == 3)
			{
				wl_backend.setOcmOptMethod(icraft::xrt::OcmOptMethod::Option3);
			}
			else if (ocm_option == 4)
			{
				wl_backend.setOcmOptMethod(icraft::xrt::OcmOptMethod::Option4);
			}
			else if (ocm_option == 0)
			{
				wl_backend.disableOcmOptimize();
			}
			else
			{
				ICRAFT_LOG(EXCEPT).append(
					"The ocm_option parameter passed to initSession <{}> is not supported.\
					\nEnsure that you pass the correct ocm_option parameter!\
					\nThe ocm_option parameter can only accept 0, 1, 2, 3, 4 and -1!",
					ocm_option
				);
			}
		}
	}
	return session;
}

icraft::xrt::Tensor CvMat2Tensor(cv::Mat &img, const icraft::xrt::Network &network)
{
	// 获取输入的value 用于从 cvMat 构造 输入tensor
	auto input_value = network.inputs()[0];
	// 将cv Mat构造为输入网络的TENSOR
	auto out_dtype = input_value.tensorType().clone();
	auto out_stor_type = out_dtype->element_dtype.getStorageType();
	cv::Mat converted;
	if (out_stor_type.is<icraft::xir::FloatType>())
	{
		auto float_stor_type = out_stor_type.cast<icraft::xir::FloatType>();
		if (float_stor_type.isFP32())
		{
			img.convertTo(converted, CV_32F);
		}
		else if (float_stor_type.isFP16())
		{
			img.convertTo(converted, CV_16F);
		}
		else
		{
			ICRAFT_LOG(EXCEPT).append("[Error in HostBackend Image2Tensor] DataType {} is not supported.", float_stor_type->typeKey());
		}
	}
	else if (out_stor_type.is<icraft::xir::IntegerType>())
	{
		auto int_stor_type = out_stor_type.cast<icraft::xir::IntegerType>();
		if (int_stor_type.isSInt8())
		{
			img.convertTo(converted, CV_8S);
		}
		else if (int_stor_type.isUInt8())
		{
			img.convertTo(converted, CV_8U);
		}
		else if (int_stor_type.isSInt16())
		{
			img.convertTo(converted, CV_16S);
		}
		else if (int_stor_type.isUInt16())
		{
			img.convertTo(converted, CV_16U);
		}
		else if (int_stor_type.isSInt32())
		{
			img.convertTo(converted, CV_32S);
		}
		else
		{
			ICRAFT_LOG(EXCEPT).append("[Error in HostBackend Image2Tensor] DataType {} is not supported.", int_stor_type->typeKey());
		}
	}
	else
	{
		ICRAFT_LOG(EXCEPT).append("[Error in HostBackend Image2Tensor] DataType {} is not supported.", out_stor_type->typeKey());
	}
	int H = converted.rows;
	int W = converted.cols;
	int C = converted.channels();
	// define output tensor
	std::vector<int64_t> output_shape = {1, H, W, C};
	auto tensor_layout = icraft::xir::Layout("NHWC");
	out_dtype.setShape(output_shape);
	icraft::xrt::Tensor img_tensor = icraft::xrt::Tensor(out_dtype).mallocOn(icraft::xrt::HostDevice::MemRegion());
	// data copy
	memcpy(img_tensor.data().cptr(), converted.data, H * W * C * out_dtype->element_dtype.bits() / 8);
	// std::cout << "CvMat2Tensor: " << img_tensor.dtype()->shape << std::endl;
	return img_tensor;
}

template <typename T>
icraft::xrt::Tensor data2Tensor(const T *input_data, const icraft::xir::Value &input_value)
{
	icraft::xir::TensorType out_dtype;
	if (input_value.tensorType()->shape[0] == -1)
	{
		out_dtype = input_value.getUsesOp()[0]->outputs[0].tensorType().clone();
	}
	else
	{
		out_dtype = input_value.tensorType().clone();
	}
	auto size = out_dtype.numElements();

	auto out_stor_type = out_dtype->element_dtype.getStorageType();

	auto ele_dtype = out_dtype->element_dtype;

	if (ele_dtype.isUInt(8))
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(uint8_t)); // malloc on host
		auto trans_data = (uint8_t *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (uint8_t)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else if (ele_dtype.isSInt(8))
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(int8_t)); // malloc on host
		auto trans_data = (int8_t *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (int8_t)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else if (ele_dtype.isUInt(16))
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(uint16_t)); // malloc on host
		auto trans_data = (uint16_t *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (uint16_t)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else if (ele_dtype.isSInt(16))
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(int16_t)); // malloc on host
		auto trans_data = (int16_t *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (int16_t)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else if (ele_dtype.isUInt(32))
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(uint32_t)); // malloc on host
		auto trans_data = (uint32_t *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (uint32_t)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else if (ele_dtype.isSInt(32))
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(int32_t)); // malloc on host
		auto trans_data = (int32_t *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (int32_t)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else if (ele_dtype.isFP32())
	{
		auto param_chunk = icraft::xrt::HostDevice::MemRegion().malloc(size * sizeof(float)); // malloc on host
		auto trans_data = (float *)param_chunk->begin.cptr();
		std::transform((T *)input_data, (T *)input_data + size, trans_data, [](auto d)
					   { return (float)d; });
		return icraft::xrt::Tensor(out_dtype, param_chunk);
	}
	else
	{
		ICRAFT_LOG(EXCEPT).append("[Error in HostBackend::GenTensorFromParams] Unsupported dtype {}, can't convert to torch tensor.", ele_dtype->typeKey());
		return icraft::xrt::Tensor{};
	}
}

inline std::vector<icraft::xrt::Tensor> icraftRun(icraft::xrt::Session &session, const std::vector<icraft::xrt::Tensor> &input_tensors)
{
	auto output_tensors = session.forward(input_tensors);
	for (auto& output_tensor : output_tensors) {
		if (!output_tensor.waitForReady(std::chrono::seconds(100))) {
			throw std::runtime_error("timeout while waiting for output tensor ready");
		}
	}
	return output_tensors;
}

/*----------- Debug Helpers ---------------*/
inline void dumpOutputFtmp(icraft::xir::NetworkView network, std::vector<icraft::xrt::Tensor> &output_tensors, std::string dump_format, std::string log_path)
{
	std::filesystem::create_directories(log_path);
	auto network_outp = network.outputs();
	// dump网络output算子的输出
	for (uint64_t i = 0; i < network_outp.size(); i++)
	{
		// auto os = std::ofstream(fmt::format("{}//{}.ftmp", log_path, network_outp[i]->v_id), std::ios::binary);//存实际ftmp_id
		auto os = std::ofstream(fmt::format("{}//{}.ftmp", log_path, std::to_string(i)), std::ios::binary); // 存输出顺序
		output_tensors[i].dump(os, dump_format);
	}
};

// 删除输出分支上的指定pattern（cast-Pruneaxis），并按照原来output算子的ifm顺序重新连接hardop <->output；
// idx_list用于指定分支删除cast&Pruneaxis算子，例如：指定第1条分支删除cast&Pruneaxis算子：idx_list={0}
void removeOutputCast(icraft::xir::Network &network, bool mmu, icraft::xir::Array<int> idx_list = {})
{
	auto codegen_speedmode = Downcast<icraft::xir::Bool>(network.getTag("speedmode").value())->value;
	auto codegen_compressFtmp = Downcast<icraft::xir::Bool>(network.getTag("compressFtmp").value())->value;
	bool codegen_mmu = codegen_speedmode || codegen_compressFtmp;
	if (codegen_mmu || mmu)
		ICRAFT_LOG(WARNING).append("Open MMU will lock the order of ftmp's physical address, and this may affect network connection!");

	auto cast_p = icraft::xir::IsOp<icraft::xir::Cast>();
	auto prune_axis_p = icraft::xir::IsOp<icraft::xir::PruneAxis>(cast_p[0]).setConstraint([](const icraft::xir::Operation &op)
																			  {
		auto prune_axis = op.cast<icraft::xir::PruneAxis>();
		PATTERN_REQUIRE(prune_axis.consumers().size() == 1);
		PATTERN_REQUIRE(prune_axis.consumers()[0]->isInstance<icraft::xir::OutputNode>());
		return true; });

	network.rewrite(prune_axis_p, [&](icraft::xrt::Network &network, const icraft::xir::MatchGroup &result)
					{
						auto cast = result.at(cast_p);
						auto prune_axis = result.at(prune_axis_p);
						auto output = prune_axis.consumers()[0];
						auto hardop = cast.producers()[0];

						// 匹配到的是第index个输出
						auto index = output.getInputIndex(prune_axis[0]);
						auto it = std::find(idx_list.begin(), idx_list.end(), *(index.begin()));

						// 可指定分支，去除cast&Pruneaxis；若不输入指定分支，默认去除所有分支的cast&Pruneaxis
						if (it != idx_list.end() || idx_list.size() == 0)
						{
							// 重新连接hardop<->output
							output.setInput(*(index.begin()), hardop[0]);
							// 删除Cast&PruneAxis
							network.removeOpById(prune_axis->op_id);
							network.removeOpById(cast->op_id);
						}
						// 如果不是指定分支，不做任何操作
						else
						{
							network.rewriter().Continue();
						} });
}
// 删除输入分支上的指定pattern（Alignaxis-cast）, 并按照原来input算子的ofm顺序重新连接hardop<->input；
// idx_list用于指定分支删除Alignaxis&cast算子，例如：指定第1条分支删除Alignaxis&cast算子：idx_list={0}
void removeInputCast(icraft::xir::Network &network, bool mmu, icraft::xir::Array<int> idx_list = {})
{
	auto codegen_speedmode = Downcast<icraft::xir::Bool>(network.getTag("speedmode").value())->value;
	auto codegen_compressFtmp = Downcast<icraft::xir::Bool>(network.getTag("compressFtmp").value())->value;
	bool codegen_mmu = codegen_speedmode || codegen_compressFtmp;
	if (codegen_mmu || mmu)
		ICRAFT_LOG(WARNING).append("Open MMU will lock the order of ftmp's physical address, and this may affect network connection!");

	auto input_p = icraft::xir::IsOp<icraft::xir::Input>();
	auto align_axis_p = icraft::xir::IsOp<icraft::xir::AlignAxis>(input_p);
	auto cast_p = icraft::xir::IsOp<icraft::xir::Cast>(align_axis_p[0]);

	network.rewrite(cast_p, [&](icraft::xrt::Network &network, const icraft::xir::MatchGroup &result)
					{
						auto input = result.at(input_p);
						auto align_axis = result.at(align_axis_p);
						auto cast = result.at(cast_p);

						// 提前记录下来cast要连接到地方
						auto cast_uses_info = network.getUsesInfoExceptMatch(cast[0], result);

						// 匹配到的是第index个输出
						auto index = align_axis->inputs[0].index();
						auto it = std::find(idx_list.begin(), idx_list.end(), index);

						// 可指定分支，去除cast&Alignaxis；若不输入指定分支，默认去除所有分支的cast&Alignaxis
						if (it != idx_list.end() || idx_list.size() == 0)
						{
							// 拷贝一份cast的输入，重置一下v_id，防止重名
							auto new_value = cast[0].clone(-1).setId(-1);
							// 重新连接hardop<->input
							input.setOutput(index, new_value);
							// 删除AlignAxis&Cast
							network.removeOpById(align_axis->op_id);
							network.removeOpById(cast->op_id);

							// Input的第index个输入连接到原来cast要连接到地方
							network.connect(input[index], cast_uses_info);
						}
						// 如果不是指定分支，不做任何操作
						else
						{
							network.rewriter().Continue();
						} });
}
std::vector<float> getOutputNormratio(icraft::xir::NetworkView network)
{
	auto network_outp = network.outputs();
	std::vector<float> ret;
	ret.reserve(network_outp.size());
	for (auto &&value : network_outp)
	{
		try
		{
			auto b = value->dtype.getNormratio().value();
			ret.emplace_back(b[0]);
		}
		catch (const std::exception &e)
		{
			std::cout << "the output of network/networkview have no Normratio" << std::endl;
		}
	}
	return ret;
}

std::vector<float> getInputNormratio(icraft::xir::NetworkView network)
{
	auto network_inp = network.inputs();
	std::vector<float> ret;
	ret.reserve(network_inp.size());
	for (auto &&value : network_inp)
	{
		try
		{
			auto b = value->dtype.getNormratio().value();
			ret.emplace_back(b[0]);
		}
		catch (const std::exception &e)
		{
			std::cout << "the input of network/networkview have no Normratio" << std::endl;
		}
	}
	return ret;
}