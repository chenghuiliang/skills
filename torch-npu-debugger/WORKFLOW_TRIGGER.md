# 多 Agent 工作流触发机制

本文档说明定位完成后如何自动触发评估器和资料归档。

## 工作流触发链

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Planner │────►│ Executor │────►│ Verifier │────►│ Evaluator│────►│ Archiver │
│(planning)│    │(execution)│    │ (verify) │    │(evaluation)│    │(archive) │
└─────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                │                │                │                │
      │  1.创建计划     │  2.修复实现     │  3.编译测试     │  4.审查验收     │  5.归档
      │                │                │                │                │
      ▼                ▼                ▼                ▼                ▼
   用户问题         workflow_step    workflow_step    workflow_step    workflow_step
                   ="execution"     ="verify"        ="evaluation"    ="archive"
```

## 触发机制

### 核心逻辑 (`Coordinator._trigger_next_step`)

```python
def _trigger_next_step(self, completed_task_id: str, result: Dict):
    workflow_step = result.get("workflow_step")

    next_steps = {
        "analysis": ("scoping", [AgentCapability.SCOPE.value]),
        "scoping": ("location", [AgentCapability.LOCATE.value]),
        "location": ("fix", [AgentCapability.FIX.value]),
        "fix": ("verify", [AgentCapability.VERIFY.value]),
        "execution": ("verify", [AgentCapability.VERIFY.value]),
        "verify": ("evaluate", [AgentCapability.EVALUATE.value]),
        "evaluation": ("archive", [AgentCapability.ARCHIVE.value]),
    }

    if workflow_step in next_steps:
        next_step_type, required_caps = next_steps[workflow_step]
        # 创建并分派下一任务
```

## 各 Agent 的 workflow_step 设置

| Agent | workflow_step | 触发条件 | 下一 Agent |
|-------|---------------|----------|-----------|
| Planner | planning | 用户创建问题 | Executor |
| Executor | execution | 修复完成 | Verifier |
| Verifier | verify | 编译测试完成 | Evaluator |
| Evaluator | evaluation | 审查通过 | Archiver |
| Archiver | archive | 归档完成 | 无（结束） |

## 代码示例

### ExecutorAgent 完成修复后

```python
# ExecutorAgent._handle_execution_task
result = {
    "success": True,
    "deliverables": deliverables,
    "workflow_step": "execution"  # ← 触发 verify
}

self.send_message(
    recipient="coordinator",
    message_type=MessageType.TASK_COMPLETE,
    payload={
        "task_id": task_id,
        "result": result,
        "workflow_step": "execution"
    }
)
```

### Coordinator 触发下一任务

```python
# Coordinator._trigger_next_step
if workflow_step == "execution":
    next_step_type = "verify"
    required_caps = [AgentCapability.VERIFY.value]

    # 创建新任务
    new_task_id = f"{completed_task_id}_verify"
    self.send_message(
        recipient=self.agent_id,  # 发送给自己来分派
        message_type=MessageType.TASK_CREATE,
        payload={
            "task_id": new_task_id,
            "task_type": "verify",
            "previous_result": result,
            "required_capabilities": required_caps,
            "priority": 5
        }
    )
```

### VerifierAgent 完成验证后

```python
# VerifierAgent._handle_verify_task
if verification.get("success"):
    self.send_message(
        recipient="coordinator",
        message_type=MessageType.TASK_COMPLETE,
        payload={
            "task_id": task_id,
            "result": verification,
            "workflow_step": "verify"  # ← 触发 evaluate
        }
    )
```

### EvaluatorAgent 完成评估后

```python
# EvaluatorAgent._handle_evaluation_task
result = {
    "passed": passed,
    "evaluation_results": evaluation_results,
    "workflow_step": "evaluation"  # ← 触发 archive
}

if passed:
    self.send_message(
        recipient="coordinator",
        message_type=MessageType.TASK_COMPLETE,
        payload={
            "task_id": task_id,
            "result": result
        }
    )
```

### ArchiverAgent 完成归档

```python
# ArchiverAgent._handle_archive_task
archive_result = {
    "success": True,
    "archive_dir": str(task_archive_dir),
    "workflow_step": "archive"  # ← 工作流结束
}

self.send_message(
    recipient="coordinator",
    message_type=MessageType.TASK_COMPLETE,
    payload={
        "task_id": task_id,
        "result": archive_result
    }
)
```

## 评估失败的处理

如果 Evaluator 审查不通过：

```python
# EvaluatorAgent
if not passed:
    self.send_message(
        recipient="executor",  # 直接发回 Executor
        message_type=MessageType.TASK_REJECT,
        payload={
            "task_id": task_id,
            "reason": feedback,
            "requires_rework": True
        }
    )
```

这会跳过归档，直接让 Executor 重做。

## 启动完整工作流

```python
from multi_agent.core import CoordinatorAgent

# 创建 coordinator
coordinator = CoordinatorAgent()

# 启动工作流
workflow_id = coordinator.start_debugging_workflow({
    "title": "matmul精度问题",
    "description": "torch_npu.matmul与CPU结果不一致",
    "error_log": "allclose failed...",
    "operator_name": "matmul"
})

# 工作流自动执行：
# 1. Coordinator 创建 analysis 任务 → Planner
# 2. Planner 完成 → 创建 scoping 任务 → Planner (scoping sub-role)
# 3. Planner 完成 → 创建 location 任务 → Executor (locator sub-role)
# 4. Locator 完成 → 创建 fix 任务 → Executor (fixer sub-role)
# 5. Executor 完成 → 创建 verify 任务 → Verifier
# 6. Verifier 完成 → 创建 evaluate 任务 → Evaluator
# 7. Evaluator 通过 → 创建 archive 任务 → Archiver
# 8. Archiver 完成 → 工作流结束
```

## 状态跟踪

```python
# 查看工作流状态
status = coordinator.get_workflow_status(workflow_id)
print(f"Current step: {status['current_step']}")
print(f"Steps completed: {status['steps_completed']}")

# 查看系统状态
system_status = coordinator.get_system_status()
print(f"Active tasks: {system_status['active_assignments']}")
print(f"Completed tasks: {system_status['completed_tasks']}")
```
