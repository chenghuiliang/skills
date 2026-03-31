---
name: torch-npu-debugger
description: >
  端到端定位并解决 torch_npu 算子问题的专家 skill。涵盖问题分析、定界、定位、修复、回归验证、测试补充全流程。
  torch_npu 是 PyTorch 的 Ascend NPU 后端适配层，代码分为框架层（torch_npu/csrc）和算子层（third_party/op-plugin）。
  当用户提到 torch_npu 算子问题、NPU 算子 bug、ACLNN 适配错误、精度问题、format 转换异常、
  dispatch key 错误、dispatch key 冲突、expected_k._equalsBoxedAndUnboxed、_dispatch_check_all_invariants、
  DO_COMPATIBILITY fallback、OpCommand 报错、算子注册失败、NPU 编译错误、
  stream 同步问题、dtype 不匹配、反向传播异常等任何与 torch_npu 相关的问题时，
  都应该使用这个 skill。即使用户只是提到了一个 torch_npu 报错或者要调试某个 NPU 算子的行为，也应该触发此 skill。
  同样适用于 torch_npu 算子开发、ACLNN 算子移植、op-plugin 算子适配、NPU 算子测试编写等开发场景。
---

# torch_npu 算子问题端到端解决

你是 torch_npu 算子问题的诊断与修复专家。你能够端到端地分析、定界、定位、修复 NPU 算子问题，并完成回归验证和测试补充。

## 工作流程与检查点系统

本 skill 使用 **6 步工作流 + 强制检查点** 确保规定动作必须完成。

### 检查点定义

| 步骤 | 检查点 | 验证条件 | 是否强制 |
|------|--------|----------|---------|
| Step 1 | `problem_analyzed` | 问题分类已记录 | 必需 |
| Step 2 | `scope_identified` | 层级和文件路径已确定 | 必需 |
| Step 3 | `code_located` | 具体行号已定位 | 必需 |
| Step 4 | `fix_applied` | 补丁已生成并应用 | 必需 |
| Step 5 | `regression_verified` | 编译测试通过 | **强制** |
| Step 6 | `test_added` | 测试用例已添加 | **强制** |
| Final | `artifacts_archived` | 交付件已归档 | **强制** |

**强制检查点**（Step 5/6/Final）不能跳过，任务结束前必须调用 `workflow_guard.py require` 验证。

### 检查点调用方式

每完成一个步骤，使用 `Bash` 工具调用检查点脚本：

```bash
# 标记检查点完成
python scripts/workflow_guard.py mark <checkpoint_name> '<evidence_json>'

# 验证前置条件
python scripts/workflow_guard.py verify <checkpoint_name>

# 查看当前状态
python scripts/workflow_guard.py status

# 任务结束前强制检查（会阻断如果缺少强制检查点）
python scripts/workflow_guard.py require
```

---

## 工作目录

torch_npu 源码在用户的工作目录下：
- `torch_npu/` — 仓库根目录
  - `torch_npu/csrc/` — C++ 框架层（OpCommand、FormatHelper、NPU 运行时）
  - `third_party/op-plugin/` — 算子实现层（aclops、opapi、atb）
  - `torch_npu/npu/` — Python NPU 模块
  - `test/` — 测试套件
  - `ci/` — 构建脚本

注意: 算子实现主要在 `third_party/op-plugin/op_plugin/ops/` 下，分为 `aclops/`（旧路径）和 `opapi/`（新 ACLNN 路径）。

## 参考文档

`references/` 目录包含以下参考文档：

| 文档 | 用途 | 何时使用 |
|------|------|---------|
| `architecture.md` | 源码导航地图 | Step 3 定位时查找源码路径 |
| `issue_patterns.md` | 问题分类与诊断特征 | Step 2 定界时参考 |
| `fix_patterns.md` | 常见修复模式与代码模板 | Step 4 修复时参考 |
| `debugging_tools.md` | 内置调试工具使用指南 | 需要深度调试时参考 |

## 6 步工作流

### Step 1: 问题分析

**目标**: 收集错误信息、环境、复现步骤，进行问题分类

**操作**:
1. 使用 `Read` 工具查看错误日志
2. 使用 `Grep` 搜索相关代码
3. 参考 `references/issue_patterns.md` 进行问题分类（12 类之一）

**输出**: 问题类型、涉及算子、错误层级

**检查点**:
```bash
python scripts/workflow_guard.py mark problem_analyzed '{"issue_type": "format_conversion", "operator": "cdist", "layer": "ACLNN"}'
```

### Step 2: 定界 (Scoping)

**目标**: 确定问题所在层级

**操作**:
1. 根据错误信息判断层级：
   - `registration` - 算子注册问题
   - `ACLNN` - ACLNN 算子实现问题
   - `format` - 格式转换问题
   - `runtime` - NPU 运行时问题
2. 使用 `references/architecture.md` 定位源码路径模式

**输出**: 问题层级、相关文件路径模式

**检查点**:
```bash
python scripts/workflow_guard.py mark scope_identified '{"layer": "ACLNN", "path_pattern": "third_party/op-plugin/op_plugin/ops/opapi/*Npu.cpp"}'
```

### Step 3: 定位 (Localization)

**目标**: 找到具体的源码位置

**操作**:
1. 使用 `Grep` 搜索算子实现：
   ```bash
   # 搜索 ACLNN 实现
   rg -l "cdist" third_party/op-plugin/op_plugin/ops/opapi/

   # 搜索算子注册
   rg "TORCH_LIBRARY_IMPL.*cdist" third_party/op-plugin/
   ```
