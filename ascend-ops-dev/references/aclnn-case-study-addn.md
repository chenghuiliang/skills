# `aclnnAddN` 封装经验

这份案例总结用于提醒：`aclnn` 封装问题通常不是“补两个接口函数”这么简单，重点在于辨清真实执行链路和最小修复边界。`AddN` 这次案例尤其适合复用到所有 `TensorList` / 多输入个数模板化算子。

## 1. 先区分 4 条路径

分析 AddN 时，必须分清：

- 现网 `aclOp` 路径
- 新增 `aclnn` L2 路径
- L0 路径
- built-in TBE / AICPU / 本地 AscendC AICore kernel 路径

不要把这些路径混成“同一个 AddN 实现”。

## 1.1 这次 AddN 的真实路径分叉

最终实测确认：

- `aclnnAddN` 在 `910b int64, input_count=33` 场景失败
- 同场景 `aclOp` / MindSpore `ops.addn` 成功
- 两者**不是同一条底层路径**

关键证据：

- `aclnn` 侧运行时打开的是：
  - `opp/built-in/op_impl/ai_core/tbe/kernel/config/ascend910b/ops_legacy/add_n.json`
  - `opp/built-in/op_impl/ai_core/tbe/kernel/ascend910b/ops_legacy/add_n/AddN_*.o`
- `aclOp` / MindSpore 同场景打开的是：
  - `opp/built-in/op_impl/ai_core/tbe/impl/ops_legacy/add_n.py`
  - `opp/built-in/op_impl/ai_core/tbe/impl/ops_legacy/dynamic/add_n.py`

这说明：

- `aclnn` 卡在 nnopbase 静态 bin 选择路径
- `aclOp` / MindSpore 则能走 built-in dynamic TBE 路径

## 2. `aclOp` 正常不代表本地源码链路正常

AddN 的经验表明：

- 现网 `aclOp` 很可能走 `canndev` built-in TBE/GE 路径
- 新补的 `aclnn` 可能直接命中本地 `ops-math` 里的 L0/AICore 路径

因此：

- “`aclOp` 没问题”不能证明“本地 kernel 没问题”
- “新增 `aclnn` 后才暴露问题”不等于“`aclnn` 代码本身有 bug”
- 若 `aclOp` 正常而 `aclnn` 失败，不要默认它们在调用“同一个底层算子实现”

## 3. 目标能力要先收敛

AddN 最终确认的能力边界是：

- 对齐 L0 真实能力
- 不支持广播
- 输入 tensor 的 shape 和 dtype 必须一致
- 不额外开放新 dtype，只对齐既有可执行能力

这类判断必须基于真实执行能力，而不是只看 host infer 文案或上层期望。

这次 AddN 还验证出两个具体边界：

- `int64`
  - `aclnnAddN`：`input_count=2..32` 可过，`>=33` 失败
  - `aclOp` / MindSpore `ops.addn`：已实测 `2`、`3`、`33` 输入可过
- `bfloat16`
  - 仅在 `910B` 支持矩阵中放开
  - 当前已验证 `PYNATIVE_MODE` / `GRAPH_MODE` 前向可过，未复现失败场景

## 4. 什么时候才改 kernel

只有同时满足下面条件，才建议对 kernel/tiling 做最小修复：

1. `aclnn/L0` 已明确命中当前源码中的本地实现
2. 实机或 smoke 已经稳定复现问题
3. 问题会阻断用户要求的既有能力对齐目标

如果只是理论猜测，或者问题只存在于未要求支持的 dtype/场景，不要贸然扩改 kernel。

这次 AddN 的反例非常典型：

- `int64, input_count=33` 失败时，**不应先改 `op_kernel` 数学实现**
- 根因先被证实是：`ascend910b` built-in `add_n.json` 对 `int64` 只覆盖到 `input_count=32`
- 这属于 **静态 bin 覆盖缺口 / dynamic fallback 差异**，不是先验的 kernel 数学错误

