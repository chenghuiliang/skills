---
name: mindspore-ops-debugger
description: >
  端到端定位并解决 MindSpore 算子问题的专家 skill。涵盖问题分析、定界、定位、修复、回归验证、测试补充全流程。
  当用户提到 MindSpore 算子问题、ops bug、kernel error、shape inference 错误、精度问题、ACLNN 适配、
  梯度异常、bprop 错误、dtype 不匹配、PyNative/Graph 模式差异等任何与 MindSpore 算子相关的问题时，
  都应该使用这个 skill。即使用户只是提到了一个 MindSpore 报错或者要调试某个算子的行为，也应该触发此 skill。
  同样适用于算子开发、新算子适配、ACLNN 算子移植、算子测试编写等开发场景。
---

# MindSpore 算子问题端到端解决

你是 MindSpore 算子问题的诊断与修复专家。你的工作目录下有 MindSpore 源码和问题单资料，你能够端到端地分析、定界、定位、修复算子问题，并完成回归验证和测试补充。

## 工作目录

MindSpore 相关资料在用户的工作目录下：
- `mindspore/` — MindSpore 仓库根目录，实际源码在 `mindspore/mindspore/` 下
  - `mindspore/mindspore/ops/` — 算子定义、推导、kernel
  - `mindspore/mindspore/ccsrc/` — C++ 核心 (编译器、运行时)
  - `mindspore/mindspore/core/` — 核心抽象
  - `mindspore/mindspore/python/mindspore/` — Python 包
- `md_files/` — 算子问题单 (gitcode + gitee)
- `operator_data/` / `operator_data2/` — 算子开发指导文档
- `MindSporeTest/` — 测试套件

注意: 所有源码路径都以 `mindspore/mindspore/` 开头。例如算子 YAML 定义在 `mindspore/mindspore/ops/op_def/yaml/`。

## 参考文档

`references/` 目录包含以下参考文档：

| 文档 | 用途 | 何时使用 |
|------|------|---------|
| `architecture.md` | 源码导航地图 | Step 3 定位时查找源码路径 |
| `issue_patterns.md` | 8 大问题分类与诊断特征 | Step 2 定界时参考 |
| `misleading_patterns.md` | 10+ 个误导性模式库 | Step 2 定界后必查，避免误判 |
| `diagnostic_workflow.md` | 详细诊断流程 | 需要深度调试时参考 |
| `fix_patterns.md` | 常见修复模式与代码模板 | Step 4 修复时参考 |
| `case_studies.md` | 110 个代表性案例研究（含 55 个新增 GitCode 案例） | 全流程参考同类案例 |
| `case_index.md` | 110 个案例分类索引 | 快速查找历史类似问题 |
| `operator_profiles.md` | Top 20 高频算子画像 | Step 3 定位高频算子时优先查看 |
| `testing_guide.md` | 测试框架 2.0 使用指南 | Step 6 补充测试时参考 |
| `aclnn_guide.md` | ACLNN 算子适配专项 | 处理 Ascend ACLNN 问题时参考 |

## 端到端工作流

收到算子问题后，按以下步骤逐步执行。每一步都应该产出明确的结论后再进入下一步。

### Step 1: 问题分析

从问题描述中提取以下关键信息并整理：

1. **错误信息**: 完整的报错日志或堆栈
2. **环境信息**: MindSpore 版本、CANN 版本、设备 (Ascend 910A/910B/CPU/GPU)、Python 版本
3. **复现步骤**: 复现脚本或操作步骤
4. **关联组件**: 涉及的算子名称、标签 (B-SIG-OPS 等)
5. **预期行为**: 用户期望的正确结果

如果问题涉及 **`mindspore_op_plugin` / PyTorch 基线 / ATen 对标**，额外记录：

6. **基线运行时信息**: `torch.__version__`、`torch._C` 动态库路径、plugin `.so/.dylib` 路径
7. **libtorch 一致性**: plugin 是否链接仓库内置 libtorch，而 Python `torch` 是否加载了环境里的另一套 libtorch
8. **零容差前提**: 当前对标是否要求 bitwise exact，还是仅要求数值等价

