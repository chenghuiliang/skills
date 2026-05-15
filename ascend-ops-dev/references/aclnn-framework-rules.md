# `aclnn` 框架硬规则

这份清单总结自 `CANN社区版 9.0.0 算子库 01.pdf` 中的 `aclnn` 开发规范，适合在实现 L0/L2 接口时对照检查。

## 1. L0 与 L2 的职责边界

- L0 是 host 侧单 kernel API，常见命名空间为 `l0op`
- L0 返回或操作 `aclTensor *`、`aclTensorList *` 等对象
- L0 最后一个参数固定为 `aclOpExecutor *executor`
- L2 `aclnn` 是对一个或多个 L0 调用的高层封装

## 2. L2 固定两段式签名

标准 `aclnn` 接口为：

```cpp
aclnnStatus aclnnXxxGetWorkspaceSize(..., uint64_t *workspaceSize, aclOpExecutor **executor);
aclnnStatus aclnnXxx(void *workspace, uint64_t workspaceSize, aclOpExecutor *executor, aclrtStream stream);
```

规则：

- 参数顺序和类型按框架固定格式实现
- phase-1 负责校验、准备、构造 executor、计算 workspace
- phase-2 负责执行
- 默认不要把 phase-2 当作同一 executor 的可重复执行入口

## 3. 宏与调用时序

### 3.1 L2 phase-1 / phase-2

- `L2_DFX_PHASE_1` 必须放在 `aclnnXxxGetWorkspaceSize` 函数最开始
- `L2_DFX_PHASE_2` 必须放在 `aclnnXxx` 函数最开始
- `CREATE_EXECUTOR` 必须早于 `aclOpExecutor` 生命周期管理
- phase-1 返回前必须通过 `ReleaseTo` 或等价方式把 executor 所有权转给输出参数

### 3.2 L0

- `L0_DFX` 必须位于 L0 API 起始位置
- 避免在 L0 中写出不规范的递归/嵌套 L0 调用形态

### 3.3 形状推导与下发

- 若算子需要 shape infer，`INFER_SHAPE` 必须先于 `ADD_TO_LAUNCHER_LIST_AICORE` 或 `ADD_TO_LAUNCHER_LIST_AICPU`
- 常见参数包装宏包括：
  - `OP_INPUT`
  - `OP_OUTPUT`
  - `OP_ATTR`
  - `OP_ATTR_NAMES`
  - `OP_OPTION`
  - `OP_WORKSPACE`

## 4. 标准基础算子包装

做 `aclnn` 封装时，优先复用基础 tensor 操作，而不是自己重写中间变换：

- `Contiguous`
- `ViewCopy`
- `Cast`
- `Reshape`
- `Transpose`
- `TransData`

其中 `Contiguous` / `ViewCopy` 是最常见的输入准备和输出回写手段。

## 5. Repeatable Executor 约束

`aclSetAclOpExecutorRepeatable` 允许 phase-1 构建后的 executor 被重复使用，但有约束：

- 调用方需要自行销毁 executor，例如 `aclDestroyAclOpExecutor`
- 若内部依赖 host/device copy 类 L0，通常不适合 repeatable
- 若 `ViewCopy` 使用相同 src/dst 地址，通常不适合 repeatable
- 算子内部不应偷偷创建新的 device tensor 来规避地址变化

若需要变更地址，可关注：

- `aclSetDynamicInputTensorAddr`
- `aclSetDynamicOutputTensorAddr`
- `aclSetDynamicTensorAddr`

默认封装时，不启用 repeatable executor，除非用户明确要求且约束已逐项核实。

## 6. 头文件与库名习惯

- `aclnn` 头文件优先放在 `aclnnop/aclnn_*.h`
- 9.0.0 起常见按域拆分库为 `libopapi_math.so`、`libopapi_nn.so` 等
- 不要默认依赖旧的 `libopapi.so` 习惯
