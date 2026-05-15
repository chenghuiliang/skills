# `ascend-ops-dev` 参考输出基线

这份文档不是给最终用户看的说明书，而是给 skill 自身做前向校验时使用的回答基线。目标是约束回答顺序，避免把 `aclnn` 封装问题答成泛泛的“加接口、补测试”。

## Eval 1: 为已有 `aclOp` 算子补 `aclnn`，且严格对齐现网能力

理想回答应包含以下结构：

1. 先收敛目标能力边界
   - 明确“不新增广播”
   - 明确“不默认新增 dtype”
   - 明确“先对齐现网 `aclOp` 或 L0 的真实能力”
2. 说明必须横向检查的仓位
   - `ops-*` 的 `op_api`、`op_host`、`op_kernel`、`tests/ut`、`examples`
   - `canndev/ops/built-in` 的 TBE/AICPU 与 op info
   - 必要时查 `ge/`
3. 说明最小改动面
   - 首选只改 `aclnn_<op>.h/.cpp`、CMake、UT、example、文档
   - 只有真实执行链路命中本地 kernel 且实测失败时，才改 `op_host` / `op_kernel`
4. 给出测试计划
   - `nullptr`
   - 空输入列表
   - dtype / shape mismatch
   - 单输入、多输入
   - 关键成功 dtype
   - 至少一条 smoke 或实机 case

如果回答缺少“能力边界判定”或“全链路盘点”，则说明 skill 仍偏泛化。

## Eval 2: `aclOp` 正常但新增 `aclnn` 后实机失败

理想回答应包含以下结构：

1. 明确指出 `aclOp` 正常不能直接证明本地源码链路没问题
2. 区分至少 5 条路径
   - `aclOp`
   - `aclnn` L2
   - L0
   - built-in TBE / AICPU
   - 本地 AscendC AICore kernel
3. 给出排查顺序
   - 看 `canndev` built-in 是否已公开该能力
   - 看 `ops-*` 中 `aclnn` 是否会直达本地 L0 / kernel
   - 单算子编译
   - 定向 UT / smoke / example
   - 实机日志收口
4. 给出修复准则
   - 若只是 `aclnn` 包装问题，修 `op_api`
   - 若真实命中本地 kernel 且失败，再做最小 kernel/tiling 修复

如果回答直接跳到“修改 kernel”或“新增平台注册”，说明 skill 没有守住最小修复原则。

## Eval 3: 判断是否可以开放新增 dtype

理想回答应包含以下结构：

1. 明确结论不是“只改白名单”
2. 列出必须同时核实的 4 个方面
   - L0 实际可执行 dtype
   - `canndev` built-in 已公开 dtype
   - `op_host` / `tiling` / `op_kernel` 是否覆盖
   - 测试是否能打到新增路径
3. 若用户要求对齐现网能力
   - 优先按已公开且已可执行能力收口
   - 不按理论可扩展能力收口
4. 给出验证动作
   - 增加对应 dtype 的 UT
   - 至少一条实机执行 case
   - 必要时查 smoke / example

如果回答把问题简化成“看 def / config / op_info 是否支持”，说明 skill 仍然不够严格。