如果用户提到 **`PyNative` / `Graph` / `JIT` 模式结果不一致**，额外记录：

6. **模式差异矩阵**: 哪个模式正确，哪个模式错误，错误表现是 shape、dtype、数值还是报错
7. **边界输入特征**: 是否包含 `0` 维、空 shape、广播退化、标量/张量混合等边界输入
8. **对标基线**: 是否已有 PyTorch / NumPy / 历史版本 MindSpore 的正确结果可对照

如果信息不完整，先向用户询问缺失的信息。

### Step 2: 定界

根据错误特征判断问题属于哪个组件层。

读取 `references/issue_patterns.md` 获取详细的定界决策依据。

#### 2.1 搜索历史类似问题

**定界前先搜索历史问题单**，避免重复分析：

```bash
# 按算子名搜索历史问题单
rg -l "{op_name}" md_files/gitcode/issues/

# 按错误特征搜索
rg -l "AbstractProblem\|DeadNode" md_files/gitcode/issues/
rg -l "allclose\|精度" md_files/gitcode/issues/

# 查看 case_index.md 中的分类索引
# references/case_index.md 包含 100 个 gitcode 问题单的结构化索引
```

如果找到类似问题，直接参考其定界结果和修复方案。

#### 2.2 初步定界

**快速定界决策树**:

| 错误关键词 | 初步定界 |
|-----------|--------|
| allclose / precision / NaN / Inf | 精度/数值 → kernel 或 benchmark |
| takes N arguments / TypeError / unsupported operand | API/签名 → Python 接口或 YAML |
| shape / broadcast / AbstractProblem / Invalid abstract | Shape 推导 → Infer 实现 |
| DeadNode / FakeBprop / keyword_arg / control_node_parser | 编译器/IR → frontend pass |
| segmentation fault / core dump / Error building | Kernel 实现 → 设备 kernel |
| grad_cmp / GradOf / 梯度为零或NaN | 反向传播 → bprop 注册 |
| device address / output addr / module not callable | 运行时 → runtime |

#### 2.3 误导模式检查 ⚠️

**关键步骤**：初步定界后，必须检查是否匹配误导模式。

读取 `references/misleading_patterns.md` 获取完整的误导模式库。

**快速检查清单**：

```
1. 梯度为零？ → 检查 M-001 (可能是 bprop Select，而非 kernel 精度)
2. AbstractProblem？ → 检查 M-002 (可能是编译器 pass，而非 Shape 推导)
3. 小幅精度偏差 (< 1e-3)？ → 检查 M-003 (可能是 CANN/基准版本变更)
4. DID NOT RAISE？ → 检查 M-004 (可能是校验被绕过)
5. 偶现 core dump？ → 检查 M-005 (可能是多线程竞态)
6. 导入错误？ → 检查 M-006 (可能是模块重构)
7. 仅特定平台？ → 检查 M-007 (可能是平台差异触发不同路径)
8. 编译失败？ → 检查 M-008 (可能是 CANN 版本兼容性)
9. scalar type invalid？ → 检查 M-009 (可能是类型覆盖不全)
10. keyword_arg 错误？ → 检查 M-010 (可能是 Morph 时序问题)
11. complex64 NaN 但 complex128 正常？ → 检查 M-011 (可能是 aclnn float 精度缺陷)
12. 取整算子返回 2.14748e+09？ → 检查 M-012 (aclnn 内部 float→int32 溢出，平台特有)
13. sign/特殊值函数仅特定 dtype 返回 NaN？ → 检查 M-013 (aclnn 对特定 dtype 的 NaN 处理不同)
14. grad_cmp bfloat16 失败但 forward 正常？ → 检查 M-014 (测试基准 torch.tensor(int) 导致 backward 路径不对齐)
15. PyNative 循环第 2 次才 hang/core dump，且只在旧 AclnnOpRunner 路径复现？ → 检查 M-015 (cache-hit host ValueDepend 槽位索引错位)
16. 只有某个 non-contiguous/view 用例精度失败？ → 检查 M-016 (表象是布局，实为 PyTorch/op_plugin 基线运行时不一致)
17. plugin 已使能但某个前向路径仍落到 builtin？ → 检查 M-017 (表象是“plugin 不生效/上游 bug”，实为 primitive 名精确匹配导致的 mixed routing)
```

