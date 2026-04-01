# 测试用例：cdist 反向传播 contiguous 张量问题

## 问题描述

**算子**: `torch.cdist`
**问题类型**: Format 转换问题
**错误信息**: `RuntimeError: expected contiguous tensor, but got non-contiguous tensor`
**触发场景**: 反向传播时，梯度张量非连续导致 ACLNN API 调用失败

## 完整工作流测试

### Step 1: 问题分析

```bash
python scripts/workflow_guard.py mark problem_analyzed '{"issue_type": "format_conversion", "operator": "cdist", "layer": "ACLNN", "error": "non-contiguous tensor in backward"}'
```

**预期输出**: ✓ Checkpoint 'problem_analyzed' marked as completed

### Step 2: 定界

```bash
python scripts/workflow_guard.py mark scope_identified '{"layer": "ACLNN", "path_pattern": "third_party/op-plugin/op_plugin/ops/opapi/CdistKernelNpu.cpp", "component": "backward implementation"}'
```

**预期输出**: ✓ Checkpoint 'scope_identified' marked as completed

### Step 3: 定位

```bash
python scripts/workflow_guard.py mark code_located '{"file": "third_party/op-plugin/op_plugin/ops/opapi/CdistKernelNpu.cpp", "line": 78, "function": "cdist_backward_npu"}'
```

**预期输出**: ✓ Checkpoint 'code_located' marked as completed

### Step 4: 修复

**修复内容**: 在调用 ACLNN API 前添加 `.contiguous()` 确保张量连续性

```cpp
// Before fix:
aclnnCdistBackward(grad_output, ...);

// After fix:
auto grad_contiguous = grad_output.contiguous();
aclnnCdistBackward(grad_contiguous, ...);
```

```bash
python scripts/workflow_guard.py mark fix_applied '{"files": ["third_party/op-plugin/op_plugin/ops/opapi/CdistKernelNpu.cpp"], "lines_changed": 2, "pattern": "contiguous_before_aclnn"}'
```

**预期输出**: ✓ Checkpoint 'fix_applied' marked as completed

### Step 5: 回归验证 (强制)

```bash
python scripts/workflow_guard.py mark regression_verified '{"test_passed": true, "log": "test_cdist.py::test_cdist_backward PASSED", "build_status": "success"}'
```

**预期输出**: ✓ Checkpoint 'regression_verified' marked as completed

### Step 6: 测试补充 (强制)

```bash
python scripts/workflow_guard.py mark test_added '{"test_file": "test/test_ops/test_cdist.py", "test_name": "test_cdist_backward_non_contiguous", "coverage": "non-contiguous gradient tensor"}'
```

**预期输出**: ✓ Checkpoint 'test_added' marked as completed

### Final: 归档交付件 (强制)

```bash
python scripts/workflow_guard.py mark artifacts_archived '{"patch": "fixes/cdist_contiguous_backward.patch", "test": "test/test_ops/test_cdist.py", "summary": "Fixed cdist backward to handle non-contiguous gradient tensors", "root_cause": "ACLNN API requires contiguous input"}'
```

**预期输出**: ✓ Checkpoint 'artifacts_archived' marked as completed

### 强制检查

```bash
python scripts/workflow_guard.py require
```

**预期输出**: ✓ All mandatory checkpoints completed

## 验证标准

- 所有 7 个检查点必须按顺序完成
- 强制检查点（regression_verified, test_added, artifacts_archived）不能跳过
- `workflow_guard.py require` 必须通过
- `.workflow/checkpoints.json` 包含所有检查点记录

## 清理

```bash
rm -f .workflow/checkpoints.json
```

## 参考

- 问题分类: `references/issue_patterns.md` - Format 转换问题
- 修复模式: `references/fix_patterns.md` - contiguous_before_aclnn 模式
- 架构导航: `references/architecture.md` - ACLNN 算子层
