# 远程服务器部署指南

本指南说明如何将 mindspore-ops-debugger skill 部署到 Ascend 远程服务器上，实现全流程本地执行。

## 环境要求

| 组件 | 要求 |
|------|------|
| OS | Linux (推荐 EulerOS / Ubuntu 20.04+) |
| Python | 3.9+ |
| Node.js | 18+ (用于安装 Claude Code) |
| MindSpore | 源码仓库已克隆到服务器 |
| CANN | 与 MindSpore 版本匹配 |
| 硬件 | Ascend 910A/910B (Step 5-6 需要) |

## 部署步骤

### 1. 安装 Claude Code

```bash
# 安装 Node.js (如果没有)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 Claude Code
npm install -g @anthropic-ai/claude-code
```

### 2. 同步 Skill 到服务器

从本地机器执行：

```bash
# 使用同步脚本
bash scripts/sync-to-server.sh user@your-server

# 或指定自定义路径
bash scripts/sync-to-server.sh user@your-server /home/user/skills/mindspore-ops-debugger
```

或者在服务器上直接克隆：

```bash
git clone <repo-url> ~/mindspore-ops-debugger
```

### 3. 注册 Skill

在服务器上将 skill 注册到 Claude Code：

```bash
mkdir -p ~/.claude/skills
ln -sf ~/mindspore-ops-debugger ~/.claude/skills/mindspore-ops-debugger
```

### 4. 准备工作目录

确保服务器上的目录结构符合 skill 预期：

```
~/                              # 用户 home 目录
├── mindspore/                  # MindSpore 源码仓库
│   └── mindspore/              # 实际源码目录
├── md_files/                   # 算子问题单
│   ├── gitcode/issues/
│   └── gitee/issues/
├── MindSporeTest/              # 测试套件
├── operator_data/              # 算子开发指导文档 (可选)
└── mindspore-ops-debugger/     # 本 skill
    ├── SKILL.md
    ├── references/
    └── scripts/
```

如果目录结构不同，在启动 Claude Code 时通过工作目录指定即可。skill 中的路径都是相对路径。

## 使用方法

### 启动

SSH 登录服务器后，在 MindSpore 工作目录下启动 Claude Code：

```bash
ssh user@your-server
cd ~/mindspore   # 或包含 mindspore/ 和 md_files/ 的父目录
claude
```

### 触发 Skill

在 Claude Code 中描述算子问题即可自动触发 skill，例如：

```
MindSpore 的 imod 算子在 Ascend 上精度异常，float16 输入时结果与 CPU 不一致
```

skill 会自动执行 6 步工作流：问题分析 → 定界 → 定位 → 修复 → 回归验证 → 测试补充。

## 远程增量编译与验证约定

如果用户已经给出服务器上的标准环境初始化方式，优先严格照用，不要自行改成其他脚本或全量重编流程。以常见 MindSpore Ascend 环境为例：

```bash
cd /home/lch/work
source env_ms.sh mindspore/
cd mindspore
```

在这个基础上再执行编译或测试命令。

### 增量编译

修改 C++ / `ccsrc/` / `core/` / kernel / fallback 路径后，优先做增量编译：

```bash
cd /home/lch/work
source env_ms.sh mindspore/
cd mindspore
bash build.sh -e ascend -V 910b -j64 -S on
```

注意：

- 默认不要清空 `build/` 目录，除非用户明确要求全量重编
- 纯 Python 或测试文件改动通常无需重新编译
- 编译结束后再运行同一套 `source env_ms.sh mindspore/` 环境中的 Python/pytest，避免误用系统安装版本

### 模式差异问题验证

如果问题涉及 `PyNative` 和 `Graph/JIT` 不一致，验证时至少覆盖：

1. 原始复现场景
2. `PyNative` 模式结果
3. `Graph/JIT` 模式结果
4. 第三方基线（如 PyTorch）或历史正确结果

对零维、空 shape、标量退化类问题，不只看值，还要核对 `shape`、rank、dtype。

### 交付物与 PR 描述

如果用户要求在 issue 目录沉淀材料，至少准备：

- 定位总结 `*_summary.md`
- 代码修改 `*_code_changes.diff`
- PR 描述 `*_pr_description.md`

生成 PR 描述时：

- 必须先读取用户给出的 PR 模板文件
- 只保留模板要求的字段和 checklist
- `Test Plan and Test result` 必须写实际执行过的命令和结果，不能留空
- 若 `/check-pr` 报“存在不符合模板的选项”，通常说明混入了旧版模板的检查项，需要按最新模板整体重写

### 更新 Skill

当 skill 有更新时，重新同步即可：

```bash
# 从本地推送更新
bash scripts/sync-to-server.sh user@your-server

# 或在服务器上 git pull
cd ~/mindspore-ops-debugger && git pull
```

## 常见问题

### Claude Code 安装失败

如果服务器无法访问外网，可以在有网络的机器上下载 npm 包，然后离线安装：

```bash
# 有网络的机器上
npm pack @anthropic-ai/claude-code
# 将 .tgz 文件传到服务器
scp anthropic-ai-claude-code-*.tgz user@server:~/
# 服务器上安装
npm install -g ~/anthropic-ai-claude-code-*.tgz
```

### Skill 未被识别

确认符号链接正确：

```bash
ls -la ~/.claude/skills/mindspore-ops-debugger/SKILL.md
```

如果文件不存在，检查符号链接路径是否正确。

### 编译环境问题

Step 5-6 需要完整的 MindSpore 编译环境。确认以下组件可用：

```bash
# 检查编译工具
gcc --version
cmake --version

# 检查 CANN
ls /usr/local/Ascend/ascend-toolkit/latest/

# 检查 Python 环境
python3 -c "import mindspore; print(mindspore.__version__)"
```