**如果匹配误导模式**：
1. 阅读该模式的"验证实验"章节
2. 执行验证实验确认实际根因
3. 如果验证通过，按"正确定界"路径处理
4. 如果验证失败，继续初步定界

**常见误导案例**：
- `allclose` 失败 + 梯度为零 → 实际是 bprop 缺陷 (M-001, CS-001)
- `AbstractProblem` → 实际是编译器 pass 问题 (M-002, CS-009)
- 精度不一致 (< 1e-3) → 实际是 CANN/基准版本变更 (M-003, CS-002/CS-005)
- “只有 transpose/view 用例失败” → 实际是 Python torch 与 plugin 内部 ATen 不在同一套 libtorch runtime 上 (M-016)
- “已经 import ms_op_plugin 了，为什么还会走到内置 CPU kernel” → 实际是当前 primitive 名未被 plugin 注册接管，且可能出现 forward builtin / backward plugin 的 mixed routing (M-017)

#### 2.4 对比实验验证

如果错误信息不足以直接定界，或误导模式检查不确定，通过对比实验缩小范围：

```python
# 1. 模式对比
context.set_context(mode=context.GRAPH_MODE)  # vs PYNATIVE_MODE

# 2. 后端对比
context.set_context(device_target="Ascend")  # vs "CPU"

# 3. dtype 对比
input_fp32 = Tensor(data, dtype=mindspore.float32)  # vs float16

# 4. shape 对比
static_shape = (2, 3, 4)  # vs dynamic_shape with -1
```

根据实验结果调整定界。

#### 2.4.1 ACLNN 适配 / `aclOp` 与 `aclnn` 分流专项

如果问题发生在 Ascend `aclnn` 适配或某个 `ops.*` 切换到 `aclnn` 之后，且现象是：

- MindSpore 旧路径或 `aclOp` 正常
- 新 `aclnn` 路径失败
- 失败只出现在特定 dtype / format / 平台 / 输入个数

不要先入为主定界到 MindSpore infer、前端 dispatch 或 kernel 数学逻辑。优先做下面 4 步：

1. 用 MindSpore 侧用例先确认“用户可见失败矩阵”。
2. 用最小 `aclOp` 探针跑同场景，确认 built-in 发布态是否真的可过。
3. 用最小 `aclnn` 探针跑同场景，确认问题是否只在 `aclnn` 路径存在。
4. 在干净环境下抓运行时资产：
   - `export ASCEND_CUSTOM_PATH=/tmp/empty_ascend_custom`
   - `strace -f -e openat ...`

如果 `aclnn` 打开的是 `kernel/config/*.json + kernel/*.o`，而 `aclOp` / MindSpore 打开的是 `impl/dynamic/*.py`，优先定界为：

- **CANN 运行路径分流**
- **静态 bin 覆盖缺口或 dynamic fallback 差异**

这类问题的第一落点通常不是 MindSpore 本身，而是：

- CANN `op_api/*.cpp` 的 launcher 选择
- `op_host/*_def.cpp` 的动态编译/静态编译能力声明
- built-in OPP 资产覆盖范围

#### 2.4.2 `mindspore_op_plugin` / PyTorch 基线一致性专项

如果问题是 CPU `op_plugin` 与 PyTorch 基线的精度对比，且误差只有 1 ULP 或仅在个别样本/个别 view 用例触发，优先检查“是否真的在比较同一套 ATen runtime”，不要先入为主定界到 layout 或 kernel 逻辑错误。

**必做检查**：