2. 使用 `Read` 阅读相关代码
3. 可选：使用 `Agent` 工具（Explore subagent）进行深度探索

**输出**: 具体文件路径和行号

**检查点**:
```bash
python scripts/workflow_guard.py mark code_located '{"file": "third_party/op-plugin/op_plugin/ops/opapi/CdistKernelNpu.cpp", "line": 45}'
```

### Step 4: 修复 (Fixing)

**目标**: 应用最小化修复

**操作**:
1. 参考 `references/fix_patterns.md` 选择修复模式
2. 使用 `Edit` 工具应用修复
3. 遵循 Clean Code 原则和项目编码规范

**输出**: 修复补丁

**检查点**:
```bash
python scripts/workflow_guard.py mark fix_applied '{"files": ["third_party/op-plugin/op_plugin/ops/opapi/CdistKernelNpu.cpp"], "lines_changed": 3}'
```

### Step 5: 回归验证 (Regression Verification) ⚠️ 强制

**目标**: 在 Ascend 服务器上编译测试

**操作**:
```bash
# 1. 同步代码到远程服务器
./scripts/sync-to-server.sh

# 2. SSH 到服务器并在 Docker 容器中编译
ssh root@192.168.9.116 "docker exec lch_test bash -c 'cd /home/lch/work/torch_npu2 && bash ci/build.sh'"

# 3. 运行测试
ssh root@192.168.9.116 "docker exec lch_test bash -c 'cd /home/lch/work/torch_npu2 && pytest test_ops.py::test_cdist -v'"
```

**输出**: 编译成功、测试通过

**检查点** (强制):
```bash
python scripts/workflow_guard.py mark regression_verified '{"test_passed": true, "log": "test_cdist.py::test_backward PASSED"}'
```

### Step 6: 测试补充 (Test Supplementation) ⚠️ 强制

**目标**: 添加覆盖此 bug 的测试用例

**操作**:
1. 使用 `Edit` 添加测试用例到相应的测试文件
2. 确保测试覆盖 bug 场景
3. 验证新测试能够通过

**输出**: 新增测试用例

**检查点** (强制):
```bash
python scripts/workflow_guard.py mark test_added '{"test_file": "test_ops/test_cdist.py", "test_name": "test_cdist_backward_contiguous"}'
```

### Final: 归档交付件 ⚠️ 强制

**目标**: 归档所有交付件和经验教训

**操作**:
1. 整理修复补丁
2. 整理测试用例
3. 记录问题根因和解决方案

**输出**: 归档文件

**检查点** (强制):
```bash
python scripts/workflow_guard.py mark artifacts_archived '{"patch": "fixes/cdist_contiguous.patch", "test": "test_ops/test_cdist.py", "summary": "Fixed cdist backward contiguous tensor issue"}'
```

### 任务结束前强制检查

**重要**: 任务结束前必须调用以下命令，确保所有强制检查点已完成：

```bash
python scripts/workflow_guard.py require
```

如果缺少强制检查点，此命令会阻断并列出缺失项。

## 使用 Claude Code 原生工具

本 skill 充分利用 Claude Code 的原生能力：

- **Agent 工具**: 使用 Explore subagent 进行深度代码探索
- **Bash 工具**: 执行远程命令（ssh）和本地脚本
- **Read/Edit 工具**: 读取和修改源码文件
- **Grep 工具**: 搜索代码模式
- **TaskCreate/TaskUpdate**: 跟踪工作进度

无需启动额外的后台进程或 Agent 系统。

## 常见问题类型

参考 `references/issue_patterns.md` 了解 12 类常见问题：

1. ACLNN 算子实现问题
2. 算子注册问题
3. Format 转换问题
4. Dispatch key 冲突
5. 精度问题
6. 反向传播问题
7. 内存问题
8. 编译错误
9. 运行时错误
10. 分布式问题
11. ATB 算子问题
12. 版本兼容性问题

## 修复模式

参考 `references/fix_patterns.md` 了解常见修复模式和代码模板。

## 调试工具

参考 `references/debugging_tools.md` 了解 torch_npu 内置的调试工具：
- OpHook - 算子执行钩子
- NPU Trace - NPU 执行追踪
- Dump - 张量数据导出
- Overflow Detection - 溢出检测
- ATB Logs - ATB 算子日志

---

## 远程验证注意事项

### 环境初始化

```bash
# 错误：直接运行
ssh user@server "cd /home/lch/work/torch_npu && pytest test/test_xxx.py"

# 正确：先 source 环境
ssh user@server "cd /home/lch/work && source env_ms.sh mindspore/ && cd torch_npu && pytest test/test_xxx.py"
```

### 编译优化

**纯 Python 修改无需重新编译**：如果补丁只修改了 `.py` 文件，无需重新编译，直接运行测试即可。只有修改了 C++ 源码（`csrc/`、`op-plugin/`）才需要重新编译。

### 工具链兼容性检查

若遇到 segfault 或 undefined symbol 错误，检查编译工具链版本：

```bash
readelf -p .comment /path/to/torch/_C.cpython-310-aarch64-linux-gnu.so
```

若 Python / torch / torch_npu 包的 GCC 版本不一致，应优先判定为构建工具链不兼容，回到原容器内做 clean rebuild。

---

## 知识库参考

- `references/architecture.md` - torch_npu 架构和路径导航
- `references/issue_patterns.md` - 12 类问题分类和决策树
- `references/fix_patterns.md` - 修复模式模板
- `references/debugging_tools.md` - 调试工具使用指南

---

