---
name: ascend-ops-dev
description: >
  在 CANN `ops-*`/`canndev`/`ge` 工作区中开发和封装 Ascend 算子的专家 skill，重点覆盖 `aclnn` 两段式接口封装、
  L0/`aclOp`/built-in 路径分析、最小化代码改动、UT/example 补充、实机编译验证和交付归档。
  当用户提到 CANN 算子开发、`aclnn` 接口封装、Ascend 算子适配、`ops-math`/`ops-nn`/`canndev` 算子改造、
  `aclOp` 与 `aclnn` 差异分析、910A/910B/910C/910D/950 平台支持、AscendC kernel 修复、算子 UT/example 编写、
  远端实机编译测试或交付件归档时，都应该使用这个 skill。
  即使用户只是要求“给某个已有算子补 aclnn 接口”或“分析为什么 aclOp 正常但 aclnn 有问题”，也应触发此 skill。
---

# Ascend `aclnn` 封装执行清单

用于 CANN 多仓工作区里的 `aclnn` 接口封装、链路分析、最小修复和交付整理。默认目标不是“多改代码”，而是先辨清真实执行路径，再做最小可验证改动。

## 先做什么

收到需求后，先明确 4 个问题：

1. 目标能力边界是什么：对齐 L0、现网 `aclOp`，还是 built-in 发布态？
2. 用户是否要求“完全对齐已有能力”，还是允许新增 dtype / 广播 / format？
3. 当前问题属于 `ops-*` 源码、`canndev` built-in、还是 `ge`/图编译链路？
4. 是否要求远端实机编译、执行、归档交付？

如果用户没有特别要求，默认策略是：

- 对齐已有能力，不主动新增 dtype
- 不主动新增广播
- 只做能被真实链路证明必要的 kernel/tiling 修复
- 必须补 UT、example、至少一条实机或 smoke 验证

## 执行步骤

### 1. 盘点整条链路

不要只看单仓。至少检查：

- `ops-*`：`op_api/`、`op_host/`、`op_kernel/`、`examples/`、`tests/ut/`
- `canndev/ops/built-in`：TBE/AICPU `op_info_cfg` 与 `impl`
- `canndev/ops/<domain>/<op>`：发布态 host / graph 资产
- `ge/`：必要时看 op type、infer、pass

优先加载：

- [references/cann-aclnn-workflow.md](./references/cann-aclnn-workflow.md)
- [references/aclnn-framework-rules.md](./references/aclnn-framework-rules.md)
- [references/aclnn-case-study-addn.md](./references/aclnn-case-study-addn.md)

如果要检查 skill 自身是否会稳定给出正确回答结构，再读：

- [references/eval-baselines.md](./references/eval-baselines.md)

### 2. 判断是否只封装接口

先尝试只改：

- `op_api/aclnn_<op>.h`
- `op_api/aclnn_<op>.cpp`
- `CMakeLists.txt`
- `examples/test_aclnn_<op>.cpp`
- `tests/ut/op_api/test_aclnn_<op>.cpp`

只有在真实执行链路命中本地 AICore/L0 路径，且实机或 smoke 已证明失败时，才允许最小修复 `op_host/*tiling*` 或 `op_kernel/*`。

### 3. 按框架硬规则实现

实现 `aclnn` 时必须遵守：

- L2 固定两段式签名：`GetWorkspaceSize` + 执行函数
- `L2_DFX_PHASE_1` / `L2_DFX_PHASE_2` 必须放在函数起始处
- `CREATE_EXECUTOR` 后再创建 `aclOpExecutor`
- phase-1 返回前用 `ReleaseTo` 转移 executor 所有权
- 需要 shape 推导时，`INFER_SHAPE` 必须在 `ADD_TO_LAUNCHER_LIST_*` 之前
- L0 API 起始处使用 `L0_DFX`
- 标准包装优先考虑 `Contiguous`、`ViewCopy`、`Cast`、`Reshape`、`Transpose`、`TransData`

如果用户没有明确要求，不默认启用 repeatable executor。

### 4. 先判断 dtype / 平台扩展是否成立

如果用户要求“新增 dtype”或“补齐 910A/B/C/D/950 支持”，不要直接改白名单、`opdef` 或平台注册，先同时核实：

- L0 真实执行能力是否支持
- `canndev` built-in 已公开能力是否支持
- 本地 `op_host` / `op_kernel` / `tiling` 是否已覆盖
- 新增能力是否会把执行链路打到未验证路径

如果用户要求“仅对齐现网能力”，优先按已公开且已可执行的能力收口，而不是按理论上可扩展能力收口。

### 5. 补测试与样例

最少覆盖：

- `nullptr`
- 空输入列表 / 输入项为空
- dtype 不支持 / dtype 不一致
- shape 不一致
- 输出 shape/dtype 不匹配
- 单输入、多输入
- 关键成功 dtype
- 典型失败 case
- 至少一条 smoke 或实机执行 case

如果目标是“对齐已有 `aclOp` / built-in 能力”，则**`aclOp` 与 `aclnn` 能力对比本身是必须测试项**，不能只测 `aclnn` 自己能不能跑。至少补齐并核实以下维度：

- format：区分 `ND`、常见 public format、private format，不要默认“非 private 都支持”
- dtype：区分 AICore 主链路 dtype、AICPU fallback dtype、平台差异 dtype
- shape 规则：同 shape 成功、shape 不一致失败、广播失败
- 结构边界：空 Tensor、空 TensorList、单输入、多个输入、标量输入
- 维度边界：最大维度数、超维度失败
- 类型边界：mixed dtype 失败、输出 dtype 不匹配失败
- 典型执行路径：至少一条 public format 成功 case、至少一条负例 case、必要时一条 AICPU fallback 执行 case