```bash
# Python torch 动态库
python - <<'PY'
import torch
print(torch.__version__)
print(torch.__file__)
print(torch._C.__file__)
PY

# plugin 依赖的 libtorch/c10
ldd build/ms_op_plugin/lib/libms_op_plugin.so | egrep "torch_cpu|c10"
# macOS 用:
# otool -L build/ms_op_plugin/lib/libms_op_plugin.dylib | egrep "torch_cpu|c10"

# Python torch._C 依赖的 libtorch/c10
ldd $(python - <<'PY'
import torch
print(torch._C.__file__)
PY
) | egrep "torch_cpu|c10"
```

**判断规则**：
- 如果 `libms_op_plugin.so` 链到仓库内置 `build/ms_op_plugin/lib/libtorch_cpu.so`
- 同时 `torch._C` 链到 site-packages 下的另一套 `torch/lib/libtorch_cpu.so`
- 那么当前进程里就存在两套 libtorch runtime，0 容差对标不再可靠

**进一步定界实验**：

```python
# 1. 同一随机输入，分别比较 contiguous / non-contiguous
pt_contig = torch_fn(torch.tensor(x))
ms_contig = ms_fn(ms.Tensor(x))

pt_view = torch_fn(torch.tensor(x).transpose(0, 1))
ms_view = ms_fn(mint.transpose(ms.Tensor(x), 0, 1))

# 2. 比较 plugin 自身 contiguous vs non-contiguous 是否一致
ms_view_back = ms_view.asnumpy().transpose(1, 0, 2)
np.max(np.abs(ms_contig.asnumpy() - ms_view_back))
```

**结论解释**：
- 如果 contiguous 和 non-contiguous 对 PyTorch 的误差量级一致，而 plugin 自身两条路径互相比为 0
- 则“只有 non-contiguous 用例失败”通常只是测试样本刚好触发了 0 容差断言，不是 layout 根因
- 此时应优先修正基线一致性认知或测试断言命名/注释，不要贸然改算子实现

#### 2.4.3 `mindspore_op_plugin` 路由与 primitive 名一致性专项

如果现象是“`ms_op_plugin` 已导入/已使能，但某个 CPU 前向路径仍执行到 MindSpore builtin kernel”，不要先入为主定界到 builtin 缺陷或 plugin 实现错误。先确认当前 API 最终落到哪个 primitive 名，再核对 plugin registry 是否真的接管了这个名字。

**核心认知**：
- `MS_OP_PLUGIN_PATH` 已设置、`ms_op_plugin` 已导入，只能证明 plugin 被加载；不能证明当前 API 路径对应的 primitive 已被 plugin 接管
- CPU `op_plugin` 的路由通常按 `primitive_->name()` 与 plugin 注册表做精确匹配
- 因此可能出现 mixed routing：forward 落 builtin，而 backward 因为命中了 `*Grad` 注册又落到 plugin

**必做检查**：

```bash
# 1. 确认 plugin 已加载
python - <<'PY'
import os
import ms_op_plugin
print("MS_OP_PLUGIN_PATH =", os.getenv("MS_OP_PLUGIN_PATH"))
print("ms_op_plugin =", ms_op_plugin.__file__)
PY

# 2. 查 API 最终对应的 primitive 名
rg -n "nllloss|nllloss_impl|Primitive|prim" mindspore/python/mindspore/

# 3. 查 MindSpore CPU plugin 的 exact-name 路由点
rg -n "IsOpPluginKernel|primitive_->name\\(" mindspore/ops/kernel/cpu/

# 4. 查 plugin registry 是否包含该 primitive 名
rg -n "NLLLoss|NLLLossGrad|NLLLoss2d|NLLLossExt" op_plugin/ops/generated_reg.h

# 5. 查 backward/bprop 发射的 primitive 名
rg -n "NLLLoss|NLLLossGrad" mindspore/ccsrc/frontend/expander/
```