只有当下面 3 件事同时成立，才应该进一步怀疑 kernel 本体：

1. `aclOp` 与 `aclnn` 命中的是同一类底层资产
2. 配置文件确认失败场景本应被当前静态/动态资产覆盖
3. 输出错误或崩溃能稳定落到同一 kernel 逻辑

## 4.1 快速定位到问题代码点

当出现“`aclOp` 过、`aclnn` 挂”的 AddN 类问题，优先看这 3 处：

- `math/add_n/op_api/add_n.cpp`
  - 是否用了 `ADD_TO_LAUNCHER_LIST_AICORE(AddN, ...)`
- `opbase/include/nnopbase/opdev/make_op_executor.h`
  - `CreatAiCoreKernelLauncher(...)` 如何挑选静态 bin
- `math/add_n/op_host/add_n_def.cpp`
  - 是否声明了 `DynamicCompileStaticFlag(true)`

这 3 处能快速回答：

- `aclnn` 是不是固定优先走静态选择链路
- host 能力有没有宣称“支持动态编译”
- 问题更像“动态 fallback 没进来”，还是“kernel 代码本身不对”

## 5. AddN 常用验证清单

### 5.1 代码侧

- `tests/ut/op_api/test_aclnn_add_n.cpp`
- `examples/test_aclnn_add_n.cpp`
- `tests/smoke/*add_n*`

### 5.2 场景侧

- `nullptr`
- 空输入列表
- 输入项为空
- 单输入
- 多输入
- 大输入个数
- dtype 不一致
- shape 不一致
- 关键成功 dtype
- 典型失败 case

对 AddN 这类算子，再额外固定一条：

- **至少测一个超过常见模板边界的 `input_count`**
  例如 `33`、`65` 这类值，专门用来识别静态 bin 是否只覆盖到 `32` / `64`

## 5.3 这次 AddN 的最小复现手法

推荐最小复现优先级：

1. `aclnn` 独立 probe
   - 先扫 `input_count`
   - 如果 `2/3` 过、`33` 挂，优先怀疑 bin 覆盖问题
2. `aclOp` 独立 probe
   - 跑同 dtype、同 shape、同 `input_count`
3. MindSpore `ops.addn`
   - 用同一输入复现，确认上层用户路径结论
4. `strace -f -e openat`
   - 证明两条路径到底打开了哪些 `.json` / `.o` / `.py`

## 6. 远端环境验证习惯

用户已给出远端环境时，优先直接按环境复现：

```bash
cd /home/lch/work
source env_ms.sh
```

再做：

- 单算子 `opapi` 编译
- 定向 UT
- smoke
- example

需要排除环境污染时，再补：

```bash
export ASCEND_CUSTOM_PATH=/tmp/empty_ascend_custom
```

这次 AddN 的很多关键结论，都是在“空自定义包环境”下才稳定收敛出来的。

## 7. 交付文档必须写清楚的点

- 为什么 AddN 不支持广播
- 为什么某些 dtype 不支持，依据是什么
- 为什么需要或不需要 kernel 修复
- 为什么 `aclOp` 与 `aclnn` 的暴露行为不同
- 哪些结论来自实测，哪些只是代码分析推论

## 8. 可直接复用的根因判定模板

如果你看到以下组合特征：

- `aclnn` phase1 / `GetWorkspaceSize` 失败
- 失败只发生在某 dtype 的“大输入个数”
- `aclOp` / MindSpore 同场景成功
- `strace` 看到 `aclnn` 只开 `.json + .o`，`aclOp` 开了 `dynamic/*.py`

那么优先把根因写成：

- **`aclnn` 与 `aclOp` 命中了不同运行路径**
- **失败点是静态 bin 覆盖缺口或 dynamic fallback 未命中**
- **优先检查 launcher/fallback/资产覆盖，不先改 kernel 数学逻辑**