推荐对比顺序：

1. 先用 built-in `aclOp` 实测真实能力边界，再判断 `aclnn` 应该对齐什么
2. 再补 `aclnn` 的 UT / smoke / example
3. 最后只对真实不对齐项做最小修复

新增强制规则：

- **`aclnn` 封装若宣称“对齐 `aclOp` 能力”，必须优先证明两者命中的实际执行路径一致或等价。**
  这里的“路径”至少包括：AICore/AICPU 分流、built-in/vendor 资产来源、host binary 配置、kernel 资产命中结果。
  不能只因为 `l0op::<Op>` 看起来支持某 dtype/format，就推断 `aclOp` 也公开支持，或推断 `aclnn` 已自动对齐。
- **必须先做 `aclOp` 基线探针，再做 `aclnn` 对照。**
  对于 dtype/format/平台争议项，先用最小 `aclOp` 探针直接调用现网安装环境中的 `aclopCompileAndExecuteV2` 或等价运行接口，
  拿到真实返回码和输出，再决定 `aclnn` 要不要补能力、修路径或收缩文档。
- **必须隔离环境污染后再下结论。**
  若机器上存在 `opp/vendors/*` 自定义包、多个 `ASCEND_CUSTOM_PATH` 候选目录、旧版自定义 so/json/o 资产，必须至少补一轮“干净环境”对照：
  例如把 `ASCEND_CUSTOM_PATH` 指到空目录，或只挂单一 vendor 目录，再分别复跑 `aclOp` / `aclnn` 关键 case。
  未做环境隔离前，不能把失败直接归因到源码缺陷。

特别注意：

- **不要把本地 `l0op::<Op>` 或源码理论能力，当成 built-in `aclOp` 已公开能力**
- format 能力必须实测；很多算子并不是“所有非 private format 都支持”
- 若 `aclnn` 封装里存在 `ReFormat(..., ND)` 一类 descriptor 归一化步骤，不要默认它是必需的。先区分：
  - `ReFormat` 往往只是改 tensor descriptor，不等于真实 `TransData`
  - 真正的性能代价通常来自 `Contiguous` / `ViewCopy` / `TransData`
  - 若怀疑 `ReFormat(ND)` 是冗余步骤，优先做一次“最小去除探针”：
    1. 只移除 `ReFormat(ND)`，保留其余规整逻辑
    2. 先跑 `GetWorkspaceSize` 定向 UT，确认 phase-1 不回归
    3. 再跑执行级 smoke / example，确认 kernel 真正能过
    4. 只有执行级证据也成立，才允许正式删除该步骤
- 对 format 能力做结论时，必须区分：
  - phase-1/`GetWorkspaceSize` 通过
  - 执行级 smoke / example 通过
  不能用前者替代后者
- 若 `aclOp` 与 `aclnn` 某 dtype/format 的结论互相矛盾，优先排查：
  - 是否跑到了不同的 built-in/vendor 资产
  - 是否 `aclnn` 命中了本地 `ops-*` 资产而 `aclOp` 命中了安装态 built-in 资产
  - 是否默认环境里混入了历史自定义包、旧二进制或旧 so
- 若 full suite 在清理阶段有历史性崩溃，优先采用“单 case 单进程”探针或定向 `gtest_filter`
- 进程退出阶段若有历史性 TBE/Python 清理崩溃，只能把“崩溃前已经打印出的单 case 结果”作为证据，且必须在结论中说明
- 必须区分：
  - **用例本体执行是否通过**
  - **进程退出阶段是否发生历史性崩溃**
  后者不能直接写成“算子执行失败”，除非已经证明崩溃发生在算子执行或结果校验之前
- 报告中必须分别写清：`aclOp` 实测结论、`aclnn` 实测结论、两者差异、修复项、残留未验证风险

### 6. 做实机验证

涉及平台、dtype、kernel、注册差异时，不要只靠静态阅读收尾。优先按用户给定环境执行，例如：

```bash
cd /home/lch/work
source env_ms.sh
```

再做单算子 `opapi` 编译、UT、smoke、example 验证。

如果需求包含“能力对齐”或“为什么 `aclOp` 正常但 `aclnn` 有问题”，则实机验证必须至少包含：

- 一组 built-in `aclOp` 对比探针或等价调用
- 一组 `aclnn` 定向 UT / smoke
- 一组“干净环境 vs 默认环境”的对照结果
- 一份按场景列出的 capability matrix

补充经验：

- `bash build.sh --opapi -u --noexec --ops=<op>` 不一定会重新生成或刷新某些独立 smoke 可执行；若源码已更新但 smoke 仍表现为旧行为，需直接执行：

```bash
cmake --build build --target add_n_aclnn_smoke_test -j16
```

再运行对应 smoke case，避免把“旧二进制未更新”误判为“新代码无效”。

### 7. 归档交付

若用户要求交付件，至少整理：

- 设计文档
- 开发总结
- 最终代码 diff / patch
- 编译运行命令
- 已验证结论与未验证风险

## 输出要求

结论必须明确区分：

- 代码事实
- 基于代码事实的推论
- 已实测验证项
- 未验证风险项

不要把“现网 `aclOp` 能跑”直接写成“本地源码链路正确”。