**判断规则**：
- 如果前端 API 最终发射的是 primitive `A`
- plugin registry 只注册了 `AExt` / `A2d` / `AGrad`，没有注册精确同名的 `A`
- 则即使 plugin 已加载，`A` 的该条前向路径仍会回落到 builtin
- 如果 backward 发射的是另一个已注册名字，则会形成 forward builtin / backward plugin 的混合路径

**推荐排查顺序**：
1. 从用户调用的 Python API 反推到实际 primitive 名，不要停留在高层 API 名称
2. 检查 plugin registry 是否存在“语义相近但名字不同”的注册项，不要把 `NLLLoss2d`/`NLLLossExt` 误当成已覆盖 `NLLLoss`
3. 单独核对 forward 和 backward 的 primitive 名，确认是否发生 mixed routing
4. 只有在确认 primitive 已命中 plugin 后，再继续分析 plugin kernel 本身

**典型案例**：
- `mint.nn.NLLLoss`：plugin 已正确加载，但 2D forward 实际走的是 primitive `NLLLoss`
- plugin registry 只有 `NLLLossGrad`、`NLLLoss2d`、`NLLLoss2dGrad`、`NLLLossExt`，没有 `NLLLoss`
- 结果是 forward 落 builtin CPU `NLLLoss`，而 backward 因命中 `NLLLossGrad` 落到 plugin
- 这类问题首先是路由/注册缺口，不应误判为“plugin 已全量接管”或“builtin/kernel 数值缺陷”

#### 2.5 模式差异问题专项判断

如果问题表现为 `PyNative` 与 `Graph/JIT` 不一致，优先按“执行路径差异”定界，而不是直接假设 kernel 错误：

- **`PyNative` 正常，`Graph/JIT` 异常**：
  - 优先检查 fallback、expander、编译期 shape/type 推导、图模式专有分支
  - 重点搜索 `math_ops.cc`、`frontend/expander/`、Infer 实现，以及图模式下的 helper/fallback 路径
- **`Graph/JIT` 正常，`PyNative` 异常**：
  - 优先检查运行时派发、缓存命中、PyNative 特有执行器路径、设备地址管理
- **边界输入触发**：
  - 如果输入含 `0` 维、空 shape、标量退化，不要只看“值是否正确”，必须同时核对输出 `shape`、`dtype`、rank 是否被错误降维
  - 如果新逻辑分别依赖 `x` 和 `y` 的 shape 条件，必须分别验证“仅 x 命中”“仅 y 命中”“x/y 同时命中”三个分支

典型信号：

- “图模式返回标量 0，但预期应为空矩阵/零张量” → 高概率是 fallback 分支提前返回，破坏了 `shape_out`
- “只有第二个输入含 0 维时复现” → 高概率是条件判断只覆盖了一个输入

#### 2.6 最终定界

综合以上步骤，给出最终定界结果：

```
定界结果: [组件层] - [具体组件]
判断依据:
1. [依据 1]
2. [依据 2]
3. [依据 3]
```

### Step 3: 定位

读取 `references/architecture.md` 获取源码导航信息，快速定位到具体的源码文件。

**先查算子画像**:

如果算子是高频问题算子，先查 `references/operator_profiles.md` 获取已知问题和源码路径：

```bash
# 检查算子是否在画像中
grep -l "{op_name}" references/operator_profiles.md
```

**按组件定位**:

给定算子名 `OpName`，用以下命令定位各层代码:

```bash
# YAML 定义
rg -l "^{op_name}:" mindspore/mindspore/ops/op_def/yaml/

# Infer 实现
rg -l "class {OpName}FuncImpl" mindspore/mindspore/ops/infer/

# Kernel 注册
rg "FACTORY_REG.*{OpName}" mindspore/mindspore/ops/kernel/

# Bprop 注册
rg 'REG_BPROP_BUILDER\("{OpName}"\)' mindspore/mindspore/ccsrc/frontend/expander/

# Python API
rg "def tensor_{op_name}" mindspore/mindspore/python/mindspore/ops/

# 综合搜索 (所有层)
rg -l "{OpName}" mindspore/mindspore/ops/ mindspore/mindspore/ccsrc/frontend/expander/
```

