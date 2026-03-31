# Docker 容器远程访问集成

本文档描述 VerifierAgent 如何使用 Docker 容器模式在远程 Ascend 服务器上进行增量编译和测试。

## 概述

VerifierAgent 现在支持两种远程执行模式：

1. **SSH 直连模式**（默认）：在远程服务器上直接执行命令
2. **Docker 容器模式**：在远程服务器的 Docker 容器内执行编译和测试

## Docker 模式优势

- **增量编译**：无需清空 build 目录，节省时间
- **环境隔离**：容器内已配置好所有依赖（CANN、Python、GCC 等）
- **可复现性**：相同容器环境确保编译结果一致
- **简化配置**：不需要在远程服务器上配置复杂的环境变量

## 典型使用场景

用户在远程服务器上有一个运行中的 Docker 容器 `lch_test`，容器内已经配置好了 torch_npu 编译环境：

```bash
# 在远程服务器上手动执行的方式：
docker exec -it lch_test bash
cd /home/lch/work/torch_npu2/
bash ci/build.sh --python=3.10
exit
```

使用 VerifierAgent 可以自动化这个过程。

## 使用方法

### 1. 环境变量配置

```bash
export TORCH_NPU_REMOTE_HOST="user@server"
export TORCH_NPU_REMOTE_KEY="~/.ssh/id_rsa"
export TORCH_NPU_USE_DOCKER="true"
export TORCH_NPU_DOCKER_CONTAINER="lch_test"
export TORCH_NPU_DOCKER_WORKDIR="/home/lch/work/torch_npu2"
export TORCH_NPU_PYTHON_VERSION="3.10"
```

### 2. 代码中使用

```python
from multi_agent.agents.verifier_agent import VerifierAgent

# 创建 VerifierAgent（Docker 模式）
agent = VerifierAgent(
    remote_host="user@server",
    remote_key_path="~/.ssh/id_rsa",
    use_docker=True,
    docker_container="lch_test",
    docker_work_dir="/home/lch/work/torch_npu2",
    python_version="3.10",
    compile_timeout=3600
)

# 开始验证流程
fix = {
    "operator_name": "matmul",
    "requires_rebuild": True,
    "patches": [...]
}

result = agent._verify_fix(fix, "task_001")
```

### 3. 使用测试脚本

```bash
# 测试 Docker 连接和编译
python test_docker_remote.py --host user@server --container lch_test

# 运行完整示例
python examples/docker_verifier_example.py
```

## 新增文件

| 文件 | 说明 |
|------|------|
| `remote/core/docker_executor.py` | Docker 命令执行器 |
| `test_docker_remote.py` | Docker 远程访问测试脚本 |
| `examples/docker_verifier_example.py` | 使用示例 |
| `DOCKER_INTEGRATION.md` | 本文档 |

## 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `multi_agent/core/remote_agent.py` | 添加 Docker 支持 |
| `multi_agent/agents/verifier_agent.py` | 支持 Docker 编译和测试 |
| `multi_agent/config/remote_config.py` | 添加 Docker 配置字段 |
| `remote/core/__init__.py` | 导出 DockerExecutor |
| `SKILL.md` | 更新 VerifierAgent 文档 |

## 核心类说明

### DockerExecutor

```python
from remote.core.docker_executor import DockerExecutor

# 创建 executor
docker = DockerExecutor(
    session=session,
    container_name="lch_test",
    default_working_dir="/home/lch/work/torch_npu"
)

# 检查容器状态
info = docker.get_container_info()

# 启动容器（如果未运行）
docker.start_container()

# 在容器内执行命令
result = docker.execute_sync(
    command="bash ci/build.sh --python=3.10",
    working_dir="/home/lch/work/torch_npu",
    timeout=3600
)

# 复制文件到容器
docker.copy_into_container("/host/file.txt", "/container/file.txt")

# 从容器复制文件
docker.copy_from_container("/container/file.txt", "/host/file.txt")
```

### RemoteCapableAgent（Docker 支持）

```python
from multi_agent.core.remote_agent import RemoteCapableAgent

class MyAgent(RemoteCapableAgent):
    def __init__(self):
        super().__init__(
            agent_id="my_agent",
            capabilities=[...],
            remote_host="user@server",
            # Docker 配置
            use_docker=True,
            docker_container="lch_test",
            docker_work_dir="/home/lch/work/torch_npu"
        )

    def do_something(self):
        if self.use_docker:
            executor = self.get_docker_executor()
            result = executor.execute_sync("some command")
        else:
            result = self.execute_remote_sync("some command")
```

### VerifierAgent（Docker 模式）

```python
from multi_agent.agents.verifier_agent import VerifierAgent

agent = VerifierAgent(
    use_docker=True,
    docker_container="lch_test",
    docker_work_dir="/home/lch/work/torch_npu2",
    python_version="3.10"
)

# 编译（自动使用 Docker 模式）
result = agent._compile_code()

# 测试（自动使用 Docker 模式）
result = agent._run_tests(fix)
```

## 增量编译说明

Docker 模式使用同步执行（非异步），编译过程会保留 build 目录，因此支持增量编译：

1. 首次编译：完整编译，创建 build 目录
2. 后续编译：只编译修改过的文件，节省时间
3. 清理编译：如需完整重建，手动删除容器内的 build 目录

## 注意事项

1. **容器必须存在**：VerifierAgent 不会创建容器，只操作已存在的容器
2. **容器路径正确**：`docker_work_dir` 必须是容器内的有效路径
3. **权限问题**：SSH 用户需要有 docker 命令的执行权限
4. **编译产物**：编译生成的包在容器内的 dist 目录，如需要可通过 `copy_from_container` 复制出来

## 故障排除

### 容器未找到

```
✗ Container lch_test not found
```

解决方案：
- 确认容器名称正确
- 在远程服务器上运行 `docker ps` 查看容器列表

### 容器未运行

```
→ Starting container lch_test...
```

Agent 会自动尝试启动容器，但如果启动失败，需要手动检查：

```bash
ssh user@server "docker start lch_test"
```

### 编译失败

查看详细错误信息：

```python
result = agent._compile_code()
if not result["success"]:
    print(result.get("output"))
    print(result.get("stderr"))
```
