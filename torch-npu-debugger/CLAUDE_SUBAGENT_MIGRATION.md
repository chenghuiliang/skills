# 多 Agent 系统改造评估：自定义实现 vs Claude Code subAgent

## 一、评估：是否需要改造？

### 当前实现特点

| 维度 | 现状 |
|------|------|
| **进程模型** | Python `multiprocessing.Process`，完全独立进程 |
| **通信机制** | 文件系统消息总线（`.agent_messages/`）或 Redis |
| **生命周期** | 自我管理（心跳、重启、故障恢复） |
| **部署方式** | 可作为独立服务长期运行 |
| **与 Claude 关系** | 松耦合，Claude 只负责启动 |

### Claude Code subAgent 特点

| 维度 | subAgent |
|------|----------|
| **进程模型** | Claude 内部管理的子进程 |
| **通信机制** | 通过 Claude Code 内部机制 |
| **生命周期** | Claude 管理（启动、停止、超时） |
| **部署方式** | 每次调用时启动，完成后结束 |
| **设计目标** | 并行执行独立任务，收集结果 |

### 改造建议：**不需要完全改造，建议混合架构**

**理由：**

1. **当前设计合理** - 您的系统是一个**长期运行的多 Agent 服务**，适合作为独立进程
2. **subAgent 适合短任务** - Claude subAgent 更适合"并行执行多个独立查询"的场景
3. **保留灵活性** - 当前实现可以脱离 Claude Code 独立运行（如部署为服务）

### 建议的混合架构

```
用户问题
    ↓
Claude (主会话)
    ↓ (使用 Agent 工具并行)
┌─────────────┬─────────────┐
│ subAgent 1  │ subAgent 2  │  ← 使用 Claude subAgent
│ 分析日志     │ 搜索代码     │
└─────────────┴─────────────┘
    ↓
整合结果 → 原多 Agent 系统
    ↓ (通过 CLI 或 API 调用)
Planner → Executor → Evaluator → ... (保持现有架构)
```

## 二、如需改造：方案设计

如果仍希望将核心 Agent 改造为 Claude subAgent，有两种方案：

### 方案 A：轻量级改造（推荐）

保持现有架构，仅将**部分子任务**改为 subAgent 并行执行。

**适用场景：**
- 分析阶段需要同时处理多个日志文件
- 定位阶段需要并行搜索多个目录

```python
# 在 Executor 的 analyzer 子角色中使用 subAgent
from claude_agent_sdk import Agent

def analyze_logs_parallel(log_files: List[str]) -> List[AnalysisResult]:
    """使用 subAgent 并行分析多个日志。"""
    agents = [
        Agent(
            model="haiku",
            prompt=f"分析日志文件: {log_file}",
            tools=["Read", "Grep"]
        )
        for log_file in log_files
    ]
    # 并行执行，收集结果
    results = [agent.run() for agent in agents]
    return results
```

### 方案 B：完整改造（工作量大）

将每个 Agent 改为 Claude subAgent。

**架构变化：**

| 当前组件 | 改造后 | 说明 |
|---------|--------|------|
| `ProcessManager` | Claude Agent 工具 | 不再自行管理进程 |
| `MessageBus` | subAgent 输出 | 通过返回值通信 |
| `Agent._run()` | subAgent prompt | 每个 Agent 是一个子任务 |
| 心跳机制 | 不再需要 | Claude 管理生命周期 |

**改造示例：**

```python
# 原代码：coordinator.py
class CoordinatorAgent(Agent):
    def _assign_task_to_agent(self, pending: PendingTask, agent_id: str):
        # 通过消息总线发送任务
        self.send_message(recipient=agent_id, ...)

# 改造后：使用 Claude Agent 工具
def run_planner_agent(issue: Dict) -> Plan:
    """启动 Planner subAgent。"""
    result = Agent(
        model="sonnet",
        prompt=PLANNER_PROMPT.format(issue=issue),
        tools=["Read", "Grep", "Glob"]
    ).run()
    return parse_plan(result)
```

### 方案 C：API 封装（折中）

保留现有系统，添加 Claude Code 集成层。

```
Claude Code
    ↓
multi_agent/cli/commands.py (扩展)
    ↓ HTTP/gRPC
已运行的 Multi-Agent 服务
```

## 三、改造工作量评估

| 方案 | 工作量 | 风险 | 收益 |
|------|--------|------|------|
| A. 轻量级 | 1-2 天 | 低 | 分析阶段提速 |
| B. 完整改造 | 1-2 周 | 高 | 代码简化，但失去独立性 |
| C. API 封装 | 2-3 天 | 中 | 保留现有，增加集成 |
| **不改造** | 0 | 无 | 保持现状 |

## 四、我的建议

**推荐：不改造 + 在分析阶段使用 subAgent**

您的多 Agent 系统设计合理，作为长期服务运行是正确的选择。Claude subAgent 更适合短生命周期任务。

**可在以下场景增量使用 subAgent：**

1. **日志分析** - 同时分析多个日志文件
2. **代码搜索** - 并行搜索多个目录/模式
3. **测试执行** - 并行运行多个测试用例

**是否需要继续提供改造代码？**

如果选择方案 A 或 C，我可以继续提供具体实现代码。如果选择不改造，可以关闭此任务。