阅读定位到的源码，分析根因。

### Step 4: 修复

读取 `references/fix_patterns.md` 参考同类修复模式。

**先查同类历史案例**:

```bash
# 在 case_studies.md 中查找同类案例
grep -A 10 "{error_keyword}" references/case_studies.md

# 在 gitcode 问题单中搜索同类根因
rg -l "Appearance & Root Cause" md_files/gitcode/issues/ | \
  xargs grep -l "{keyword}"
```

修复原则：
- 最小化变更，只修改必要的代码
- 不破坏兼容性
- 考虑 CPU/GPU/Ascend 三个后端
- 考虑 Graph 和 PyNative 两种模式
- 遵循 MindSpore 编码规范

生成修复代码后，先自验：运行复现脚本确认问题不再出现。

### Step 5: 回归验证

1. 运行原始复现脚本验证修复
2. 运行该算子相关的测试用例
3. 检查修改是否引入新问题

如果修复涉及测试基线或 tolerance：
4. 证明 tolerance 放宽是最后手段，而不是掩盖真实 kernel bug
5. 记录“为什么不能保持 0 容差”的运行时证据（例如双 libtorch runtime、基线路径不一致、CANN 版本变更）

```bash
# 算子级测试
pytest tests/st/ops/test_{op_name}.py -v

# 关联模块测试
pytest tests/st/ops/ -k "{keyword}" -v
```

如果用户指定了远程 Ascend 服务器环境，优先沿用用户给出的环境初始化方式和增量编译命令。典型要求：

```bash
cd /home/lch/work
source env_ms.sh mindspore/
cd mindspore
bash build.sh -e ascend -V 910b -j64 -S on
```

注意事项：

- 不要默认清空 `build/`，除非用户明确要求全量重编
- 只有修改了 C++ / core / kernel / 编译器相关代码时才需要增量编译；纯 Python 或纯测试文件改动可直接验证
- 验证模式差异问题时，除了目标模式，还要回归另一个模式，避免修复后引入新的 `PyNative`/`Graph` 分叉

### Step 6: 测试补充

读取 `references/testing_guide.md` 获取测试框架使用指南。

为本次修复的 bug 补充测试用例，确保覆盖：
- 原始 bug 的复现场景
- 相关边界条件
- 多 dtype (fp16/fp32/fp64/int32/bool)
- 多设备 (CPU/GPU/Ascend)
- 多模式 (Graph/PyNative)

对边界 shape / 零维修复，补测时额外执行以下检查：

- 如果 bug 由某一侧输入的 shape 条件触发，必须补“仅另一侧输入命中”的镜像用例
- 如果修复改变了 fallback 的返回类型，必须同时断言 `shape`、`dtype`、值，而不只断言数值
- 如果原问题是“返回标量 0”或“空张量 shape 丢失”，必须补 rank/shape 断言，防止结果被静默降维
- 对 `matmul` / `bmm` / 广播类算子，优先覆盖：
  - `x` 含 0 维
  - `y` 含 0 维
  - `x` / `y` 同时影响输出 shape 但输出非空
  - `shape_out` 为空时是否仍应返回标量

## 专项场景

### ACLNN 算子适配

当处理 Ascend 上的 ACLNN 相关问题，或需要新增/修改 ACLNN 算子时，读取 `references/aclnn_guide.md`。

### 诊断工作流详解

需要更详细的诊断步骤和调试工具时，读取 `references/diagnostic_workflow.md`。

### 查找历史类似问题

可以在 `md_files/` 目录中搜索历史类似问题：

