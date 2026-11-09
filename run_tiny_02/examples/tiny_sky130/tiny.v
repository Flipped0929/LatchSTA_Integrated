`timescale 1ns / 1ps

////////////////////////////////////English///////////////////////////////////////
// Company:         Erie
// Engineer:        Erie
//
// Create Date:     2026/10/13 00:00:00
// Design Name:     SKY130 latch timing example
// Module Name:     tiny
// Description:     description/tiny_Design.pdf
// Simulations:     testbench/vivado/2021.1/tiny
//
// Referrences:
// File Format      File Name
// lib              SKY130 HD tt_025C_1v80
//
// Dependencies:
// Module Name      Version
// sky130_fd_sc_hd   external
//
// Version:         V1.0
// Revision Date:   2026/10/13 00:00:00
// History:
// Time             Version     Revised by        Contents
// 2026/10/13       V1.0        Codex             Create SKY130 latch example.
///////////////////////////////////Chinese////////////////////////////////////////
// 版权归属:        Erie
// 开发人员:        Erie
//
// 创建日期:        2026年10月13日
// 设计名称:        SKY130 latch timing example
// 模块名称:        tiny
// 模块说明:        Description/tiny_Design.pdf
// 仿真工程:        TestBench/Vivado/2021.1/tiny
//
// 参考资料:
// 文件格式         文件名称
// lib              SKY130 HD tt_025C_1v80
//
// 依赖文件:
// 模块名称         版本
// sky130_fd_sc_hd   external
//
// 当前版本:        V1.0
// 修订日期:        2026年10月13日
// 修订历史:
// 时间             版本        修订人            修订内容
// 2026年10月13日   V1.0        Codex             创建 SKY130 锁存器小电路。

module tiny
(
	//-----------------全局信号-----------------//
	input i_clk,                                // 三个高电平透明锁存器的共同使能时钟

	//-----------------用户接口-----------------//
	input i_din,                                // 进入第一级锁存器的数据
	output o_dout                               // 末级锁存器经缓冲后的数据
);

	//--------------模块实例化信号--------------//
	//sky130_fd_sc_hd__buf_1--用户接口
	wire input_data;                            // 输入缓冲器输出

	//sky130_fd_sc_hd__dlxtp_1--用户接口
	wire launch_data;                           // 第一级锁存器输出和分支起点

	//sky130_fd_sc_hd__buf_1--用户接口
	wire long_head;                             // 长支路首级缓冲器输出
	wire long_middle;                           // 长支路中间缓冲器输出
	wire long_data;                             // 长支路到达汇合门的数据
	wire short_data;                            // 短支路到达汇合门的数据

	//sky130_fd_sc_hd__and2_1--用户接口
	wire merge_data;                            // 两条支路经与门汇合的数据

	//sky130_fd_sc_hd__dlxtp_1--用户接口
	wire capture_data;                          // 第二级锁存器输出

	//sky130_fd_sc_hd__buf_1--用户接口
	wire tail_data;                             // 第二级到第三级之间的组合路径输出

	//sky130_fd_sc_hd__dlxtp_1--用户接口
	wire result_data;                           // 第三级锁存器输出

	//--------------模块实例化区域--------------//
	// 输入缓冲器提供可追踪的端口到单元路径。
	sky130_fd_sc_hd__buf_1 U_INPUT (
		.A(i_din),                              // 外部输入进入缓冲器
		.X(input_data)                          // 缓冲后的数据驱动首级数据端
	);

	// 高电平期间透明，低电平期间保持已有数据。
	sky130_fd_sc_hd__dlxtp_1 L1 (
		.D(input_data),                         // 接收输入缓冲器输出
		.GATE(i_clk),                           // 用共同使能确定透明窗口
		.Q(launch_data)                         // 输出同时驱动长短两条支路
	);

	// 长支路第一段保留独立的实际单元延迟。
	sky130_fd_sc_hd__buf_1 U_LONG_HEAD (
		.A(launch_data),                        // 取首级锁存器输出
		.X(long_head)                           // 驱动长支路中间级
	);

	// 长支路第二段连接相邻缓冲器。
	sky130_fd_sc_hd__buf_1 U_LONG_MIDDLE (
		.A(long_head),                          // 接收长支路首级输出
		.X(long_middle)                         // 驱动长支路末级
	);

	// 长支路第三段连接汇合门的第一个输入。
	sky130_fd_sc_hd__buf_1 U_LONG_TAIL (
		.A(long_middle),                        // 接收长支路中间级输出
		.X(long_data)                           // 将长支路数据送至与门
	);

	// 短支路仅经过一个缓冲器，便于核对最小延迟。
	sky130_fd_sc_hd__buf_1 U_SHORT (
		.A(launch_data),                        // 与长支路共用同一个源引脚
		.X(short_data)                          // 将短支路数据送至与门
	);

	// 显式实例化汇合门，保留两个真实输入时序弧。
	sky130_fd_sc_hd__and2_1 U_MERGE (
		.A(long_data),                          // 汇合长支路的数据
		.B(short_data),                         // 汇合短支路的数据
		.X(merge_data)                          // 与门输出驱动第二级锁存器
	);

	// 中间锁存器接收汇合后的数据。
	sky130_fd_sc_hd__dlxtp_1 L2 (
		.D(merge_data),                         // 接收两支路的汇合结果
		.GATE(i_clk),                           // 与首级保持相同使能极性
		.Q(capture_data)                        // 输出驱动末段组合路径
	);

	// 末段缓冲器形成第二级到第三级的组合路径。
	sky130_fd_sc_hd__buf_1 U_TAIL (
		.A(capture_data),                       // 将中间级输出送入末段缓冲
		.X(tail_data)                           // 缓冲后的数据驱动末级数据端
	);

	// 末级锁存器提供可追踪的最终存储边界。
	sky130_fd_sc_hd__dlxtp_1 L3 (
		.D(tail_data),                          // 接收末段组合路径输出
		.GATE(i_clk),                           // 使用共同的高电平使能
		.Q(result_data)                         // 输出送至端口缓冲器
	);

	// 输出缓冲器承担外部端口负载。
	sky130_fd_sc_hd__buf_1 U_OUTPUT (
		.A(result_data),                        // 接收末级锁存器保存的数据
		.X(o_dout)                              // 将数据送至顶层输出端口
	);

endmodule
