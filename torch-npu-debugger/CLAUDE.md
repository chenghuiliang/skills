# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A lightweight Claude Code skill (`SKILL.md`) for diagnosing and fixing torch_npu operator bugs. Pure documentation-based skill with checkpoint enforcement — no runtime processes, no background agents.

## Skill Activation

The skill triggers on keywords related to torch_npu operator issues: NPU operator bugs, ACLNN adaptation errors, precision anomalies, format conversion issues, dispatch key errors, DO_COMPATIBILITY fallback, OpCommand errors, compilation failures, stream sync problems, dtype mismatches, backward propagation issues, HCCL distributed errors, ATB operator issues, version compatibility problems, import failures, triton conflicts, etc.

## Repository Structure

```
SKILL.md                        # Skill definition, trigger conditions, and 6-step workflow with checkpoints
CLAUDE.md                       # This file: project guidance
references/                     # Domain knowledge base (core value)
  architecture.md               # torch_npu architecture and path navigation
  issue_patterns.md             # 12 problem categories and decision tree
  fix_patterns.md               # Fix templates by component
  debugging_tools.md            # Debugging tools guide
scripts/
  workflow_guard.py             # Checkpoint enforcement script (<200 lines)
  sync-to-server.sh             # Rsync script for remote deployment
.workflow/                      # Workflow state tracking (auto-created)
  checkpoints.json              # Checkpoint completion records
archive/                        # Archived multi-agent implementation (backup)
  multi_agent/                  # Previous multi-agent system
  workflow/                     # Previous workflow engine
```

## Skill Workflow

The skill guides through 6 steps with mandatory checkpoints:

1. **Problem Analysis** → checkpoint: `problem_analyzed`
2. **Scoping (定界)** → checkpoint: `scope_identified`
3. **Localization (定位)** → checkpoint: `code_located`
4. **Fixing** → checkpoint: `fix_applied`
5. **Regression Verification** → checkpoint: `regression_verified` (MANDATORY)
6. **Test Supplementation** → checkpoint: `test_added` (MANDATORY)
7. **Artifacts Archiving** → checkpoint: `artifacts_archived` (MANDATORY)

Mandatory checkpoints cannot be skipped. Use `scripts/workflow_guard.py` to enforce completion.

## torch_npu Source Layout (external, referenced by skill)

Operator source lives in two layers:
- `torch_npu/csrc/framework/` — OpCommand, FormatHelper, OpHook (framework layer)
- `torch_npu/csrc/core/npu/` — NPUCachingAllocator, NPUStream, ACL interface (runtime layer)
- `third_party/op-plugin/op_plugin/ops/opapi/` — ACLNN operator implementations (new path)
- `third_party/op-plugin/op_plugin/ops/aclops/` — ACL operator implementations (old path)

## Remote Server Operations

Use `scripts/sync-to-server.sh` to sync code to the Ascend server, then execute commands via ssh:

```bash
# Sync code
./scripts/sync-to-server.sh

# Compile on remote server (in Docker container)
ssh root@192.168.9.116 "docker exec lch_test bash -c 'cd /home/lch/work/torch_npu2 && bash ci/build.sh'"

# Run tests
ssh root@192.168.9.116 "docker exec lch_test bash -c 'cd /home/lch/work/torch_npu2 && pytest test_ops.py -v'"
```

## Editing Guidelines

- All reference docs are in Chinese — keep them in Chinese
- Code comments in all files must be in English
- When updating `issue_patterns.md`, maintain the decision tree consistency
- `fix_patterns.md` patterns should map to the problem categories in `issue_patterns.md`
- `SKILL.md` trigger keywords should stay aligned with the problem categories