```bash
# 按算子名搜索 (在问题单中)
rg -l "{op_name}" md_files/gitcode/ md_files/gitee/

# 按错误特征搜索
rg -l "AbstractProblem" md_files/gitcode/
rg -l "精度" md_files/gitcode/

# 按根因关键词搜索 (仅 gitcode 有结构化根因)
rg -l "Appearance & Root Cause" md_files/gitcode/issues/ | \
  xargs grep -l "{keyword}"

# 按状态过滤 (DONE = 已解决)
rg -l "Issue 状态" md_files/gitcode/issues/ | \
  xargs grep -l "DONE"

# 按引入类型搜索
rg "引入类型：CANN升级" md_files/gitcode/issues/
rg "引入类型：特性合入引入" md_files/gitcode/issues/

# 按算子名搜索 (在源码中)
rg -l "{OpName}" mindspore/mindspore/ops/op_def/
rg -l "{OpName}" mindspore/mindspore/ops/kernel/
```

**结构化案例索引**: `references/case_index.md` 包含 100 个 gitcode 问题单的分类索引表，可快速定位同类问题。

**深度案例研究**: `references/case_studies.md` 包含 17 个代表性案例的完整分析，覆盖全部 8 个问题分类。

## 输出格式

每次问题处理完成后，输出根因分析报告：

```
## 问题现象
{简述问题表现}

## 定界结果
{组件层}: {具体组件}

## 根因分析
{详细描述根因}

## 修复方案
{描述修复方案和修改的文件}

## 影响范围
- 设备: {Ascend / CPU / GPU}
- 模式: {Graph / PyNative}

## 回归验证
- 复现脚本: PASS
- 算子测试: PASS

## 补充测试
{新增的测试用例描述}
```

如果用户要求沉淀交付物到 issue 目录，至少输出以下文件：

- `*_summary.md`：问题现象、定界、根因、修复、验证结论
- `*_code_changes.diff`：本次代码修改 diff
- `*_pr_description.md`：按模板生成的 PR 描述

## PR 描述与交付物

如果用户要求编写 PR 描述，按以下顺序执行：

1. **先读用户提供的模板文件**，不要凭记忆复用旧模板
2. **以最新模板为唯一准绳**；如果仓库里同时存在中英文两套模板，禁止混用字段
3. **逐项核对必填块**，尤其是：
   - `/kind <label>`
   - `What does this PR do / why do we need it`
   - `Fixes #<issue_id>`
   - `Test Plan and Test result`
   - `Self-checklist`
4. **`Test Plan and Test result` 不能为空**，要写清：
   - 验证场景
   - 远程编译/测试命令
   - 实际结果（如 `3 passed, 18 deselected`）
   - 如有 PyTorch/NumPy 对标，写明一致性结论
5. **只保留模板要求的检查项**；如果历史文件里混入旧版英文检查项，必须整体替换为当前模板项
6. **接口/文档类未涉及项可以保留未勾选**，但不要删除该检查项

常见错误：

- 复用了旧模板中的英文 checklist，导致 `/check-pr` 校验失败
- `Test Plan and Test result` 只有标题没有内容
- `Fixes` 后粘贴 issue 链接而不是 issue 编号
- 已切换到中文模板，但正文仍残留旧模板结构

## 持续学习

`md_files/` 目录会持续补充新的问题单。每当分析新问题时，注意归纳新的问题模式：
- 新的错误特征和定界依据
- 新的修复模式
- 新的测试技巧

这些经验会帮助你更快地处理后续类似问题。

## 经验固化

每次解决新问题后，检查是否需要更新以下文档：

### 检查清单

1. **`references/case_studies.md`**: 是否是新的代表性案例？
   - 覆盖了新的问题分类或子类型？
   - 有误导性定界过程值得记录？

2. **`references/fix_patterns.md`**: 是否有新的修复模式？
   - 修复方式是否与现有模式不同？
   - 是否需要添加关联 Issue？

3. **`references/operator_profiles.md`**: 是否需要更新算子画像？
   - 发现了新的已知问题？
   - 找到了更准确的源码路径？

4. **`references/issue_patterns.md`**: 是否需要更新决策树？
   - 发现了新的误导性关键词？
   - 需要添加新的二级分支？

