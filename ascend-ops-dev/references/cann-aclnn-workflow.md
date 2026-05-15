# CANN `aclnn` 封装工作流

这份清单适合在 `ops-*` 多仓里落地 `aclnn` 封装时逐项执行。重点是先判断能力边界和真实路径，再决定改动面。

## 1. 接单后先定边界

先写清楚以下结论，再开始改代码：

1. 目标是对齐 L0、现网 `aclOp`，还是发布态 built-in 能力？
2. 是否允许新增 dtype、广播、format？
3. 平台范围是 910A/B/C/D、950，还是只要求某一平台可运行？
4. 是否要求远端实机验证与交付归档？

若用户要求“和现有 `aclOp` 完全一致”，默认策略是：

- 不新增 dtype
- 不新增广播
- 不擅自扩展 format
- 先复用现有行为，再补必要缺口

## 2. 代码盘点顺序

收到算子封装任务后，按下面顺序查：

1. `ops-*` 中目标算子的目录结构
2. `op_api/` 是否已有可复用 L0 接口
3. `op_host/` 中 `*_def.cpp`、infer shape、tiling
4. `op_kernel/` 和 `op_kernel_aicpu/`
5. `examples/` 和 `tests/ut/`
6. `canndev/ops/built-in/tbe/op_info_cfg`
7. `canndev/ops/built-in/tbe/impl`
8. `canndev/ops/built-in/aicpu/op_info_cfg`
9. `canndev/ops/<domain>/<op>`
10. 必要时查 `ge/` 中的 op type / infer / pass

## 3. 高频判断题

### 3.1 是否只包接口，不动 kernel

优先尝试不改 kernel。只有在以下情况才改：

- `aclnn/L0` 真实执行会直达当前源码里的 AICore kernel
- 实机或 smoke 已证明该 kernel 路径失败
- 用户要求对齐现有能力，而当前源码路径缺少关键 dtype/行为支持

### 3.2 是否必须同时看 `canndev`

只要用户提到以下任一项，就必须看 `canndev`：

- “现有 `aclOp` 能跑”
- “发布态已经支持”
- “为什么 `aclOp` 没问题，`aclnn` 有问题”
- “910A/B/C/D/950 是否支持”

### 3.3 是否需要注册多个平台

不要从单个算子类比。至少同时核实：

- 当前算子的 `*_def.cpp`
- 仓内相似算子的注册方式
- `canndev` built-in op info 是否已覆盖对应平台
- 实机“跑通”是否真的命中了本地源码链路

### 3.4 是否允许新增 dtype 支持

不要只因某个相似算子支持更多 dtype，就直接给当前算子放开白名单。至少同时核实：

- L0 接口实际可执行的 dtype
- `canndev` built-in 已公开 dtype
- `op_host`/`tiling`/`op_kernel` 是否存在对应分支
- 相关 UT、smoke、example 是否能覆盖新增路径

如果缺少其中任一项，默认结论应是“继续核实”，而不是“先放开再看”。

## 4. 典型文件改动面

最小 `aclnn` 封装常见改动：

- `CMakeLists.txt`
- `op_api/aclnn_<op>.h`
- `op_api/aclnn_<op>.cpp`
- `examples/test_aclnn_<op>.cpp`
- `tests/ut/op_api/test_aclnn_<op>.cpp`
- `README.md`
- `docs/aclnn<Op>.md`

当 L0 尚未提供可复用入口时，才可能进一步改：

- `op_api/<op>.cpp`
- `op_host/<op>_def.cpp`

只有被真实问题打到时，才改：

- `op_host/*tiling*.cpp`
- `op_kernel/*`

## 5. 测试与验证顺序

### 5.1 UT 最低集合

- 空指针
- 空输入列表
- 输入项为空
- dtype 不支持
- dtype 不一致
- shape 不一致
- 输出 shape/dtype 不一致
- 单输入
- 多输入
- 关键 dtype 成功路径

### 5.2 smoke / example 最低集合

- `many_inputs`
- `shape_mismatch`
- 一个成功执行 example

如果问题与 dtype 相关，再补：

- `int64`
- `bfloat16`
- 用户要求对齐的其他已公开 dtype

## 6. 远端验证建议

优先用隔离目录，避免污染原仓：

```bash
cd /home/lch/work
source env_ms.sh
cp -a cann/ops-math addn_verify
cd addn_verify
```

常见单算子构建方式：

```bash
bash build.sh --opapi -u --noexec --soc=ascend910b --ops=add_n -j8
```

常见追加编译与执行：

```bash
cd build
cmake --build . --target add_n_aclnn_smoke_test -j8
./tests/ut/op_api/add_n_aclnn_smoke_test many_inputs
./tests/ut/op_api/add_n_aclnn_smoke_test shape_mismatch
```

## 7. 文档中要写清楚的内容

- 目标能力是否与现有 L0/`aclOp` 对齐
- 是否支持广播
- 输入输出是否必须同 shape、同 dtype
- 为什么新增 dtype 可以或不可以开放
- 为什么某些平台注册是必需或非必需
- 为什么需要或不需要修改 kernel
- 远端验证环境、命令和结果
- 哪些结论是实测，哪些只是推断