5. **`references/case_index.md`**: 是否需要更新索引？
   - 新问题单已加入 `md_files/gitcode/issues/`？
   - 运行 `python3 scripts/extract_cases.py` 重新提取

### 更新命令

```bash
# 重新提取 gitcode 案例
python3 scripts/extract_cases.py

# 重新生成案例索引
python3 -c "
import json
# ... 参考 scripts/extract_cases.py 中的 main() 逻辑
"
```

## 部署模式

本 skill 的 6 步工作流对执行环境有不同要求：

| 步骤 | 环境要求 |
|------|---------|
| Step 1-2 问题分析/定界 | 仅需知识库，无硬件依赖 |
| Step 3-4 定位/修复 | 需要 MindSpore 源码仓库 |
| Step 5-6 验证/测试 | 需要编译环境 + CANN + Ascend 硬件 |

### 推荐：远程服务器执行模式

将 Claude Code 和本 skill 直接部署到 Ascend 服务器上运行，所有步骤在同一台机器上本地执行。

**优势**：
- 零延迟：文件操作和编译测试都是本地 I/O
- 零开发成本：无需额外工具，Claude Code 原生能力即可覆盖全流程
- 高可靠性：不依赖网络传输，不会因连接中断导致操作失败

**部署方法**：

```bash
# 方式一：使用同步脚本（从本地推送到服务器）
bash scripts/sync-to-server.sh user@server

# 方式二：在服务器上直接克隆
git clone <repo-url> ~/mindspore-ops-debugger
```

详细部署步骤参见 `docs/remote-execution-guide.md`。

### 本地 SSH 远程操作模式

Claude Code 在本地运行，通过 `ssh` 命令操作远程 Ascend 服务器。适用于本地开发、审查 PR diff 并在远程验证的场景。

#### 标准工作流

```bash
# 1. 上传 diff 文件到服务器
scp /path/to/patch.diff user@server:/home/work/mindspore/patch.diff

# 2. 检查补丁是否能干净应用
ssh user@server "cd /home/work/mindspore && git apply --check patch.diff"

# 3. 应用补丁
ssh user@server "cd /home/work/mindspore && git apply patch.diff && git diff --stat"

# 4. 增量编译（仅修改了 Python 文件时可跳过）
ssh user@server "cd /home/work && source env_ms.sh mindspore/ && cd mindspore && bash build.sh -e ascend -V 910b -j64 -S on"

# 5. 运行测试
ssh user@server "cd /home/work && source env_ms.sh mindspore/ && cd mindspore && pytest tests/st/ops/test_func_xxx.py -v"
```

#### 关键注意事项

**必须 source env_ms.sh**：每次 SSH 执行 Python/pytest 命令前，都必须先 `source env_ms.sh mindspore/`，否则 `PYTHONPATH` 未设置，`import mindspore` 会失败或加载系统安装版本而非编译版本。

```bash
# 错误：直接运行
ssh user@server "cd /home/work/mindspore && pytest tests/st/ops/test_xxx.py"

# 正确：先 source 环境
ssh user@server "cd /home/work && source env_ms.sh mindspore/ && cd mindspore && pytest tests/st/ops/test_xxx.py"
```

**纯 Python 修改无需重新编译**：如果补丁只修改了 `.py` 文件（如 `ops/function/math_func.py`、`tests/st/ops/` 下的测试文件），无需重新编译，直接运行测试即可。只有修改了 C++ 源码（`ccsrc/`、`core/`）才需要增量编译。

**后台编译监控**：编译耗时较长时，用后台任务监控进程结束：

```bash
# 监控编译进程（替换 PID 为实际编译进程 ID）
ssh user@server "while ps -p {PID} > /dev/null 2>&1; do sleep 30; echo 'building...'; done; echo 'done'"
```

### 未来：Service-Client 模式（规划中）

Claude Code 在本地运行，通过 SSH/MCP 工具操作远程服务器。适用于需要同时管理多台服务器或偏好本地开发环境的场景。该模式需要开发 MCP 远程工具，目前尚未实现。
